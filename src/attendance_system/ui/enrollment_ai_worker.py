"""Background QThread: AI inference for enrollment (head-pose, liveness, embedding)."""

from __future__ import annotations

import logging
import queue
from typing import Any

import numpy as np
from PyQt5.QtCore import QThread, pyqtSignal

from attendance_system.services.ai_pipeline import AIPipeline
from attendance_system.services.exceptions import LivenessInferenceError, PoseInferenceError

logger = logging.getLogger(__name__)

_SENTINEL = object()
_MAX_CONSECUTIVE_FAILURES = 30


class EnrollmentAIWorker(QThread):
    """
    Worker QThread that performs head-pose estimation, liveness checking, and
    face embedding extraction on a background thread.
    Uses a queue of size 1 for backpressure.
    """

    pose_estimated = pyqtSignal(float, float, float)  # pitch, yaw, roll
    capture_complete = pyqtSignal(bool, object, float)  # success, embedding_or_None, liveness_score
    inference_warning = pyqtSignal(str)
    camera_error = pyqtSignal(str)

    def __init__(
        self,
        pipeline: AIPipeline,
        parent: Any = None,
    ) -> None:
        super().__init__(parent)
        self._pipeline = pipeline
        self._queue: queue.Queue[Any] = queue.Queue(maxsize=1)
        self._running = False
        self._consecutive_failures = 0

    def submit_task(
        self,
        frame_bgr: np.ndarray,
        face_row: np.ndarray,
        do_capture: bool = False,
    ) -> bool:
        """
        Submit a task to the worker queue.
        Numpy arrays MUST be copied to avoid frame buffer overwriting.
        Returns True if submitted, False if queue is full.
        """
        try:
            self._queue.put_nowait((do_capture, frame_bgr.copy(), face_row.copy()))
            return True
        except queue.Full:
            return False

    def run(self) -> None:
        self._running = True
        self._consecutive_failures = 0

        while self._running:
            try:
                task = self._queue.get(timeout=0.1)
            except queue.Empty:
                continue

            if task is _SENTINEL:
                break

            do_capture, frame_bgr, face_row = task

            # Delegate to AIPipeline for the core AI processing
            try:
                result = self._pipeline.run_enrollment(
                    frame_bgr, face_row, self._queue.qsize(), do_capture=do_capture,
                )
            except (PoseInferenceError, LivenessInferenceError):
                self._consecutive_failures += 1
                logger.warning(
                    "[EnrollmentAIWorker] Inference error (%d/%d consecutive)",
                    self._consecutive_failures,
                    _MAX_CONSECUTIVE_FAILURES,
                    exc_info=True,
                )
                if self._consecutive_failures >= _MAX_CONSECUTIVE_FAILURES:
                    self.camera_error.emit(
                        f"Mô hình AI gặp lỗi sau {_MAX_CONSECUTIVE_FAILURES} "
                        "lần liên tiếp. Vui lòng khởi động lại ứng dụng."
                    )
                    self._running = False
                    break
                if do_capture:
                    self.capture_complete.emit(False, None, 0.0)
                else:
                    self.inference_warning.emit("Lỗi head-pose — đang thử lại...")
                continue

            # Reset consecutive-failure counter on success
            self._consecutive_failures = 0

            # Emit appropriate signals based on result type
            if result.result_type == "pose_only":
                self.pose_estimated.emit(result.pitch, result.yaw, result.roll)
            elif result.result_type == "capture_success":
                self.pose_estimated.emit(result.pitch, result.yaw, result.roll)
                self.capture_complete.emit(True, result.embedding, result.liveness_score)
            elif result.result_type == "capture_fail":
                if result.pitch is not None:
                    self.pose_estimated.emit(result.pitch, result.yaw, result.roll)
                self.capture_complete.emit(False, None, result.liveness_score or 0.0)

    def stop(self) -> None:
        self._running = False
        # Drain the queue to release references to frames
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
            except queue.Empty:
                pass

        # Push sentinel to unblock queue.get()
        try:
            self._queue.put_nowait(_SENTINEL)
        except queue.Full:
            try:
                self._queue.get_nowait()
            except queue.Empty:
                pass
            try:
                self._queue.put_nowait(_SENTINEL)
            except queue.Full:
                pass

        self.wait(3000)
