"""AI pipeline: liveness detection (ONNX) + face recognition (SFace)."""

from __future__ import annotations
 
__all__ = ["LivenessResult", "RecognitionResult", "LivenessChecker", "FaceRecognizer"]

import math
from pathlib import Path
from typing import NamedTuple

import cv2
import numpy as np
import onnxruntime as ort

from attendance_system.core.db import Database
from attendance_system.services.exceptions import LivenessInferenceError
from attendance_system.repositories.face_reference_repository import (
    FaceReferenceRepository,
)
from attendance_system.repositories.user_repository import UserRepository

_LIVENESS_IMG_SIZE = 128


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

    @property
    def is_enabled(self) -> bool:
        """Whether a real ONNX model is loaded (vs. disabled/bypassed).

        Returns:
            True if a real model was loaded and liveness checking is active.
            False if model_path was None (liveness is bypassed).
        """
        return self._session is not None

    def _preprocess(self, face_rgb: np.ndarray) -> np.ndarray:
        """Letterbox-resize and normalize face crop to model input tensor [1, 3, H, W].

        Pipeline (matches MiniFASNet training preprocessing without CLAHE):
            1. Resize longest side to 128px (keep aspect ratio)
            2. Reflect-pad to 128×128
            3. Transpose HWC → CHW and normalize to [0, 1]
        """
        #=======================================================================
        # Step 1: Scale the longest side down to 128px, keep aspect ratio
        #=======================================================================
        old_size = face_rgb.shape[:2]  # (H, W)
        ratio = float(_LIVENESS_IMG_SIZE) / max(old_size)
        scaled_shape = (int(old_size[0] * ratio), int(old_size[1] * ratio))
        interp = cv2.INTER_LANCZOS4 if ratio > 1.0 else cv2.INTER_AREA
        img = cv2.resize(face_rgb, (scaled_shape[1], scaled_shape[0]), interpolation=interp)

        #=======================================================================
        # Step 2: Pad the shorter side to make a 128×128 square
        #=======================================================================
        # BORDER_REFLECT_101 avoids hard edge artifacts at the padding boundary.
        delta_h = _LIVENESS_IMG_SIZE - scaled_shape[0]
        delta_w = _LIVENESS_IMG_SIZE - scaled_shape[1]
        top, bottom = delta_h // 2, delta_h - (delta_h // 2)
        left, right = delta_w // 2, delta_w - (delta_w // 2)
        img = cv2.copyMakeBorder(img, top, bottom, left, right, cv2.BORDER_REFLECT_101)

        #=======================================================================
        # Step 3: HWC uint8 → CHW float32 in [0, 1] (model training range)
        #=======================================================================
        # NOTE: Do NOT normalize to [-1, 1]; this model was trained with [0, 1] inputs.
        arr = img.transpose(2, 0, 1).astype(np.float32) / 255.0
        return arr[np.newaxis]  # add batch dim → [1, 3, H, W]

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
            stored_emb = np.frombuffer(ref["embedding"], dtype=np.float32)
            sim = self._cosine_similarity(live_emb, stored_emb)
            if sim > best_sim:
                best_sim = sim
                best_ref = ref

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
