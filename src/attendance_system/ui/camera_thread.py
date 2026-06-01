"""Background QThread: camera capture + AI pipeline execution."""

from __future__ import annotations

import logging
import queue
import time
from typing import Any

import cv2
import cv2.data  # ensures cv2.data submodule is accessible
import numpy as np
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtGui import QImage

from pathlib import Path
from attendance_system.services.ai_pipeline import FaceRecognizer, LivenessChecker
from attendance_system.services.exceptions import LivenessInferenceError
from attendance_system.core.liveness_tracker import LivenessTracker, compute_iou, IOU_THRESHOLD
from attendance_system.utils.face_utils import _crop_face, _create_face_detector

_AI_FRAME_SKIP = 3       # run full pipeline every N frames (≈10 Hz at 30 fps)
_COOLDOWN_SECONDS = 3.0  # min seconds between two recognitions of the same user
_PAUSE_POLL_INTERVAL_SECONDS = 0.05  # how often the paused loop sleeps before re-checking the flag

# Bounding-box colours in RGB (frame is already RGB after cvtColor)
_COLOR_DETECTING: tuple[int, int, int] = (180, 180, 180)  # gray  – face found, awaiting result
_COLOR_SUCCESS:   tuple[int, int, int] = (0,   220,   0)  # green – recognised
_COLOR_ALERT:     tuple[int, int, int] = (220,   0,   0)  # red   – spoof / unrecognized
_COLOR_UNKNOWN:   tuple[int, int, int] = (255, 255,   0)  # yellow– unknown / unrecognized
_COLOR_LANDMARK:  tuple[int, int, int] = (0, 255, 255)    # cyan  – landmarks

_RESULT_HOLD_FRAMES = 30  # keep result colour for this many display frames (~1 s at 30 fps)
_MAX_CONSECUTIVE_FAILURES = 30  # kill thread if 30 frames in a row fail inference
_READ_RETRY_DELAYS = [1.0, 2.0, 4.0]  # exponential backoff seconds between retries
_MAX_READ_RETRIES = 3

logger = logging.getLogger(__name__)

_SENTINEL = object()


class AIWorker(QThread):
    """
    Worker QThread that performs anti-spoofing and face recognition on a background thread.
    Uses a queue of size 1 for backpressure.
    """
    recognition_result = pyqtSignal(str, int, str, float, object, str)
    inference_warning = pyqtSignal(str)
    camera_error = pyqtSignal(str)

    def __init__(
        self,
        liveness_threshold: float,
        similarity_threshold: float,
        liveness_checker: LivenessChecker,
        face_recognizer: FaceRecognizer,
        parent: Any = None,
    ) -> None:
        super().__init__(parent)
        self._liveness_threshold = liveness_threshold
        self._similarity_threshold = similarity_threshold
        self._liveness_checker = liveness_checker
        self._face_recognizer = face_recognizer
        self._queue: queue.Queue[Any] = queue.Queue(maxsize=1)
        self._running = False
        self._consecutive_failures = 0
        self._last_recognized: dict[int, float] = {}  # user_id -> monotonic timestamp
        self._liveness_tracker = LivenessTracker()

    def submit_task(
        self,
        frame_bgr: np.ndarray,
        frame_rgb: np.ndarray,
        face_row: np.ndarray,
        frame_counter: int,
    ) -> bool:
        """
        Submit a task to the worker queue.
        Numpy arrays MUST be copied to avoid frame buffer overwriting.
        Returns True if submitted, False if queue is full.
        """
        try:
            self._queue.put_nowait((frame_bgr.copy(), frame_rgb.copy(), face_row.copy(), frame_counter))
            return True
        except queue.Full:
            return False

    def is_busy(self) -> bool:
        """Returns True if the worker queue is full (cannot accept new tasks)."""
        return self._queue.qsize() >= self._queue.maxsize

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

            frame_bgr, frame_rgb, face_row, frame_counter = task

            # Extract bbox for liveness
            x, y, w, h = face_row[:4].astype(int)
            face_crop = _crop_face(frame_rgb, (x, y, w, h), scale=2.7)

            # Step 1 — Liveness (MiniFASNet ONNX)
            try:
                liveness = self._liveness_checker.check(face_crop, 0.0)
            except LivenessInferenceError:
                self._consecutive_failures += 1
                logger.warning(
                    "[AIWorker frame %d] Liveness inference error (%d/%d consecutive)",
                    frame_counter,
                    self._consecutive_failures,
                    _MAX_CONSECUTIVE_FAILURES,
                    exc_info=True,
                )
                if self._consecutive_failures >= _MAX_CONSECUTIVE_FAILURES:
                    self.camera_error.emit(
                        f"Liveness model failed after {_MAX_CONSECUTIVE_FAILURES} "
                        "consecutive errors. Vui lòng khởi động lại ứng dụng."
                    )
                    self._running = False
                    break
                self.inference_warning.emit("Lỗi xử lý AI — đang thử lại...")
                continue

            # Reset consecutive-failure counter on success
            self._consecutive_failures = 0

            # ── Temporal smoothing via EMA + Hysteresis tracker ─────────────
            # Feed raw detection + liveness score into the tracker, then look
            # up our face's result from the returned active tracks.
            bbox_float = (float(x), float(y), float(w), float(h))
            tracked_faces = self._liveness_tracker.update([bbox_float], [liveness.score])

            # Find the track that matches our current detection
            state = "SPOOF"
            ema_score = liveness.score
            for tb, ts, tes in tracked_faces:
                if compute_iou(bbox_float, tb) >= IOU_THRESHOLD:
                    state = ts
                    ema_score = tes
                    break

            if state == "SPOOF":
                self.recognition_result.emit("spoof", 0, "", ema_score, None, "")
                continue

            # Step 2 — Recognition (SFace)
            match = self._face_recognizer.identify(frame_bgr, face_row, self._similarity_threshold)
            if match is None:
                self.recognition_result.emit("unrecognized", 0, "", ema_score, 0.0, "")
                continue

            # Per-user cooldown to avoid flooding the DB
            now = time.monotonic()
            if now - self._last_recognized.get(match.user_id, 0.0) < _COOLDOWN_SECONDS:
                continue
            self._last_recognized[match.user_id] = now

            self.recognition_result.emit(
                "success", match.user_id, match.full_name, ema_score, match.similarity,
                match.matched_pose_label,
            )

    def stop(self) -> None:
        self._liveness_tracker.tracks.clear()
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


class CameraThread(QThread):
    """
    Reads frames from a webcam and runs the AI pipeline on a background thread.

    Signals
    -------
    frame_ready(QImage)
        Every captured frame, annotated with bounding boxes, converted to QImage.
    recognition_result(result_type, user_id, full_name, liveness_score, similarity_score)
        result_type: "success" | "spoof" | "unrecognized"
    camera_error(str)
        Emitted if the camera cannot be opened or a read fails.
    """

    frame_ready = pyqtSignal(QImage)
    recognition_result = pyqtSignal(str, int, str, float, object, str)
    camera_error = pyqtSignal(str)
    inference_warning = pyqtSignal(str)

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
        super().__init__(parent)
        self._session_id = session_id
        self._liveness_threshold = liveness_threshold
        self._similarity_threshold = similarity_threshold
        self._liveness_checker = liveness_checker
        self._face_recognizer = face_recognizer
        self._camera_index = camera_index
        self._running = False
        self._paused: bool = False

        # Initialize YuNet detector
        if detector_model_path is None:
            detector_model_path = Path("models") / "face_detection" / "face_detection_yunet_2023mar.onnx"
        self._detector = _create_face_detector(detector_model_path, (640, 480))

        # Bounding-box display state (updated by AI frames, used by every display frame)
        self._detected_faces: np.ndarray | None = None  # YuNet format: [N, 15]
        self._bbox_color: tuple[int, int, int] = _COLOR_DETECTING
        self._result_hold_counter: int = 0

        # Recognition result overlay state (for Vietnamese text via QPainter)
        self._current_result_type: str | None = None  # "success", "spoof", "unrecognized", None
        self._current_result_name: str = ""
        self._current_result_score: float = 0.0

        # Initialize AI worker thread
        self._ai_worker = AIWorker(
            liveness_threshold=self._liveness_threshold,
            similarity_threshold=self._similarity_threshold,
            liveness_checker=self._liveness_checker,
            face_recognizer=self._face_recognizer,
            parent=self,
        )
        self._ai_worker.recognition_result.connect(self._on_recognition_result)
        self._ai_worker.inference_warning.connect(self.inference_warning.emit)
        self._ai_worker.camera_error.connect(self._on_ai_worker_camera_error)

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
        try:
            self._ai_worker.recognition_result.disconnect()
            self._ai_worker.inference_warning.disconnect()
            self._ai_worker.camera_error.disconnect()
        except TypeError:
            pass
        self._ai_worker.stop()
        self.wait()

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
            cap = cv2.VideoCapture(self._camera_index)
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
        cap = cv2.VideoCapture(self._camera_index)
        if not cap.isOpened():
            self.camera_error.emit(f"Cannot open camera (index {self._camera_index})")
            return

        try:
            # Set resolution
            w, h = 640, 480
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, w)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, h)
            
            # Update detector input size to match camera
            self._detector.setInputSize((w, h))

            # Start AI worker thread
            self._ai_worker.start()

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
                    # Reconnected successfully — continue processing this frame

                # YuNet expects BGR for detection, but we want RGB for display
                faces = self._detect_faces(frame)
                self._detected_faces = faces

                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

                # Decay result colour back to gray after hold period
                if self._result_hold_counter > 0:
                    self._result_hold_counter -= 1
                    if self._result_hold_counter == 0:
                        self._bbox_color = _COLOR_DETECTING

                # Draw bboxes onto a copy, then emit the annotated frame
                annotated = self._draw_bboxes(frame_rgb)
                self._emit_display_frame(annotated)

                # Run full AI pipeline asynchronously every N frames (only when faces are present)
                frame_counter += 1
                if frame_counter % _AI_FRAME_SKIP == 0 and self._detected_faces is not None and len(self._detected_faces) > 0:
                    # Skip AI work when queue is full — CPU drops ~30% during AI lag
                    if not self._ai_worker.is_busy():
                        idx = int(np.argmax(self._detected_faces[:, 2] * self._detected_faces[:, 3]))
                        face_row = self._detected_faces[idx]
                        self._ai_worker.submit_task(frame, frame_rgb, face_row, frame_counter)
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
        # Use numpy's buffer directly (avoids intermediate bytes allocation).
        # The QImage wraps external data — it does NOT copy it internally.
        # Qt's queued connection uses shallow copy (implicit sharing), so we
        # must .copy() to own the pixel data before cross-thread emission.
        qimg = QImage(frame_rgb.data, w, h, ch * w, QImage.Format_RGB888)

        # Draw text labels with QPainter (supports Vietnamese Unicode)
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

    def _on_ai_worker_camera_error(self, message: str) -> None:
        self.camera_error.emit(message)
        self._running = False
        # Disconnect worker signals to prevent late emits during cleanup
        try:
            self._ai_worker.recognition_result.disconnect()
            self._ai_worker.inference_warning.disconnect()
            self._ai_worker.camera_error.disconnect()
        except TypeError:
            pass
        self._ai_worker.stop()

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
        self.recognition_result.emit(result_type, user_id, full_name, liveness_score, similarity_score, matched_pose_label)
