from __future__ import annotations

import time
from pathlib import Path
from typing import Any, NamedTuple

import cv2
import numpy as np
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtGui import QImage, QPainter, QColor, QFont

from attendance_system.services.ai_pipeline import FaceRecognizer, LivenessChecker
from attendance_system.services.head_pose import HeadPoseEstimator
from attendance_system.utils.face_utils import _crop_face, _create_face_detector

_COLOR_GUIDE: tuple[int, int, int] = (255, 255, 0)  # Yellow
_COLOR_SUCCESS: tuple[int, int, int] = (0, 255, 0)   # Green
_COLOR_ALERT: tuple[int, int, int] = (255, 0, 0)     # Red
_POSE_TOLERANCE_DEG = 15.0
_HOLD_FRAMES = 5
_CAPTURE_COOLDOWN = 1.0

class _PoseTarget(NamedTuple):
    name: str
    pitch: float
    yaw: float

_POSE_SEQUENCE = [
    _PoseTarget("Chính diện", 0, 0),
    _PoseTarget("Nghiêng trái", 0, -30),  # Model outputs negative yaw when user turns left
    _PoseTarget("Nghiêng phải", 0, 30),   # Model outputs positive yaw when user turns right
    _PoseTarget("Ngửa lên", 20, 0),
    _PoseTarget("Cúi xuống", -20, 0),
]

class EnrollmentCameraThread(QThread):
    frame_ready = pyqtSignal(QImage)
    capture_progress = pyqtSignal(int, int, str, str, str, str)
    camera_error = pyqtSignal(str)
    enrollment_complete = pyqtSignal(np.ndarray)

    def __init__(
        self,
        camera_index: int,
        liveness_checker: LivenessChecker,
        face_recognizer: FaceRecognizer,
        liveness_threshold: float = 0.5,
        detector_model_path: Path | str | None = None,
        head_pose_estimator: HeadPoseEstimator | None = None,
        target_count: int = 5,
        detector: Any | None = None,
        capture_cooldown: float = _CAPTURE_COOLDOWN,
        parent: Any = None,
    ) -> None:
        super().__init__(parent)
        self._camera_index = camera_index
        if detector is not None:
            self._detector = detector
        else:
            if detector_model_path is None:
                detector_model_path = Path("models") / "face_detection" / "face_detection_yunet_2023mar.onnx"
            self._detector = _create_face_detector(detector_model_path, (640, 480))
        self._face_recognizer = face_recognizer
        self._liveness_checker = liveness_checker
        self._head_pose_estimator = head_pose_estimator
        self._target_count = target_count
        self._liveness_threshold = liveness_threshold
        self._capture_cooldown = capture_cooldown

        self._running = False
        self._captured_embeddings: list[np.ndarray] = []
        self._current_pose_index = 0
        self._pose_hold_counter = 0
        self._last_capture_time = 0.0

        self._status_text = "Đang khởi động..."
        self._angles_text = "-"
        self._hold_text = ""
        self._guidance_text = ""

    def stop(self) -> None:
        self._running = False
        self.wait()

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
        self._captured_embeddings = []
        self._current_pose_index = 0
        self._pose_hold_counter = 0
        self._last_capture_time = 0.0
        self._sync_progress()

        while self._running:
            ret, frame = cap.read()
            if not ret:
                self.camera_error.emit("Camera read failed.")
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

            qimg = self._draw_status(frame_rgb)
            self._emit_frame(qimg)
            self._sync_progress()

            if self._status_text == "Hoàn tất!":
                time.sleep(1.0)
                break

        cap.release()

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
            and len(self._captured_embeddings) < self._target_count
        ):
            face_crop = _crop_face(frame_rgb, (x, y, w_face, h_face), scale=2.7)
            liveness = self._liveness_checker.check(face_crop, self._liveness_threshold)

            if liveness.is_real:
                emb = self._face_recognizer.get_embedding(frame_bgr, face)
                if emb is not None:
                    self._captured_embeddings.append(emb)
                    self._last_capture_time = now
                    self._status_text = "Đã chụp!"
                    self._angles_text = "-"
                    self._hold_text = ""
                    self._guidance_text = "Tiếp tục giữ khuôn mặt ổn định"
                    if len(self._captured_embeddings) >= self._target_count:
                        avg_emb = self._face_recognizer.average_embeddings(self._captured_embeddings)
                        self.enrollment_complete.emit(avg_emb)
                        self._status_text = "Hoàn tất!"
                else:
                    self._status_text = "Cảnh báo: Không trích xuất được embedding"
            else:
                self._status_text = "Cảnh báo: Liveness failed"
                self._guidance_text = "Giữ khuôn mặt thật trong khung"
                self._angles_text = "-"
                self._hold_text = ""

    def _handle_pose_frame(
        self,
        frame_bgr: np.ndarray,
        face: np.ndarray,
        x: int,
        y: int,
        w_face: int,
        h_face: int,
    ) -> tuple[int, int, int]:
        target = _POSE_SEQUENCE[self._current_pose_index % len(_POSE_SEQUENCE)]
        face_crop = _crop_face(frame_bgr, (x, y, w_face, h_face))
        if face_crop.size == 0:
            self._status_text = "Không thể đọc khuôn mặt"
            self._angles_text = "-"
            self._hold_text = f"Giữ: {self._pose_hold_counter}/{_HOLD_FRAMES}"
            self._guidance_text = f"Thực hiện: {target.name}"
            return _COLOR_ALERT

        pitch, yaw, roll = self._head_pose_estimator.estimate(face_crop)
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

        if is_matched and self._pose_hold_counter >= _HOLD_FRAMES:
            now = time.monotonic()
            if now - self._last_capture_time >= self._capture_cooldown:
                self._last_capture_time = now
                success = self._attempt_pose_capture(frame_bgr, face, target)
                if success:
                    self._current_pose_index += 1
                    self._pose_hold_counter = 0
                    self._last_capture_time = now
                    if len(self._captured_embeddings) >= self._target_count:
                        self._status_text = "Hoàn tất!"
                        self._hold_text = f"Giữ: {_HOLD_FRAMES}/{_HOLD_FRAMES}"
                        self._guidance_text = "Đã hoàn tất chuỗi tư thế"
                        return _COLOR_SUCCESS
                    self._status_text = "Đã chụp!"
                    self._guidance_text = f"Tiếp theo: {_POSE_SEQUENCE[self._current_pose_index % len(_POSE_SEQUENCE)].name}"
                    self._hold_text = f"Giữ: 0/{_HOLD_FRAMES}"
                    return _COLOR_SUCCESS
                self._pose_hold_counter = 0
                self._hold_text = f"Giữ: 0/{_HOLD_FRAMES}"
                self._status_text = "Không thể đọc khuôn mặt, thử lại"
                self._guidance_text = f"Giữ tư thế {target.name} và thử lại"

        return _COLOR_SUCCESS if is_matched else _COLOR_ALERT

    def _attempt_pose_capture(
        self,
        frame_bgr: np.ndarray,
        face: np.ndarray,
        target: _PoseTarget,
    ) -> bool:
        face_crop = _crop_face(frame_bgr, face[:4].astype(int), scale=2.7)
        liveness = self._liveness_checker.check(face_crop, self._liveness_threshold)
        if not liveness.is_real:
            self._status_text = "Cảnh báo: Liveness failed"
            self._guidance_text = f"Giữ tư thế {target.name} và thử lại"
            return False

        emb = self._face_recognizer.get_embedding(frame_bgr, face)
        if emb is None:
            self._status_text = "Cảnh báo: Không trích xuất được embedding"
            self._guidance_text = f"Giữ tư thế {target.name} và thử lại"
            return False

        self._captured_embeddings.append(emb)
        if len(self._captured_embeddings) >= self._target_count:
            avg_emb = self._face_recognizer.average_embeddings(self._captured_embeddings)
            self.enrollment_complete.emit(avg_emb)
        return True

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

    def _frame_color_from_status(self) -> tuple[int, int, int]:
        if "Hoàn tất" in self._status_text or "Đã chụp" in self._status_text:
            return _COLOR_SUCCESS
        if "Cảnh báo" in self._status_text or "Không" in self._status_text:
            return _COLOR_ALERT
        return _COLOR_GUIDE

    def _sync_progress(self) -> None:
        self.capture_progress.emit(
            len(self._captured_embeddings),
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
            draw_text_with_shadow(self._status_text, 20, 40, 18, True)

        if self._angles_text and self._angles_text != "-":
            draw_text_with_shadow(self._angles_text, 20, 70, 14)

        if self._hold_text:
            draw_text_with_shadow(self._hold_text, 20, 100, 14)

        if self._guidance_text:
            draw_text_with_shadow(self._guidance_text, 20, 130, 14)

        painter.end()
        return qimg

    def _emit_frame(self, qimg: QImage) -> None:
        self.frame_ready.emit(qimg.copy())
