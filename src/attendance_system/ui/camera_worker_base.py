"""Base classes for camera capture and AI worker threads.

CameraThreadBase(QThread)  — shared camera capture infrastructure.
AIWorkerBase(QThread)      — shared AI inference worker with queue and circuit-breaker.
"""

from __future__ import annotations

import logging
import queue
import time
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtGui import QImage

from attendance_system.utils.face_utils import _create_face_detector

# ---------------------------------------------------------------------------
# CameraThreadBase constants
# ---------------------------------------------------------------------------
_PAUSE_POLL_INTERVAL_SECONDS = 0.05
_MAX_CONSECUTIVE_FAILURES = 30
_READ_RETRY_DELAYS = [1.0, 2.0, 4.0]
_MAX_READ_RETRIES = 3

_COLOR_DETECTING: tuple[int, int, int] = (180, 180, 180)
_COLOR_SUCCESS:   tuple[int, int, int] = (0,   220,   0)
_COLOR_ALERT:     tuple[int, int, int] = (220,   0,   0)
_COLOR_UNKNOWN:   tuple[int, int, int] = (255, 255,   0)
_COLOR_LANDMARK:  tuple[int, int, int] = (0, 255, 255)
_RESULT_HOLD_FRAMES = 30

# ---------------------------------------------------------------------------
# AIWorkerBase constants
# ---------------------------------------------------------------------------
_SENTINEL = object()

logger = logging.getLogger(__name__)


class CameraThreadBase(QThread):
    """Base camera-capture thread.

    Subclasses override :meth:`_process_frame` to implement per-frame AI
    pipeline logic, and :meth:`_cleanup_worker` to disconnect AI worker
    signals.
    """

    frame_ready = pyqtSignal(QImage)
    camera_error = pyqtSignal(str)
    inference_warning = pyqtSignal(str)

    def __init__(
        self,
        camera_index: int,
        detector_model_path: Path | str | None = None,
        parent: Any = None,
    ) -> None:
        super().__init__(parent)
        self._camera_index = camera_index

        # Initialise YuNet detector
        if detector_model_path is None:
            detector_model_path = (
                Path("models") / "face_detection" / "face_detection_yunet_2023mar.onnx"
            )
        self._detector = _create_face_detector(detector_model_path, (640, 480))

        # Bounding-box display state
        self._detected_faces: np.ndarray | None = None
        self._bbox_color: tuple[int, int, int] = _COLOR_DETECTING
        self._result_hold_counter: int = 0

        # Recognition result overlay state
        self._current_result_type: str | None = None
        self._current_result_name: str = ""
        self._current_result_score: float = 0.0

        self._running = False
        self._paused: bool = False

    # ------------------------------------------------------------------
    # Public control
    # ------------------------------------------------------------------

    def pause(self) -> None:
        """Pause frame capture. The main loop will sleep-skip until resumed."""
        self._paused = True

    def resume(self) -> None:
        """Resume frame capture after a pause."""
        self._paused = False

    def stop(self) -> None:
        """Signal the thread to exit and block until it finishes."""
        self._running = False
        self._cleanup_worker()
        self.wait()

    def _cleanup_worker(self) -> None:
        """Disconnect and stop the child AI worker. Override if worker signals differ."""
        pass  # Subclasses override to disconnect their specific worker signals

    # ------------------------------------------------------------------
    # Camera retry
    # ------------------------------------------------------------------

    def _retry_read(self, cap: cv2.VideoCapture) -> tuple[bool, cv2.VideoCapture, np.ndarray | None]:
        """Reconnect camera with exponential backoff.

        Returns (success, cap, frame) where cap may be a new VideoCapture.
        """
        for attempt, delay in enumerate(_READ_RETRY_DELAYS, 1):
            logger.warning(
                "Camera read failed. Reconnecting in %ds (attempt %d/%d)...",
                delay, attempt, _MAX_READ_RETRIES,
            )
            time.sleep(delay)
            if not self._running:
                return False, cap, None
            cap.release()
            cap = cv2.VideoCapture(self._camera_index, cv2.CAP_DSHOW)
            if not cap.isOpened():
                continue
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            ret, frame = cap.read()
            if ret:
                return True, cap, frame
        return False, cap, None

    # ------------------------------------------------------------------
    # QThread entry point
    # ------------------------------------------------------------------

    def run(self) -> None:
        cap = cv2.VideoCapture(self._camera_index, cv2.CAP_DSHOW)
        if not cap.isOpened():
            self.camera_error.emit(f"Cannot open camera (index {self._camera_index})")
            return

        try:
            w, h = 640, 480
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, w)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, h)
            self._detector.setInputSize((w, h))

            self._running = True
            frame_counter = 0

            while self._running:
                if self._paused:
                    time.sleep(_PAUSE_POLL_INTERVAL_SECONDS)
                    continue

                ret, frame = cap.read()
                if not ret:
                    success, cap, frame = self._retry_read(cap)
                    if not success:
                        self.camera_error.emit(
                            f"Camera read failed after {_MAX_READ_RETRIES} attempts."
                        )
                        break

                # Mirror horizontally so user sees themselves like in a mirror
                frame = cv2.flip(frame, 1)

                faces = self._detect_faces(frame)
                self._detected_faces = faces
                frame_counter += 1

                # Decay result colour
                if self._result_hold_counter > 0:
                    self._result_hold_counter -= 1
                    if self._result_hold_counter == 0:
                        self._bbox_color = _COLOR_DETECTING

                self._process_frame(frame, faces, frame_counter)

        finally:
            cap.release()

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _detect_faces(self, frame_bgr: np.ndarray) -> np.ndarray | None:
        """Return YuNet detection results [N, 15] or None."""
        _, faces = self._detector.detect(frame_bgr)
        return faces

    def _draw_bboxes(self, frame_rgb: np.ndarray) -> np.ndarray:
        """Return a copy of the frame with coloured bounding boxes and landmarks drawn."""
        if self._detected_faces is None:
            return frame_rgb

        out = frame_rgb.copy()
        for face in self._detected_faces:
            # 1. Bounding box
            x, y, w, h = face[:4].astype(int)
            cv2.rectangle(out, (x, y), (x + w, y + h), self._bbox_color, 2)

            # 2. Landmarks (5 dots: eyes, nose, mouth corners)
            landmarks = face[4:14].reshape(5, 2).astype(int)
            for lx, ly in landmarks:
                cv2.circle(out, (lx, ly), 3, _COLOR_LANDMARK, -1)

        return out

    def _emit_display_frame(self, frame_rgb: np.ndarray) -> None:
        h, w, ch = frame_rgb.shape
        qimg = QImage(frame_rgb.data, w, h, ch * w, QImage.Format_RGB888)
        annotated = self._annotate_frame(qimg)
        self.frame_ready.emit(annotated.copy())

    def _annotate_frame(self, qimg: QImage) -> QImage:
        """Draw result text labels on the QImage using QPainter (supports Vietnamese)."""
        from PyQt5.QtGui import QPainter, QColor, QFont

        painter = QPainter(qimg)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        if self._detected_faces is not None and self._current_result_type is not None:
            for face in self._detected_faces:
                x, y, w, h = face[:4].astype(int)

                # Background pill behind text
                painter.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))

                if self._current_result_type == "success" and self._current_result_name:
                    label = f"{self._current_result_name} ({self._current_result_score:.2f})"
                    painter.setPen(QColor(22, 163, 74))  # green
                    # Draw text background
                    text_rect = painter.fontMetrics().boundingRect(label)
                    text_x, text_y = x, max(y - 8, 0)
                    painter.fillRect(text_x, text_y - text_rect.height() - 4,
                                     text_rect.width() + 12, text_rect.height() + 6,
                                     QColor(255, 255, 255, 200))
                    # Draw text
                    painter.drawText(text_x + 6, text_y - 4, label)

                elif self._current_result_type == "spoof":
                    label = "\U0001f6ab Gi\u1ea3 m\u1ea1o"
                    painter.setPen(QColor(220, 0, 0))  # red
                    text_rect = painter.fontMetrics().boundingRect(label)
                    text_x, text_y = x, max(y - 8, 0)
                    painter.fillRect(text_x, text_y - text_rect.height() - 4,
                                     text_rect.width() + 12, text_rect.height() + 6,
                                     QColor(255, 255, 255, 200))
                    painter.drawText(text_x + 6, text_y - 4, label)

                elif self._current_result_type == "unrecognized":
                    label = "\u274c Kh\u00f4ng nh\u1eadn di\u1ec7n \u0111\u01b0\u1ee3c"
                    painter.setPen(QColor(234, 179, 8))  # yellow/amber
                    text_rect = painter.fontMetrics().boundingRect(label)
                    text_x, text_y = x, max(y - 8, 0)
                    painter.fillRect(text_x, text_y - text_rect.height() - 4,
                                     text_rect.width() + 12, text_rect.height() + 6,
                                     QColor(255, 255, 255, 200))
                    painter.drawText(text_x + 6, text_y - 4, label)

        painter.end()
        return qimg

    # ------------------------------------------------------------------
    # Abstract hook for subclasses
    # ------------------------------------------------------------------

    def _process_frame(
        self, frame: np.ndarray, faces: np.ndarray | None, frame_counter: int
    ) -> None:
        """Per-frame processing. Subclasses implement their specific logic."""
        raise NotImplementedError


class AIWorkerBase(QThread):
    """Base AI worker thread.

    Processes tasks from a queue of size 1 (backpressure) and implements a
    circuit-breaker pattern for consecutive inference failures.

    Subclasses override :meth:`_process_frame` and :meth:`_inference_error_types`.
    """

    inference_warning = pyqtSignal(str)
    camera_error = pyqtSignal(str)

    def __init__(
        self,
        pipeline: Any,
        parent: Any = None,
    ) -> None:
        super().__init__(parent)
        self._pipeline = pipeline
        self._queue: queue.Queue[Any] = queue.Queue(maxsize=1)
        self._running = False
        self._consecutive_failures = 0

    def submit_task(self, *args) -> bool:
        """Submit a task to the worker queue. Numpy arrays are auto-copied."""
        copied = tuple(a.copy() if isinstance(a, np.ndarray) else a for a in args)
        try:
            self._queue.put_nowait(copied)
            return True
        except queue.Full:
            return False

    def is_busy(self) -> bool:
        """Returns True if the worker queue is full (cannot accept new tasks)."""
        return self._queue.qsize() >= self._queue.maxsize

    # ------------------------------------------------------------------
    # QThread entry point
    # ------------------------------------------------------------------

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

            try:
                self._process_frame(task)
            except self._inference_error_types():
                self._consecutive_failures += 1
                logger.warning(
                    "[%s] Inference error (%d/%d consecutive)",
                    type(self).__name__,
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
                self._on_inference_error(task)
                continue

            self._consecutive_failures = 0

    # ------------------------------------------------------------------
    # Hooks for subclasses
    # ------------------------------------------------------------------

    def _inference_error_types(self) -> tuple:
        """Return exception types that trigger circuit-breaker. Override in subclass."""
        return ()

    def _process_frame(self, task) -> None:
        """Process a single task. Subclasses must override."""
        raise NotImplementedError

    def _on_inference_error(self, task) -> None:
        """Called when inference raises a caught exception. Override for custom error signals."""
        self.inference_warning.emit("Lỗi xử lý AI — đang thử lại...")

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

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
