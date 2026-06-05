"""Background QThread: AI inference for enrollment (head-pose, liveness, embedding)."""

from __future__ import annotations

import logging
from typing import Any

import numpy as np
from PyQt5.QtCore import pyqtSignal

from attendance_system.services.ai_pipeline import AIPipeline
from attendance_system.services.exceptions import LivenessInferenceError, PoseInferenceError
from attendance_system.ui.camera_worker_base import AIWorkerBase

logger = logging.getLogger(__name__)


class EnrollmentAIWorker(AIWorkerBase):
    """
    Worker QThread that performs head-pose estimation, liveness checking, and
    face embedding extraction on a background thread.
    Uses a queue of size 1 for backpressure.
    """

    pose_estimated = pyqtSignal(float, float, float)  # pitch, yaw, roll
    capture_complete = pyqtSignal(bool, object, float)  # success, embedding_or_None, liveness_score

    def __init__(
        self,
        pipeline: AIPipeline,
        parent: Any = None,
    ) -> None:
        super().__init__(pipeline, parent)

    def submit_task(
        self,
        frame_bgr: np.ndarray,
        face_row: np.ndarray,
        do_capture: bool = False,
    ) -> bool:
        """
        Submit a task to the worker queue.
        Numpy arrays are auto-copied by the base class.
        Returns True if submitted, False if queue is full.
        """
        return super().submit_task(do_capture, frame_bgr, face_row)

    def _inference_error_types(self):
        return (PoseInferenceError, LivenessInferenceError)

    def _process_frame(self, task) -> None:
        do_capture, frame_bgr, face_row = task
        result = self._pipeline.run_enrollment(
            frame_bgr, face_row, self._queue.qsize(), do_capture=do_capture,
        )
        if result.result_type == "pose_only":
            self.pose_estimated.emit(result.pitch, result.yaw, result.roll)
        elif result.result_type == "capture_success":
            self.pose_estimated.emit(result.pitch, result.yaw, result.roll)
            self.capture_complete.emit(True, result.embedding, result.liveness_score)
        elif result.result_type == "capture_fail":
            if result.pitch is not None:
                self.pose_estimated.emit(result.pitch, result.yaw, result.roll)
            self.capture_complete.emit(False, None, result.liveness_score or 0.0)

    def _on_inference_error(self, task) -> None:
        do_capture = task[0] if task else False
        if do_capture:
            self.capture_complete.emit(False, None, 0.0)
        else:
            self.inference_warning.emit("Lỗi head-pose — đang thử lại...")
