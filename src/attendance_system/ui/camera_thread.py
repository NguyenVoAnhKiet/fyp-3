"""Background QThread: camera capture + AI pipeline execution."""

from __future__ import annotations

import logging
import time
from typing import Any

import cv2
import cv2.data  # noqa: F401 — ensures cv2.data submodule is accessible
import numpy as np
from PyQt5.QtCore import pyqtSignal

from pathlib import Path
from attendance_system.services.ai_pipeline import AIPipeline, FaceRecognizer, LivenessChecker
from attendance_system.services.exceptions import LivenessInferenceError
from attendance_system.ui.camera_worker_base import (
    CameraThreadBase,
    AIWorkerBase,
    _COLOR_ALERT,
    _COLOR_SUCCESS,
    _COLOR_UNKNOWN,
    _RESULT_HOLD_FRAMES,
)

_AI_FRAME_SKIP = 3       # run full pipeline every N frames (≈10 Hz at 30 fps)
_COOLDOWN_SECONDS = 1.5  # min seconds between two recognitions of the same user

logger = logging.getLogger(__name__)


class AIWorker(AIWorkerBase):
    """
    Worker QThread that performs anti-spoofing and face recognition on a background thread.
    Uses a queue of size 1 for backpressure.
    """

    recognition_result = pyqtSignal(str, int, str, float, object, str)

    def __init__(
        self,
        pipeline: AIPipeline,
        parent: Any = None,
    ) -> None:
        super().__init__(pipeline, parent)
        self._last_recognized: dict[int, float] = {}  # user_id -> monotonic timestamp
        self._ai_frame_counter: int = 0  # local counter per processed frame

    def submit_task(
        self,
        frame_bgr: np.ndarray,
        frame_rgb: np.ndarray,
        face_row: np.ndarray,
        frame_counter: int,
    ) -> bool:
        """
        Submit a task to the worker queue.
        Numpy arrays are automatically copied by the base class.
        Returns True if submitted, False if queue is full.
        """
        return super().submit_task(frame_bgr, frame_rgb, face_row, frame_counter)

    # ------------------------------------------------------------------
    # AIWorkerBase hooks
    # ------------------------------------------------------------------

    def _inference_error_types(self) -> tuple:
        return (LivenessInferenceError,)

    def _process_frame(self, task) -> None:
        frame_bgr, frame_rgb, face_row, frame_counter = task
        self._ai_frame_counter += 1

        result = self._pipeline.run_attendance(
            frame_bgr, frame_rgb, face_row, self._ai_frame_counter
        )

        # Per-user cooldown to avoid flooding the DB
        if result.result_type == "success" and result.user_id is not None:
            now = time.monotonic()
            if now - self._last_recognized.get(result.user_id, 0.0) < _COOLDOWN_SECONDS:
                return
            self._last_recognized[result.user_id] = now

        self.recognition_result.emit(
            result.result_type,
            result.user_id or 0,
            result.full_name or "",
            result.liveness_score or 0.0,
            result.similarity,
            result.matched_pose_label or "",
        )

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def stop(self) -> None:
        """Stop the worker, resetting the liveness tracker first."""
        self._pipeline.reset_tracker()
        super().stop()


class CameraThread(CameraThreadBase):
    """
    Reads frames from a webcam and runs the AI pipeline on a background thread.

    Signals
    -------
    frame_ready(QImage)
        Every captured frame, annotated with bounding boxes, converted to QImage.
        (Inherited from CameraThreadBase)
    recognition_result(result_type, user_id, full_name, liveness_score, similarity_score)
        result_type: "success" | "spoof" | "unrecognized"
    camera_error(str)
        Emitted if the camera cannot be opened or a read fails.
        (Inherited from CameraThreadBase)
    """

    recognition_result = pyqtSignal(str, int, str, float, object, str)

    def __init__(
        self,
        session_id: int,
        liveness_threshold: float,
        similarity_threshold: float,
        liveness_checker: LivenessChecker,
        face_recognizer: FaceRecognizer,
        camera_index: int = 0,
        detector_model_path: Path | str | None = None,
        parent: Any = None,
    ) -> None:
        super().__init__(camera_index, detector_model_path, parent)
        self._session_id = session_id
        self._liveness_threshold = liveness_threshold
        self._similarity_threshold = similarity_threshold
        self._liveness_checker = liveness_checker
        self._face_recognizer = face_recognizer

        # Initialize AI pipeline and worker thread
        pipeline = AIPipeline(
            liveness_checker=self._liveness_checker,
            face_recognizer=self._face_recognizer,
            liveness_threshold=self._liveness_threshold,
            similarity_threshold=self._similarity_threshold,
        )
        self._ai_worker = AIWorker(
            pipeline=pipeline,
            parent=self,
        )
        self._ai_worker.recognition_result.connect(self._on_recognition_result)
        self._ai_worker.inference_warning.connect(self.inference_warning.emit)
        self._ai_worker.camera_error.connect(self._on_ai_worker_camera_error)

    # ------------------------------------------------------------------
    # QThread entry point
    # ------------------------------------------------------------------

    def run(self) -> None:
        """Start the AI worker, then run the base camera capture loop."""
        self._ai_worker.start()
        super().run()

    # ------------------------------------------------------------------
    # CameraThreadBase hooks
    # ------------------------------------------------------------------

    def _cleanup_worker(self) -> None:
        """Disconnect AI worker signals and stop the worker."""
        try:
            self._ai_worker.recognition_result.disconnect()
            self._ai_worker.inference_warning.disconnect()
            self._ai_worker.camera_error.disconnect()
        except TypeError:
            pass
        self._ai_worker.stop()

    def _process_frame(
        self, frame: np.ndarray, faces: np.ndarray | None, frame_counter: int
    ) -> None:
        """Per-frame processing: AI submission + annotation + display."""
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # Run full AI pipeline asynchronously every N frames (only when faces are present)
        if frame_counter % _AI_FRAME_SKIP == 0 and faces is not None and len(faces) > 0:
            # Skip AI work when queue is full — CPU drops ~30% during AI lag
            if not self._ai_worker.is_busy():
                idx = int(np.argmax(faces[:, 2] * faces[:, 3]))
                face_row = faces[idx]
                self._ai_worker.submit_task(frame, frame_rgb, face_row, frame_counter)

        # Draw bboxes onto a copy, then emit the annotated frame
        annotated = self._draw_bboxes(frame_rgb)
        self._emit_display_frame(annotated)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _on_ai_worker_camera_error(self, message: str) -> None:
        self.camera_error.emit(message)
        self._running = False
        self._cleanup_worker()

    def _on_recognition_result(
        self,
        result_type: str,
        user_id: int,
        full_name: str,
        liveness_score: float,
        similarity_score: Any,
        matched_pose_label: str = "",
    ) -> None:
        self._current_result_type = result_type
        self._current_result_name = full_name
        if result_type == "success":
            self._current_result_score = float(similarity_score or 0.0)
            self._bbox_color = _COLOR_SUCCESS
        elif result_type == "spoof":
            self._current_result_score = liveness_score
            self._bbox_color = _COLOR_ALERT
        elif result_type == "unrecognized":
            self._current_result_score = liveness_score
            self._bbox_color = _COLOR_UNKNOWN

        self._result_hold_counter = _RESULT_HOLD_FRAMES
        self.recognition_result.emit(
            result_type, user_id, full_name, liveness_score, similarity_score, matched_pose_label
        )
