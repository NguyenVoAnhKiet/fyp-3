"""Background QThread: camera capture + AI pipeline execution."""

from __future__ import annotations

import time
from typing import Any

import cv2
import cv2.data  # ensures cv2.data submodule is accessible
import numpy as np
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtGui import QImage

from pathlib import Path
from attendance_system.services.ai_pipeline import FaceRecognizer, LivenessChecker

_AI_FRAME_SKIP = 3       # run full pipeline every N frames (≈10 Hz at 30 fps)
_COOLDOWN_SECONDS = 3.0  # min seconds between two recognitions of the same user

# Bounding-box colours in RGB (frame is already RGB after cvtColor)
_COLOR_DETECTING: tuple[int, int, int] = (180, 180, 180)  # gray  – face found, awaiting result
_COLOR_SUCCESS:   tuple[int, int, int] = (0,   220,   0)  # green – recognised
_COLOR_ALERT:     tuple[int, int, int] = (220,   0,   0)  # red   – spoof / unrecognized
_COLOR_UNKNOWN:   tuple[int, int, int] = (255, 255,   0)  # yellow– unknown / unrecognized
_COLOR_LANDMARK:  tuple[int, int, int] = (0, 255, 255)    # cyan  – landmarks

_RESULT_HOLD_FRAMES = 30  # keep result colour for this many display frames (~1 s at 30 fps)


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
    recognition_result = pyqtSignal(str, int, str, float, float)
    camera_error = pyqtSignal(str)

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
        self._last_recognized: dict[int, float] = {}  # user_id -> monotonic timestamp

        # Initialize YuNet detector
        if detector_model_path is None:
            detector_model_path = Path("models") / "face_detection" / "face_detection_yunet_2023mar.onnx"
        
        # FaceDetectorYN.create(model, config, input_size, score_threshold, nms_threshold, top_k)
        # We'll set input_size during the first frame read in run()
        self._detector = cv2.FaceDetectorYN.create(
            str(detector_model_path), "", (640, 480), score_threshold=0.8, nms_threshold=0.3
        )

        # Bounding-box display state (updated by AI frames, used by every display frame)
        self._detected_faces: np.ndarray | None = None  # YuNet format: [N, 15]
        self._bbox_color: tuple[int, int, int] = _COLOR_DETECTING
        self._result_hold_counter: int = 0

    # ------------------------------------------------------------------
    # Public control
    # ------------------------------------------------------------------

    def stop(self) -> None:
        """Signal the thread to exit and block until it finishes."""
        self._running = False
        self.wait()

    # ------------------------------------------------------------------
    # QThread entry point
    # ------------------------------------------------------------------

    def run(self) -> None:
        cap = cv2.VideoCapture(self._camera_index)
        if not cap.isOpened():
            self.camera_error.emit(f"Cannot open camera (index {self._camera_index})")
            return

        # Set resolution
        w, h = 640, 480
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, w)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, h)
        
        # Update detector input size to match camera
        self._detector.setInputSize((w, h))

        self._running = True
        frame_counter = 0

        while self._running:
            ret, frame = cap.read()
            if not ret:
                self.camera_error.emit("Camera read failed — check connection.")
                break

            # YuNet expects BGR for detection, but we want RGB for display
            # Actually FaceDetectorYN expects BGR by default
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

            # Run full AI pipeline every N frames (only when faces are present)
            frame_counter += 1
            if frame_counter % _AI_FRAME_SKIP == 0 and self._detected_faces is not None:
                self._process_frame(frame, frame_rgb)

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
        qimg = QImage(frame_rgb.tobytes(), w, h, ch * w, QImage.Format_RGB888)
        self.frame_ready.emit(qimg.copy())

    def _crop_face(
        self, frame_rgb: np.ndarray, bbox: tuple[int, int, int, int], scale: float = 2.7
    ) -> np.ndarray:
        """Return a padded crop of the face region specified by *bbox*."""
        x, y, w, h = bbox
        cx, cy = x + w // 2, y + h // 2
        side = int(max(w, h) * scale)
        half = side // 2
        
        fh, fw = frame_rgb.shape[:2]
        x1, y1 = max(0, cx - half), max(0, cy - half)
        x2, y2 = min(fw, cx + half), min(fh, cy + half)
        return frame_rgb[y1:y2, x1:x2]

    def _process_frame(self, frame_bgr: np.ndarray, frame_rgb: np.ndarray) -> None:
        """Run liveness -> recognize on the largest detected face."""
        if self._detected_faces is None or len(self._detected_faces) == 0:
            return

        # Find largest face by area
        idx = int(np.argmax(self._detected_faces[:, 2] * self._detected_faces[:, 3]))
        face_row = self._detected_faces[idx]
        
        # Extract bbox for liveness (MiniFASNet still uses unaligned crop)
        x, y, w, h = face_row[:4].astype(int)
        face_crop = self._crop_face(frame_rgb, (x, y, w, h))

        # Step 1 — Liveness (MiniFASNet ONNX)
        liveness = self._liveness_checker.check(face_crop, self._liveness_threshold)
        if not liveness.is_real:
            self._bbox_color = _COLOR_ALERT
            self._result_hold_counter = _RESULT_HOLD_FRAMES
            self.recognition_result.emit("spoof", 0, "", liveness.score, 0.0)
            return

        # Step 2 — Recognition (SFace uses alignment)
        match = self._face_recognizer.identify(frame_bgr, face_row, self._similarity_threshold)
        if match is None:
            self._bbox_color = _COLOR_UNKNOWN
            self._result_hold_counter = _RESULT_HOLD_FRAMES
            self.recognition_result.emit("unrecognized", 0, "", liveness.score, 0.0)
            return

        # Per-user cooldown to avoid flooding the DB
        now = time.monotonic()
        if now - self._last_recognized.get(match.user_id, 0.0) < _COOLDOWN_SECONDS:
            return
        self._last_recognized[match.user_id] = now

        self._bbox_color = _COLOR_SUCCESS
        self._result_hold_counter = _RESULT_HOLD_FRAMES
        self.recognition_result.emit(
            "success", match.user_id, match.full_name, liveness.score, match.similarity
        )
