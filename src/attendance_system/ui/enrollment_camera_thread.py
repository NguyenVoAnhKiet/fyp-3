from __future__ import annotations

import time
from typing import Any

import cv2
import numpy as np
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtGui import QImage

from pathlib import Path
from attendance_system.services.ai_pipeline import FaceRecognizer, LivenessChecker

_COLOR_GUIDE: tuple[int, int, int] = (255, 255, 0)  # Yellow
_COLOR_SUCCESS: tuple[int, int, int] = (0, 255, 0)   # Green
_COLOR_ALERT: tuple[int, int, int] = (255, 0, 0)     # Red

class EnrollmentCameraThread(QThread):
    """
    Background thread for face enrollment.
    Handles camera capture, face detection, liveness check, and auto-capture of 5 frames.
    """
    frame_ready = pyqtSignal(QImage)
    capture_progress = pyqtSignal(int)
    enrollment_complete = pyqtSignal(np.ndarray)
    camera_error = pyqtSignal(str)

    def __init__(
        self,
        camera_index: int,
        liveness_checker: LivenessChecker,
        face_recognizer: FaceRecognizer,
        liveness_threshold: float = 0.5,
        detector_model_path: Path | str | None = None,
        parent: Any = None,
    ) -> None:
        super().__init__(parent)
        self._camera_index = camera_index
        self._liveness_checker = liveness_checker
        self._face_recognizer = face_recognizer
        self._liveness_threshold = liveness_threshold
        self._running = False
        
        if detector_model_path is None:
            detector_model_path = Path("models") / "face_detection" / "face_detection_yunet_2023mar.onnx"
        
        self._detector = cv2.FaceDetectorYN.create(
            str(detector_model_path), "", (640, 480), score_threshold=0.8, nms_threshold=0.3
        )
        
        self._captured_embeddings: list[np.ndarray] = []
        self._target_count = 5
        self._status_text = "Đang khởi động..."
        self._last_capture_time = 0.0
        self._capture_cooldown = 1.0 # seconds between captures to ensure variety

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
        self.capture_progress.emit(0)

        while self._running:
            ret, frame = cap.read()
            if not ret:
                self.camera_error.emit("Camera read failed.")
                break

            _, faces = self._detector.detect(frame)
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            guide_color = _COLOR_GUIDE
            
            if faces is not None and len(faces) > 0:
                # Process largest face
                idx = int(np.argmax(faces[:, 2] * faces[:, 3]))
                face = faces[idx]
                
                # Check for "steady/centered" face
                x, y, w_face, h_face = face[:4].astype(int)
                landmarks = face[4:14].reshape(5, 2)
                
                # Simple guidance logic based on nose position relative to eyes
                eye_l, eye_r, nose = landmarks[0], landmarks[1], landmarks[2]
                eye_dist = eye_r[0] - eye_l[0]
                if eye_dist > 0:
                    ratio = (nose[0] - eye_l[0]) / eye_dist
                    if ratio < 0.4:
                        self._status_text = "Xoay sang phải một chút"
                    elif ratio > 0.6:
                        self._status_text = "Xoay sang trái một chút"
                    else:
                        self._status_text = "Nhìn thẳng, giữ yên"
                
                # Attempt capture if steady and cooldown passed
                now = time.monotonic()
                if now - self._last_capture_time > self._capture_cooldown and len(self._captured_embeddings) < self._target_count:
                    # Liveness check
                    face_crop = self._crop_face(frame_rgb, (x, y, w_face, h_face))
                    liveness = self._liveness_checker.check(face_crop, self._liveness_threshold)
                    
                    if liveness.is_real:
                        emb = self._face_recognizer.get_embedding(frame, face)
                        if emb is not None:
                            self._captured_embeddings.append(emb)
                            self._last_capture_time = now
                            self.capture_progress.emit(len(self._captured_embeddings))
                            guide_color = _COLOR_SUCCESS
                            
                            if len(self._captured_embeddings) >= self._target_count:
                                avg_emb = self._face_recognizer.average_embeddings(self._captured_embeddings)
                                self.enrollment_complete.emit(avg_emb)
                                self._status_text = "Hoàn tất!"
                                # Don't break immediately so user sees the "Hoàn tất" frame
                    else:
                        self._status_text = "Cảnh báo: Liveness failed"
                        guide_color = _COLOR_ALERT

                # Draw overlay
                cv2.rectangle(frame_rgb, (x, y), (x + w_face, y + h_face), guide_color, 2)
            else:
                self._status_text = "Không tìm thấy khuôn mặt"

            # Draw status text overlay
            self._draw_status(frame_rgb)
            
            # Emit frame
            self._emit_frame(frame_rgb)
            
            if self._status_text == "Hoàn tất!":
                time.sleep(1.0) # Show success message for a bit
                break

        cap.release()

    def _crop_face(self, frame_rgb: np.ndarray, bbox: tuple[int, int, int, int]) -> np.ndarray:
        x, y, w, h = bbox
        cx, cy = x + w // 2, y + h // 2
        side = int(max(w, h) * 2.7)
        half = side // 2
        fh, fw = frame_rgb.shape[:2]
        x1, y1 = max(0, cx - half), max(0, cy - half)
        x2, y2 = min(fw, cx + half), min(fh, cy + half)
        return frame_rgb[y1:y2, x1:x2]

    def _draw_status(self, frame: np.ndarray) -> None:
        # Text shadow for readability
        cv2.putText(frame, self._status_text, (22, 42), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)
        cv2.putText(frame, self._status_text, (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        
        count_text = f"Buffer: {len(self._captured_embeddings)}/{self._target_count}"
        cv2.putText(frame, count_text, (22, 72), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
        cv2.putText(frame, count_text, (20, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

    def _emit_frame(self, frame_rgb: np.ndarray) -> None:
        h, w, ch = frame_rgb.shape
        qimg = QImage(frame_rgb.tobytes(), w, h, ch * w, QImage.Format_RGB888)
        self.frame_ready.emit(qimg.copy())
