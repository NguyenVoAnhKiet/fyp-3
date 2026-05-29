"""Background QThread: AI inference for enrollment (head-pose, liveness, embedding)."""

from __future__ import annotations

import logging
import queue
from typing import Any

import numpy as np
from PyQt5.QtCore import QThread, pyqtSignal

from attendance_system.services.ai_pipeline import FaceRecognizer, LivenessChecker
from attendance_system.services.exceptions import LivenessInferenceError, PoseInferenceError
from attendance_system.services.head_pose import HeadPoseEstimator
from attendance_system.utils.face_utils import _crop_face

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
        head_pose_estimator: HeadPoseEstimator,
        liveness_checker: LivenessChecker,
        face_recognizer: FaceRecognizer,
        liveness_threshold: float = 0.3,
        parent: Any = None,
    ) -> None:
        super().__init__(parent)
        self._head_pose_estimator = head_pose_estimator
        self._liveness_checker = liveness_checker
        self._face_recognizer = face_recognizer
        self._liveness_threshold = liveness_threshold
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

            # Step 1 — Head-pose estimation (default scale=1.5)
            face_crop_pose = _crop_face(frame_bgr, face_row[:4].astype(int))
            if face_crop_pose.size == 0:
                self.inference_warning.emit("Không thể crop khuôn mặt cho head-pose")
                continue

            try:
                pitch, yaw, roll = self._head_pose_estimator.estimate(face_crop_pose)
            except PoseInferenceError:
                self._consecutive_failures += 1
                logger.warning(
                    "[EnrollmentAIWorker] Head-pose inference error (%d/%d consecutive)",
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
                self.inference_warning.emit("Lỗi head-pose — đang thử lại...")
                continue

            # Reset consecutive-failure counter on head-pose success
            self._consecutive_failures = 0
            self.pose_estimated.emit(pitch, yaw, roll)

            # Step 2 (optional) — Liveness + Embedding (for capture frames)
            if not do_capture:
                continue

            face_crop_capture = _crop_face(frame_bgr, face_row[:4].astype(int), scale=2.7)
            if face_crop_capture.size == 0:
                self.capture_complete.emit(False, None, 0.0)
                continue

            try:
                liveness = self._liveness_checker.check(face_crop_capture, self._liveness_threshold)
            except LivenessInferenceError:
                self._consecutive_failures += 1
                logger.warning(
                    "[EnrollmentAIWorker] Liveness inference error (%d/%d consecutive)",
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
                self.capture_complete.emit(False, None, 0.0)
                continue

            # Reset consecutive-failure counter on liveness success
            self._consecutive_failures = 0

            if not liveness.is_real:
                self.capture_complete.emit(False, None, liveness.score)
                continue

            emb = self._face_recognizer.get_embedding(frame_bgr, face_row)
            if emb is None:
                self.capture_complete.emit(False, None, liveness.score)
                continue

            self.capture_complete.emit(True, emb, liveness.score)

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
