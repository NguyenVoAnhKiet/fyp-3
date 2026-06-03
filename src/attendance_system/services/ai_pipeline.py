"""AI pipeline: liveness detection (ONNX) + face recognition (SFace) + AIPipeline orchestrator."""

from __future__ import annotations

__all__ = [
    "LivenessResult",
    "RecognitionResult",
    "LivenessChecker",
    "FaceRecognizer",
    "AIPipeline",
]

import logging
import math
from pathlib import Path
from typing import NamedTuple

import cv2
import numpy as np
import onnxruntime as ort

from attendance_system.core.db import Database
from attendance_system.services.exceptions import LivenessInferenceError
from attendance_system.services.face_preprocessor import FacePreprocessor
from attendance_system.services.head_pose import HeadPoseEstimator
from attendance_system.services.liveness_tracker import (
    LivenessTracker,
    compute_iou,
    IOU_THRESHOLD,
)
from attendance_system.services.pipeline_result import PipelineResult
from attendance_system.services.preprocessing_configs import LIVENESS_CONFIG
from attendance_system.repositories.face_reference_repository import (
    FaceReferenceRepository,
)
from attendance_system.repositories.user_repository import UserRepository
from attendance_system.utils.face_utils import _crop_face

logger = logging.getLogger(__name__)


class LivenessResult(NamedTuple):
    is_real: bool
    score: float  # logit_diff — higher means more likely real


class RecognitionResult(NamedTuple):
    user_id: int
    full_name: str
    student_id: str
    similarity: float
    matched_pose_label: str = ""


class LivenessChecker:
    """
    Wraps the quantized MiniFASNet ONNX model from facenox/face-antispoof-onnx.

    Model: models/anti_spoof/best_model_quantized.onnx
    Input:  [1, 3, 128, 128] float32, values in [0, 1]
    Output: [1, 2] logits — index 0 = real, index 1 = spoof

    Pass model_path=None (or set FACE_ANTISPOOF_ENABLED=false) to bypass
    liveness checking — every face will be treated as real.
    """

    def __init__(self, model_path: Path | None) -> None:
        """
        Initializes the liveness checker.

        Args:
            model_path: Path to the quantized MiniFASNet ONNX model.
                       If None, liveness checking is bypassed.
        """
        #=======================================================================
        # Step 1: Initialize ONNX inference session
        #=======================================================================
        if model_path is not None:
            self._session: ort.InferenceSession | None = ort.InferenceSession(
                str(model_path)
            )
            self._input_name: str | None = self._session.get_inputs()[0].name
            self._model_path: str = str(model_path)
        else:
            self._session = None
            self._input_name = None
            self._model_path = ""

        # Composable preprocessing pipeline (extracted from this class as
        # part of plan 0007). Owns crop -> resize -> normalize -> to_tensor.
        # `_preprocess` below is now a one-liner that delegates here.
        self._preprocessor = FacePreprocessor(LIVENESS_CONFIG)

    @property
    def is_enabled(self) -> bool:
        """Whether a real ONNX model is loaded (vs. disabled/bypassed).

        Returns:
            True if a real model was loaded and liveness checking is active.
            False if model_path was None (liveness is bypassed).
        """
        return self._session is not None

    def _preprocess(
        self,
        face_rgb: np.ndarray,
        bbox: tuple[int, int, int, int] | None = None,
    ) -> np.ndarray:
        """Preprocess a face crop into the MiniFASNet input tensor.

        Delegates to the shared `FacePreprocessor` (plan 0007). The
        optional `bbox` argument enables the crop step; existing
        callers pre-crop with `_crop_face` and pass ``bbox=None``,
        so behavior is unchanged.

        Returns:
            float32 tensor of shape ``(1, 3, 128, 128)``, values in [0, 1].
        """
        return self._preprocessor(face_rgb, bbox)

    def check(self, face_rgb: np.ndarray, threshold: float = 0.3) -> LivenessResult:
        """
        Check liveness of a pre-cropped face image.

        If the model is disabled (model_path=None), always returns is_real=True.

        Args:
            face_rgb:  H×W×3 uint8 RGB face crop.
            threshold: Probability threshold (0–1).  Default 0.3.

        Returns:
            LivenessResult with is_real flag and raw logit_diff score.
        """
        if self._session is None:
            return LivenessResult(is_real=True, score=1.0)

        #=======================================================================
        # Step 1: Preprocess face crop into model-ready tensor
        #=======================================================================
        arr = self._preprocess(face_rgb)

        #=======================================================================
        # Step 2: Run ONNX inference
        #=======================================================================
        # Output shape: [1, 2]  (index 0 = real logit, index 1 = spoof logit)
        try:
            raw = self._session.run(None, {self._input_name: arr})
        except Exception as exc:
            raise LivenessInferenceError(
                f"Liveness inference failed: {exc}",
                input_shape=arr.shape,
                model_path=self._model_path,
            ) from exc
        output: np.ndarray = np.array(raw[0])
        logit_diff = float(output[0][0] - output[0][1])  # positive → real, negative → spoof

        #=======================================================================
        # Step 3: Convert probability threshold → logit space and classify
        #=======================================================================
        # logit(p) = log(p / (1-p)); comparing logit_diff to this is equivalent
        # to comparing softmax(real) to the threshold probability.
        p = max(1e-6, min(1 - 1e-6, threshold))
        logit_threshold = math.log(p / (1 - p))

        is_real = logit_diff > logit_threshold
        return LivenessResult(is_real=is_real, score=logit_diff)


class FaceRecognizer:
    """
    Identifies faces by comparing live embeddings against DB references.

    Embeddings stored in face_references.embedding must be raw float32 bytes
    (numpy array serialised with ndarray.tobytes()).
    """

    def __init__(
        self, database: Database, model_path: Path | str | None = None
    ) -> None:
        """
        Initializes the face recognizer with a database and optional model path.

        Args:
            database: Database instance for retrieving user and face data.
            model_path: Path to the SFace ONNX model file.
        """
        #=======================================================================
        # Step 1: Initialize database repositories
        #=======================================================================
        self._face_refs = FaceReferenceRepository(database)
        self._users = UserRepository(database)
        
        #=======================================================================
        # Step 2: Load SFace model
        #=======================================================================
        if model_path is None:
            model_path = Path("models") / "face_recognition" / "face_recognition_sface_2021dec.onnx"
            
        self._sface = cv2.FaceRecognizerSF.create(str(model_path), "")

    @staticmethod
    def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
        """
        Calculates cosine similarity in range [-1, 1].

        Args:
            a: First vector (e.g., live embedding).
            b: Second vector (e.g., stored embedding).

        Returns:
            Similarity score. Returns -1.0 if b is a zero vector.
        """
        norm_b = np.linalg.norm(b)
        if norm_b == 0:
            return -1.0
        return float(np.dot(a.ravel(), b) / (np.linalg.norm(a) * norm_b))

    @staticmethod
    def average_embeddings(embeddings: list[np.ndarray]) -> np.ndarray:
        """
        Calculates the average (mean) embedding from a list of vectors.
        The result is normalized to unit length.
        """
        if not embeddings:
            raise ValueError("Empty embeddings list")
        
        avg = np.mean(embeddings, axis=0)
        norm = np.linalg.norm(avg)
        if norm > 0:
            avg /= norm
        return avg.astype(np.float32)

    def get_embedding(self, frame_bgr: np.ndarray, yunet_face_row: np.ndarray) -> np.ndarray | None:
        """
        Extracts a float32 embedding vector using SFace alignCrop + feature extraction.

        Args:
            frame_bgr: The original BGR frame from camera.
            yunet_face_row: The face detection result row from YuNet.

        Returns:
            A normalized float32 embedding vector, or None if extraction fails.
        """
        try:
            aligned_face = self._sface.alignCrop(frame_bgr, yunet_face_row)
            feat = self._sface.feature(aligned_face)
            emb = np.array(feat[0], dtype=np.float32)
            return emb if np.linalg.norm(emb) > 0 else None
        except Exception:
            return None

    def identify(
        self, frame_bgr: np.ndarray, yunet_face_row: np.ndarray, threshold: float = 0.6
    ) -> RecognitionResult | None:
        """
        Identifies a face by comparing its live embedding against all stored references.

        Args:
            frame_bgr: The original BGR frame from camera.
            yunet_face_row: The face detection result row from YuNet.
            threshold: Minimum similarity score to consider a match. Default 0.6.

        Returns:
            A RecognitionResult if a match is found, otherwise None.
        """
        #=======================================================================
        # Step 1: Extract 128-dim SFace embedding from the live frame
        #=======================================================================
        live_emb = self.get_embedding(frame_bgr, yunet_face_row)
        if live_emb is None:
            return None

        #=======================================================================
        # Step 2: Find the closest stored reference using cosine similarity
        #=======================================================================
        refs = self._face_refs.get_all()
        best_sim: float = -1.0
        best_ref = None

        for ref in refs:
            try:
                stored_emb = np.frombuffer(ref["embedding"], dtype=np.float32)
                sim = self._cosine_similarity(live_emb, stored_emb)
                if sim > best_sim:
                    best_sim = sim
                    best_ref = ref
            except (ValueError, TypeError, IndexError):
                continue

        #=======================================================================
        # Step 3: Apply similarity threshold guard
        #=======================================================================
        if best_ref is None or best_sim < threshold:
            return None

        #=======================================================================
        # Step 4: Resolve user details from DB
        #=======================================================================
        user = self._users.get_by_id(int(best_ref["user_id"]))
        if user is None:
            return None

        matched_pose_label = str(best_ref.get("pose_label", ""))

        return RecognitionResult(
            user_id=int(best_ref["user_id"]),
            full_name=str(user["full_name"]),
            student_id=str(user["student_id"]),
            similarity=best_sim,
            matched_pose_label=matched_pose_label,
        )


class AIPipeline:
    """Orchestrates per-frame AI inference: liveness, recognition, head-pose.

    Composes ``LivenessChecker``, ``FaceRecognizer``, ``LivenessTracker``,
    and optionally ``HeadPoseEstimator`` as injected dependencies.  Each
    ``AIPipeline`` instance owns its own ``LivenessTracker`` state (one
    tracker per worker thread).

    Usage::

        pipeline = AIPipeline(
            liveness_checker=checker,
            face_recognizer=recognizer,
            liveness_threshold=0.3,
            similarity_threshold=0.6,
        )
        result = pipeline.run_attendance(frame_bgr, frame_rgb, face_row, 42)
        if result.result_type == "success":
            print(f"Recognised user {result.user_id}")

    Args:
        liveness_checker: Liveness detection service.
        face_recognizer: Face recognition service.
        head_pose_estimator: Optional head-pose estimation service
            (required for ``run_enrollment``).
        liveness_threshold: Decision threshold for liveness check.
        similarity_threshold: Minimum cosine similarity for recognition.
    """

    def __init__(
        self,
        liveness_checker: LivenessChecker,
        face_recognizer: FaceRecognizer,
        head_pose_estimator: HeadPoseEstimator | None = None,
        liveness_threshold: float = 0.3,
        similarity_threshold: float = 0.6,
    ) -> None:
        self._liveness_checker = liveness_checker
        self._face_recognizer = face_recognizer
        self._head_pose_estimator = head_pose_estimator
        self._liveness_threshold = liveness_threshold
        self._similarity_threshold = similarity_threshold
        self._liveness_tracker = LivenessTracker()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run_attendance(
        self,
        frame_bgr: np.ndarray,
        frame_rgb: np.ndarray,
        face_row: np.ndarray,
        frame_counter: int,
    ) -> PipelineResult:
        """Run attendance pipeline: liveness → temporal smoothing → recognition.

        Args:
            frame_bgr: BGR frame from camera (for SFace alignment).
            frame_rgb: RGB frame (for liveness crop).
            face_row: YuNet detection result ``[15]`` for the largest face.
            frame_counter: Current frame number (for metadata).

        Returns:
            ``PipelineResult`` with ``result_type`` ``"success"``,
            ``"spoof"``, or ``"unrecognized"``.

        Raises:
            LivenessInferenceError: If liveness ONNX inference fails.
        """
        x, y, w, h = face_row[:4].astype(int)

        # Step 1: Crop face for liveness (scale=2.7)
        face_crop = _crop_face(frame_rgb, (x, y, w, h), scale=2.7)

        # Step 2: Liveness check
        liveness = self._liveness_checker.check(
            face_crop, self._liveness_threshold
        )

        # Step 3: Temporal smoothing via EMA + hysteresis tracker
        bbox_float = (float(x), float(y), float(w), float(h))
        tracked_faces = self._liveness_tracker.update(
            [bbox_float], [liveness.score]
        )

        state = "SPOOF"
        ema_score = liveness.score
        for tb, ts, tes in tracked_faces:
            if compute_iou(bbox_float, tb) >= IOU_THRESHOLD:
                state = ts
                ema_score = tes
                break

        if state == "SPOOF":
            return PipelineResult(
                result_type="spoof",
                frame_counter=frame_counter,
                liveness_score=ema_score,
            )

        # Step 4: Recognition
        match = self._face_recognizer.identify(
            frame_bgr, face_row, self._similarity_threshold
        )

        if match is None:
            return PipelineResult(
                result_type="unrecognized",
                frame_counter=frame_counter,
                liveness_score=ema_score,
            )

        return PipelineResult(
            result_type="success",
            frame_counter=frame_counter,
            liveness_score=ema_score,
            user_id=match.user_id,
            full_name=match.full_name,
            student_id=match.student_id,
            similarity=match.similarity,
            matched_pose_label=match.matched_pose_label,
        )

    def run_enrollment(
        self,
        frame_bgr: np.ndarray,
        face_row: np.ndarray,
        frame_counter: int,
        do_capture: bool = False,
    ) -> PipelineResult:
        """Run enrollment pipeline: head-pose → liveness → embedding.

        Args:
            frame_bgr: BGR frame from camera.
            face_row: YuNet detection result ``[15]``.
            frame_counter: Current frame number.
            do_capture: If ``True``, also run liveness + embedding extraction.

        Returns:
            ``PipelineResult`` with head-pose results and optionally
            embedding.

        Raises:
            PoseInferenceError: If head-pose ONNX inference fails.
            LivenessInferenceError: If liveness ONNX inference fails.
        """
        if self._head_pose_estimator is None:
            raise RuntimeError(
                "HeadPoseEstimator required for run_enrollment()"
            )

        # Step 1: Head-pose estimation (default crop scale=1.5)
        face_crop_pose = _crop_face(
            frame_bgr, face_row[:4].astype(int)
        )
        if face_crop_pose.size == 0:
            return PipelineResult(
                result_type="capture_fail",
                frame_counter=frame_counter,
            )

        pitch, yaw, roll = self._head_pose_estimator.estimate(
            face_crop_pose
        )

        if not do_capture:
            return PipelineResult(
                result_type="pose_only",
                frame_counter=frame_counter,
                pitch=pitch,
                yaw=yaw,
                roll=roll,
            )

        # Step 2: Liveness check (scale=2.7)
        face_crop_capture = _crop_face(
            frame_bgr, face_row[:4].astype(int), scale=2.7
        )
        if face_crop_capture.size == 0:
            return PipelineResult(
                result_type="capture_fail",
                frame_counter=frame_counter,
                pitch=pitch,
                yaw=yaw,
                roll=roll,
            )

        liveness = self._liveness_checker.check(
            face_crop_capture, self._liveness_threshold
        )

        if not liveness.is_real:
            return PipelineResult(
                result_type="capture_fail",
                frame_counter=frame_counter,
                liveness_score=liveness.score,
                pitch=pitch,
                yaw=yaw,
                roll=roll,
            )

        # Step 3: Embedding extraction
        emb = self._face_recognizer.get_embedding(frame_bgr, face_row)
        if emb is None:
            return PipelineResult(
                result_type="capture_fail",
                frame_counter=frame_counter,
                liveness_score=liveness.score,
                pitch=pitch,
                yaw=yaw,
                roll=roll,
            )

        return PipelineResult(
            result_type="capture_success",
            frame_counter=frame_counter,
            liveness_score=liveness.score,
            pitch=pitch,
            yaw=yaw,
            roll=roll,
            embedding=emb,
        )

    def reset_tracker(self) -> None:
        """Reset the LivenessTracker state. Call when starting a new session."""
        self._liveness_tracker.tracks.clear()
