"""Camera + AI worker for the face-enrollment flow.

Inherits :class:`ui.camera_worker_base.CameraThreadBase` (plan 0003) and
uses :class:`attendance_system.services.ai_pipeline.AIPipeline` (plan
0004) for per-frame inference.  Liveness and similarity thresholds are
**required** at construction — they come from the resolved
:class:`attendance_system.core.config.SystemConfig`, not local defaults.
See plan 0005 (archived 2026-06-05).
"""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any, NamedTuple

import cv2
import numpy as np
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QImage, QPainter, QColor, QFont

from attendance_system.services.ai_pipeline import AIPipeline, FaceRecognizer, LivenessChecker
from attendance_system.services.exceptions import LivenessInferenceError
from attendance_system.services.head_pose import HeadPoseEstimator
from attendance_system.ui.camera_worker_base import (
    CameraThreadBase, _MAX_CONSECUTIVE_FAILURES, _MAX_READ_RETRIES,
    _COLOR_SUCCESS, _COLOR_ALERT,
)
from attendance_system.ui.enrollment_ai_worker import EnrollmentAIWorker
from attendance_system.utils.face_utils import _crop_face

_COLOR_GUIDE: tuple[int, int, int] = (255, 255, 0)  # Yellow
_POSE_TOLERANCE_DEG = 15.0
_HOLD_FRAMES = 5
_CAPTURE_COOLDOWN = 1.0


class _PoseTarget(NamedTuple):
    name: str
    pitch: float
    yaw: float
    storage_label: str


logger = logging.getLogger(__name__)

# Outside-world pose order: center (frontal), right, left, up, down.
# storage_label matches the DB pose_label values.
_POSE_SEQUENCE = [
    _PoseTarget("Chính diện", 0, 0, "center"),
    _PoseTarget("Nghiêng phải", 0, 30, "right"),
    _PoseTarget("Nghiêng trái", 0, -30, "left"),
    _PoseTarget("Ngửa lên", 20, 0, "up"),
    _PoseTarget("Cúi xuống", -20, 0, "down"),
]


class EnrollmentCameraThread(CameraThreadBase):
    frame_ready = pyqtSignal(QImage)
    capture_progress = pyqtSignal(int, int, str, str, str, str)
    camera_error = pyqtSignal(str)
    enrollment_complete = pyqtSignal(dict)  # dict[str, np.ndarray] — pose_label -> embedding
    inference_warning = pyqtSignal(str)
    sample_captured = pyqtSignal(int)  # current count after capture

    def __init__(
        self,
        camera_index: int,
        liveness_checker: LivenessChecker,
        face_recognizer: FaceRecognizer,
        liveness_threshold: float,
        similarity_threshold: float,
        detector_model_path: Path | str | None = None,
        head_pose_estimator: HeadPoseEstimator | None = None,
        target_count: int = 5,
        capture_cooldown: float = _CAPTURE_COOLDOWN,
        parent: Any = None,
    ) -> None:
        super().__init__(camera_index, detector_model_path, parent)
        self._face_recognizer = face_recognizer
        self._liveness_checker = liveness_checker
        self._head_pose_estimator = head_pose_estimator
        self._target_count = target_count
        self._liveness_threshold = liveness_threshold
        self._similarity_threshold = similarity_threshold
        self._capture_cooldown = capture_cooldown

        # Enrollment state machine
        self._captured_embeddings_by_pose: dict[str, np.ndarray] = {}
        self._current_pose_index = 0
        self._pose_hold_counter = 0
        self._last_capture_time = 0.0
        self._consecutive_failures: int = 0
        self._frame_counter: int = 0

        self._status_text = "Đang khởi tạo..."
        self._angles_text = "-"
        self._hold_text = ""
        self._guidance_text = ""
        self._last_success_time: float = 0.0
        self._current_face_bbox: tuple[int, int, int, int] | None = None

        if self._head_pose_estimator is not None:
            pipeline = AIPipeline(
                liveness_checker=self._liveness_checker,
                face_recognizer=self._face_recognizer,
                head_pose_estimator=self._head_pose_estimator,
                liveness_threshold=self._liveness_threshold,
                similarity_threshold=self._similarity_threshold,
            )
            self._enrollment_ai_worker = EnrollmentAIWorker(
                pipeline=pipeline,
                parent=None,
            )
            self._enrollment_ai_worker.pose_estimated.connect(self._on_pose_estimated)
            self._enrollment_ai_worker.capture_complete.connect(self._on_capture_complete)
            self._enrollment_ai_worker.inference_warning.connect(self.inference_warning.emit)
            self._enrollment_ai_worker.camera_error.connect(self._on_ai_worker_camera_error)
        else:
            self._enrollment_ai_worker = None
        self._capture_in_progress: bool = False

    # ------------------------------------------------------------------
    # Worker lifecycle
    # ------------------------------------------------------------------

    def _cleanup_worker(self) -> None:
        """Disconnect and stop the enrollment AI worker."""
        if self._enrollment_ai_worker is not None:
            try:
                self._enrollment_ai_worker.pose_estimated.disconnect()
                self._enrollment_ai_worker.capture_complete.disconnect()
                self._enrollment_ai_worker.inference_warning.disconnect()
                self._enrollment_ai_worker.camera_error.disconnect()
            except TypeError:
                pass
            self._enrollment_ai_worker.stop()
            self._enrollment_ai_worker = None

    # ------------------------------------------------------------------
    # QThread entry point (fully overridden — different rendering pipeline)
    # ------------------------------------------------------------------

    def run(self) -> None:
        cap = cv2.VideoCapture(self._camera_index)
        if not cap.isOpened():
            self.camera_error.emit(f"Cannot open camera (index {self._camera_index})")
            return

        w, h = 640, 480
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, w)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, h)
        self._detector.setInputSize((w, h))

        self._running = True
        self._captured_embeddings_by_pose = {}
        self._current_pose_index = 0
        self._pose_hold_counter = 0
        self._last_capture_time = 0.0
        self._capture_in_progress = False
        self._consecutive_failures = 0
        self._frame_counter = 0
        self._last_success_time = 0.0
        self._current_face_bbox = None
        self._sync_progress()

        # Start EnrollmentAIWorker (created in __init__)
        if self._enrollment_ai_worker is not None:
            self._enrollment_ai_worker.start()

        while self._running:
            self._frame_counter += 1
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

            _, faces = self._detector.detect(frame)
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            guide_color = _COLOR_GUIDE

            if faces is not None and len(faces) > 0:
                idx = int(np.argmax(faces[:, 2] * faces[:, 3]))
                face = faces[idx]
                x, y, w_face, h_face = face[:4].astype(int)
                self._current_face_bbox = (x, y, w_face, h_face)

                if self._head_pose_estimator is None:
                    self._handle_legacy_frame(frame, frame_rgb, face, x, y, w_face, h_face)
                    guide_color = self._frame_color_from_status()
                else:
                    guide_color = self._handle_pose_frame(frame, face, x, y, w_face, h_face)

                cv2.rectangle(frame_rgb, (x, y), (x + w_face, y + h_face), guide_color, 2)
            else:
                self._status_text = "Không tìm thấy khuôn mặt"
                self._angles_text = "-"
                self._hold_text = ""
                self._guidance_text = "Đưa khuôn mặt vào khung"
                self._current_face_bbox = None

            qimg = self._draw_status(frame_rgb)
            self._emit_frame(qimg)
            self._sync_progress()

            if self._status_text == "Hoàn tất!":
                time.sleep(1.0)
                break

        cap.release()

    # ------------------------------------------------------------------
    # Legacy path (no head-pose estimator)
    # ------------------------------------------------------------------

    def _handle_legacy_frame(
        self,
        frame_bgr: np.ndarray,
        frame_rgb: np.ndarray,
        face: np.ndarray,
        x: int,
        y: int,
        w_face: int,
        h_face: int,
    ) -> None:
        eye_l, eye_r, nose = face[5:15].reshape(5, 2)[:3]
        eye_dist = eye_r[0] - eye_l[0]
        if eye_dist > 0:
            ratio = (nose[0] - eye_l[0]) / eye_dist
            if ratio < 0.4:
                self._status_text = "Xoay sang phải một chút"
            elif ratio > 0.6:
                self._status_text = "Xoay sang trái một chút"
            else:
                self._status_text = "Nhìn thẳng, giữ yên"

        now = time.monotonic()
        if (
            now - self._last_capture_time > self._capture_cooldown
            and len(self._captured_embeddings_by_pose) < self._target_count
        ):
            face_crop = _crop_face(frame_rgb, (x, y, w_face, h_face), scale=2.7)
            try:
                liveness = self._liveness_checker.check(face_crop, self._liveness_threshold)
            except LivenessInferenceError:
                self._consecutive_failures += 1
                logger.warning(
                    "[frame %d] Liveness inference error in legacy path (%d/%d consecutive)",
                    self._frame_counter,
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
                    return
                self.inference_warning.emit("Lỗi xử lý AI — đang thử lại...")
                self._status_text = "Đang xử lý..."
                self._angles_text = "-"
                self._hold_text = ""
                self._guidance_text = "Đưa khuôn mặt vào khung"
                return

            self._consecutive_failures = 0

            if liveness.is_real:
                emb = self._face_recognizer.get_embedding(frame_bgr, face)
                if emb is not None:
                    pose_label = _POSE_SEQUENCE[len(self._captured_embeddings_by_pose) % len(_POSE_SEQUENCE)].storage_label
                    self._captured_embeddings_by_pose[pose_label] = emb
                    self._last_success_time = time.monotonic()
                    self.sample_captured.emit(len(self._captured_embeddings_by_pose))
                    self._last_capture_time = now
                    self._status_text = "Đã chụp!"
                    self._angles_text = "-"
                    self._hold_text = ""
                    self._guidance_text = "Tiếp tục giữ khuôn mặt ổn định"
                    if len(self._captured_embeddings_by_pose) >= self._target_count:
                        self.enrollment_complete.emit(self._captured_embeddings_by_pose)
                        self._status_text = "Hoàn tất!"
                else:
                    self._status_text = "Cảnh báo: Không trích xuất được embedding"
            else:
                self._status_text = "Cảnh báo: Liveness failed"
                self._guidance_text = "Giữ khuôn mặt thật trong khung"
                self._angles_text = "-"
                self._hold_text = ""

    # ------------------------------------------------------------------
    # Pose-based path
    # ------------------------------------------------------------------

    def _handle_pose_frame(
        self,
        frame_bgr: np.ndarray,
        face: np.ndarray,
        x: int,
        y: int,
        w_face: int,
        h_face: int,
    ) -> tuple[int, int, int]:
        """Submit frame to EnrollmentAIWorker for async pose estimation.
        Does NOT block — returns guide color based on current state."""
        if self._enrollment_ai_worker is None:
            return _COLOR_GUIDE

        # Decide if we should attempt capture this frame
        now = time.monotonic()
        should_capture = (
            self._pose_hold_counter >= _HOLD_FRAMES
            and now - self._last_capture_time >= self._capture_cooldown
            and not self._capture_in_progress
        )

        if should_capture:
            self._capture_in_progress = True

        # Submit task to worker (non-blocking, returns False if queue full)
        submitted = self._enrollment_ai_worker.submit_task(
            frame_bgr, face, do_capture=should_capture,
        )
        if not submitted and should_capture:
            # Frame dropped due to backpressure — release capture lock
            self._capture_in_progress = False

        return self._frame_color_from_status()

    # ------------------------------------------------------------------
    # Signal handlers
    # ------------------------------------------------------------------

    def _on_pose_estimated(self, pitch: float, yaw: float, roll: float) -> None:
        """Handle pose estimation result from worker. Updates state machine."""
        if self._current_pose_index >= len(_POSE_SEQUENCE):
            return

        target = _POSE_SEQUENCE[self._current_pose_index]

        self._angles_text = (
            f"Pitch: {pitch:.1f}° | Yaw: {yaw:.1f}° | Roll: {roll:.1f}°"
        )

        is_matched = self._pose_matches(target, pitch, yaw)
        if is_matched:
            if self._pose_hold_counter < _HOLD_FRAMES:
                self._pose_hold_counter += 1
            self._hold_text = f"Giữ: {self._pose_hold_counter}/{_HOLD_FRAMES}"
            self._guidance_text = f"Tốt! Giữ yên cho tư thế: {target.name}"
            self._status_text = "Tốt! Giữ yên..."
        else:
            self._pose_hold_counter = 0
            self._hold_text = f"Giữ: 0/{_HOLD_FRAMES}"
            self._guidance_text = self._pose_guidance(target, pitch, yaw)
            self._status_text = self._guidance_text

    def _on_capture_complete(self, success: bool, embedding: object, liveness_score: float) -> None:
        """Handle capture result from worker. Advances state machine on success."""
        self._capture_in_progress = False
        target = _POSE_SEQUENCE[self._current_pose_index % len(_POSE_SEQUENCE)]

        if success and embedding is not None:
            pose_label = target.storage_label
            self._captured_embeddings_by_pose[pose_label] = embedding
            self._last_success_time = time.monotonic()
            self.sample_captured.emit(len(self._captured_embeddings_by_pose))
            self._last_capture_time = time.monotonic()
            self._current_pose_index += 1
            self._pose_hold_counter = 0

            if len(self._captured_embeddings_by_pose) >= self._target_count:
                self.enrollment_complete.emit(self._captured_embeddings_by_pose)
                self._status_text = "Hoàn tất!"
                self._hold_text = f"Giữ: {_HOLD_FRAMES}/{_HOLD_FRAMES}"
                self._guidance_text = "Đã hoàn tất chuỗi tư thế"
            else:
                self._status_text = "Đã chụp!"
                next_target = _POSE_SEQUENCE[self._current_pose_index % len(_POSE_SEQUENCE)]
                self._guidance_text = f"Tiếp theo: {next_target.name}"
                self._hold_text = f"Giữ: 0/{_HOLD_FRAMES}"
        else:
            self._pose_hold_counter = 0
            self._hold_text = f"Giữ: 0/{_HOLD_FRAMES}"
            self._status_text = "Không thể đọc khuôn mặt, thử lại"
            self._guidance_text = f"Giữ tư thế {target.name} và thử lại"

    def _on_ai_worker_camera_error(self, message: str) -> None:
        """Circuit breaker tripped — stop the entire thread."""
        self.camera_error.emit(message)
        self._running = False
        if self._enrollment_ai_worker is not None:
            try:
                self._enrollment_ai_worker.pose_estimated.disconnect()
                self._enrollment_ai_worker.capture_complete.disconnect()
                self._enrollment_ai_worker.inference_warning.disconnect()
                self._enrollment_ai_worker.camera_error.disconnect()
            except TypeError:
                pass
            self._enrollment_ai_worker.stop()
            self._enrollment_ai_worker = None

    # ------------------------------------------------------------------
    # Pose helpers
    # ------------------------------------------------------------------

    def _pose_matches(self, target: _PoseTarget, pitch: float, yaw: float) -> bool:
        return (
            abs(pitch - target.pitch) <= _POSE_TOLERANCE_DEG
            and abs(yaw - target.yaw) <= _POSE_TOLERANCE_DEG
        )

    def _pose_guidance(self, target: _PoseTarget, pitch: float, yaw: float) -> str:
        if yaw - target.yaw > _POSE_TOLERANCE_DEG:
            return "Quay sang phải một chút"
        if yaw - target.yaw < -_POSE_TOLERANCE_DEG:
            return "Quay sang trái một chút"
        if pitch - target.pitch > _POSE_TOLERANCE_DEG:
            return "Cúi xuống một chút"
        if pitch - target.pitch < -_POSE_TOLERANCE_DEG:
            return "Ngửa lên một chút"
        return f"Giữ tư thế: {target.name}"

    # ------------------------------------------------------------------
    # Rendering helpers
    # ------------------------------------------------------------------

    def _frame_color_from_status(self) -> tuple[int, int, int]:
        if "Hoàn tất" in self._status_text or "Đã chụp" in self._status_text:
            return _COLOR_SUCCESS
        if "Cảnh báo" in self._status_text or "Không" in self._status_text:
            return _COLOR_ALERT
        return _COLOR_GUIDE

    def _sync_progress(self) -> None:
        self.capture_progress.emit(
            len(self._captured_embeddings_by_pose),
            self._target_count,
            self._status_text,
            self._angles_text,
            self._hold_text,
            self._guidance_text,
        )

    def _draw_status(self, frame_rgb: np.ndarray) -> QImage:
        h, w, ch = frame_rgb.shape
        qimg = QImage(frame_rgb.tobytes(), w, h, ch * w, QImage.Format_RGB888).copy()

        painter = QPainter(qimg)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.TextAntialiasing)

        # --- Success effects ---
        elapsed = time.monotonic() - self._last_success_time
        is_final = len(self._captured_embeddings_by_pose) >= self._target_count

        # Flash effect: white overlay with decaying alpha over 200ms
        if 0 < elapsed <= 0.2:
            flash_alpha = int(255 * 0.4 * (1.0 - elapsed / 0.2))
            painter.fillRect(0, 0, w, h, QColor(255, 255, 255, flash_alpha))

        # Checkmark / final effect: lasts 800ms
        if 0 < elapsed <= 0.8 and self._current_face_bbox is not None:
            x, y, fw, fh = self._current_face_bbox

            if is_final:
                # Green tint overlay + big completion text
                painter.fillRect(0, 0, w, h, QColor(0, 255, 0, 25))
                font_big = QFont("Arial", 38, QFont.Bold)
                painter.setFont(font_big)
                painter.setPen(QColor(0, 255, 0))
                painter.drawText(0, 0, w, h, Qt.AlignmentFlag.AlignCenter, "🎉 Hoàn tất!")
            else:
                # Green checkmark at top-right of face bbox
                check_size = int(50 * min(1.0, elapsed / 0.2))  # scale 0→1 over 200ms
                font_check = QFont("Arial", max(1, check_size), QFont.Bold)
                painter.setFont(font_check)
                painter.setPen(QColor(0, 255, 0))
                painter.drawText(x + fw - check_size, y - 8, "✓")

        # --- Status text ---
        def draw_text_with_shadow(text, x, y, size, bold=False):
            font = QFont("Arial", size)
            if bold:
                font.setWeight(QFont.Bold)
            painter.setFont(font)

            # Shadow
            painter.setPen(QColor(0, 0, 0))
            painter.drawText(x + 2, y + 2, text)

            # Foreground
            painter.setPen(QColor(255, 255, 255))
            painter.drawText(x, y, text)

        if self._status_text:
            draw_text_with_shadow(self._status_text, 20, 40, 20, True)

        if self._angles_text and self._angles_text != "-":
            draw_text_with_shadow(self._angles_text, 20, 70, 16)

        if self._hold_text:
            draw_text_with_shadow(self._hold_text, 20, 100, 16)

        if self._guidance_text:
            draw_text_with_shadow(self._guidance_text, 20, 130, 16)

        painter.end()
        return qimg

    def _emit_frame(self, qimg: QImage) -> None:
        self.frame_ready.emit(qimg.copy())
