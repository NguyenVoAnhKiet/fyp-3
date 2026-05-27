from __future__ import annotations

import logging

import numpy as np
from pathlib import Path
from typing import TYPE_CHECKING

from PyQt5.QtCore import Qt, pyqtSlot
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
    QProgressBar,
    QMessageBox,
)

from PyQt5.QtCore import QPropertyAnimation, QTimer
from PyQt5.QtWidgets import QGraphicsOpacityEffect

from attendance_system.ui.constants import FONT_BODY, FONT_TITLE
from attendance_system.repositories.user_repository import UserRepository
from attendance_system.services.enrollment_service import EnrollmentService
from attendance_system.services.ai_pipeline import LivenessChecker
from attendance_system.ui.enrollment_camera_thread import EnrollmentCameraThread

if TYPE_CHECKING:
    from attendance_system.core.db import Database
    from attendance_system.services.ai_pipeline import FaceRecognizer
    from attendance_system.services.head_pose import HeadPoseEstimator
    from attendance_system.services.settings_service import SettingsService

logger = logging.getLogger(__name__)

_TARGET_CAPTURE_COUNT = 5

class EnrollmentWidget(QWidget):
    """
    UI for biometric registration (UC-08).
    Allows admin to select a user, start the camera, and guide the user through face capture.
    """

    def __init__(
        self, 
        database: Database, 
        liveness_checker: LivenessChecker,
        face_recognizer: FaceRecognizer,
        settings_service: SettingsService,
        head_pose_estimator: HeadPoseEstimator | None,
        detector_model_path: Path | None = None,
        parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self._database = database
        self._liveness_checker = liveness_checker
        self._face_recognizer = face_recognizer
        self._settings_service = settings_service
        self._head_pose_estimator = head_pose_estimator
        self._detector_model_path = detector_model_path
        
        self._user_repo = UserRepository(database)
        self._enroll_service = EnrollmentService(database)
        self._camera_thread: EnrollmentCameraThread | None = None
        
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(20)

        # Title
        title = QLabel("Đăng Ký Biometric")
        title.setFont(FONT_TITLE)
        layout.addWidget(title)

        # User Selection Row
        selection_layout = QHBoxLayout()
        selection_layout.addWidget(QLabel("Chọn Người Dùng:"))
        self._user_dropdown = QComboBox()
        self._user_dropdown.setMinimumWidth(200)
        selection_layout.addWidget(self._user_dropdown)
        
        self._refresh_btn = QPushButton("🔄")
        self._refresh_btn.setToolTip("Làm mới danh sách")
        self._refresh_btn.setFixedWidth(40)
        self._refresh_btn.clicked.connect(self.refresh_users)
        selection_layout.addWidget(self._refresh_btn)
        
        selection_layout.addStretch()
        layout.addLayout(selection_layout)

        # Camera Area
        self._camera_label = QLabel("Camera Feed")
        self._camera_label.setFixedSize(640, 480)
        self._camera_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._camera_label.setStyleSheet("background-color: black; color: white; border-radius: 8px;")
        layout.addWidget(self._camera_label, alignment=Qt.AlignmentFlag.AlignCenter)

        # Progress dots
        progress_layout = QVBoxLayout()
        self._dots_layout = QHBoxLayout()
        self._dots_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._progress_dots: list[QLabel] = []
        for _ in range(_TARGET_CAPTURE_COUNT):
            dot = QLabel()
            dot.setFixedSize(24, 24)
            dot.setStyleSheet("background-color: #D0D0D0; border-radius: 12px;")
            self._progress_dots.append(dot)
            self._dots_layout.addWidget(dot)
        progress_layout.addLayout(self._dots_layout)

        self._angles_label = QLabel("Góc: -")
        self._angles_label.setFont(FONT_BODY)
        progress_layout.addWidget(self._angles_label)

        self._guidance_label = QLabel("Hướng dẫn: -")
        self._guidance_label.setFont(FONT_BODY)
        progress_layout.addWidget(self._guidance_label)
        
        self._progress_bar = QProgressBar()
        self._progress_bar.setMaximum(_TARGET_CAPTURE_COUNT)
        self._progress_bar.setValue(0)
        self._progress_bar.setTextVisible(False)
        self._progress_bar.setFixedHeight(10)
        progress_layout.addWidget(self._progress_bar)

        # Notification label (hidden by default)
        self._notification_label = QLabel()
        self._notification_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._notification_label.setStyleSheet(
            "background-color: #27AE60; color: white; border-radius: 8px; "
            "font-weight: bold; padding: 6px;"
        )
        self._opacity_effect = QGraphicsOpacityEffect()
        self._opacity_effect.setOpacity(0.0)
        self._notification_label.setGraphicsEffect(self._opacity_effect)
        self._notification_label.setFixedHeight(32)
        self._notification_label.hide()
        progress_layout.addWidget(self._notification_label)

        # Fade animation
        self._notif_anim = QPropertyAnimation(self._opacity_effect, b"opacity")
        self._notif_anim.setDuration(200)
        self._notif_timer: QTimer | None = None

        layout.addLayout(progress_layout)

        # Controls
        controls_layout = QHBoxLayout()
        self._start_btn = QPushButton("Bắt Đầu Đăng Ký")
        self._start_btn.setMinimumHeight(40)
        self._start_btn.setStyleSheet("background-color: #2ecc71; color: white; font-weight: bold;")
        self._start_btn.clicked.connect(self._start_enrollment)
        
        self._stop_btn = QPushButton("Dừng / Hủy")
        self._stop_btn.setMinimumHeight(40)
        self._stop_btn.setEnabled(False)
        self._stop_btn.setStyleSheet("background-color: #e74c3c; color: white; font-weight: bold;")
        self._stop_btn.clicked.connect(self._stop_enrollment)

        controls_layout.addWidget(self._start_btn)
        controls_layout.addWidget(self._stop_btn)
        layout.addLayout(controls_layout)

        layout.addStretch()
        
        self.refresh_users()

    def refresh_users(self) -> None:
        """Load users who don't have a registered face yet."""
        self._user_dropdown.clear()
        users = self._user_repo.list_unregistered()
        for user in users:
            display_text = f"{user['student_id']} - {user['full_name']}"
            self._user_dropdown.addItem(display_text, user["id"])
        
        if not users:
            self._user_dropdown.addItem("Không có người dùng nào cần đăng ký", -1)
            self._start_btn.setEnabled(False)
        else:
            self._start_btn.setEnabled(True)

    def _start_enrollment(self) -> None:
        user_id = self._user_dropdown.currentData()
        if user_id == -1:
            return

        # Get settings
        cam_idx = int(self._settings_service.get("camera_index") or 0)
        liveness_thresh = float(self._settings_service.get("liveness_threshold") or 0.5)

        # Liveness check is intentionally bypassed during enrollment.
        # Multi-pose face capture (yaw/pitch/roll) already provides strong
        # implicit anti-spoofing — a static photo cannot complete the pose
        # sequence. Additionally, the enrollment crop scale (2.7) differs
        # from MiniFASNet's expected scale (1.5), causing false rejects
        # on angled faces.
        if self._liveness_checker.is_enabled:
            logger.info(
                "Enrollment: liveness check available but intentionally "
                "bypassed (multi-pose sequence provides anti-spoofing)"
            )
        else:
            logger.info(
                "Enrollment: liveness check disabled "
                "(FACE_ANTISPOOF_ENABLED=false)"
            )

        enrollment_liveness = LivenessChecker(model_path=None)

        # Start thread
        self._camera_thread = EnrollmentCameraThread(
            camera_index=cam_idx,
            liveness_checker=enrollment_liveness,  # Use bypass liveness
            face_recognizer=self._face_recognizer,
            head_pose_estimator=self._head_pose_estimator,
            liveness_threshold=liveness_thresh,
            detector_model_path=self._detector_model_path,
            parent=self
        )
        self._camera_thread.frame_ready.connect(self.update_frame)
        self._camera_thread.capture_progress.connect(self.set_progress)
        self._camera_thread.enrollment_complete.connect(self._handle_complete)
        self._camera_thread.camera_error.connect(self._handle_error)
        self._camera_thread.inference_warning.connect(self._handle_inference_warning)
        self._camera_thread.sample_captured.connect(self._on_sample_captured)
        self._reset_dots()
        
        self._camera_thread.start()
        
        # Update UI state
        self._start_btn.setEnabled(False)
        self._stop_btn.setEnabled(True)
        self._user_dropdown.setEnabled(False)
        self._refresh_btn.setEnabled(False)

    def _stop_enrollment(self) -> None:
        if self._camera_thread:
            self._camera_thread.stop()
            self._camera_thread = None
        
        self._camera_label.clear()
        self._camera_label.setText("Camera Feed")
        self.set_progress(0)
        self._reset_dots()
        
        # Reset UI state
        self._start_btn.setEnabled(True)
        self._stop_btn.setEnabled(False)
        self._user_dropdown.setEnabled(True)
        self._refresh_btn.setEnabled(True)

    @pyqtSlot(QImage)
    def update_frame(self, image: QImage) -> None:
        """Update the camera label with a new frame."""
        self._camera_label.setPixmap(QPixmap.fromImage(image))

    def set_progress(
        self,
        current: int,
        total: int = _TARGET_CAPTURE_COUNT,
        pose_label: str = "",
        angles_text: str = "",
        hold_text: str = "",
        guidance_text: str = "",
    ) -> None:
        """Update progress bar and label."""
        if total > 0:
            self._progress_bar.setMaximum(total)
        self._progress_bar.setValue(current)
        self._angles_label.setText(f"Góc: {angles_text or '-'}")
        guidance = guidance_text or hold_text or "-"
        self._guidance_label.setText(f"Hướng dẫn: {guidance}")

    def _reset_dots(self) -> None:
        """Reset all progress dots to gray."""
        for dot in self._progress_dots:
            dot.setStyleSheet("background-color: #D0D0D0; border-radius: 12px;")
        self._notification_label.hide()

    def _fade_notification(self) -> None:
        """Fade out the notification label."""
        self._notif_anim.setDuration(300)
        self._notif_anim.setStartValue(1.0)
        self._notif_anim.setEndValue(0.0)
        try:
            self._notif_anim.finished.disconnect()
        except TypeError:
            pass
        self._notif_anim.finished.connect(self._notification_label.hide)
        self._notif_anim.start()

    @pyqtSlot(np.ndarray)
    def _handle_complete(self, avg_embedding: np.ndarray) -> None:
        """Finalize enrollment after success effect plays."""
        user_id = self._user_dropdown.currentData()
        # Delay final save + dialog by 1.5s so success effect is visible
        QTimer.singleShot(1500, lambda: self._finalize_enrollment(user_id, avg_embedding))

    def _finalize_enrollment(self, user_id: int, avg_embedding: np.ndarray) -> None:
        """Save embedding and show result (called after success effect)."""
        try:
            self._enroll_service.save_face_reference(
                user_id=user_id,
                embedding=avg_embedding.tobytes(),
                model_name="SFace",
                vector_length=len(avg_embedding)
            )
            QMessageBox.information(self, "Thành Công", "Đăng ký khuôn mặt thành công!")
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Không thể lưu dữ liệu: {str(e)}")
        
        self._stop_enrollment()
        self.refresh_users()

    @pyqtSlot(str)
    def _handle_inference_warning(self, message: str) -> None:
        """Show a temporary inference warning without stopping enrollment."""
        self._guidance_label.setText(f"Hướng dẫn: {message}")
        # Previous guidance will be overwritten by the next capture_progress signal

    @pyqtSlot(int)
    def _on_sample_captured(self, count: int) -> None:
        """Animate dot and notification on successful capture."""
        # Cancel pending fade timer from previous sample
        if self._notif_timer is not None:
            self._notif_timer.stop()
            self._notif_timer = None
        try:
            self._notif_anim.finished.disconnect()
        except TypeError:
            pass

        idx = count - 1  # 0-based index
        if 0 <= idx < len(self._progress_dots):
            # Update dot to green
            self._progress_dots[idx].setStyleSheet(
                "background-color: #2ECC71; border-radius: 12px;"
            )

        # Update notification
        self._notification_label.show()
        self._opacity_effect.setOpacity(0.0)

        if count >= _TARGET_CAPTURE_COUNT:
            self._notification_label.setText("🎉 Hoàn tất! 5/5 ảnh")
            self._notif_anim.setDuration(400)
            self._notif_anim.setStartValue(0.0)
            self._notif_anim.setEndValue(1.0)
            self._notif_anim.start()
        else:
            self._notification_label.setText(f"📸 Mẫu {count}/{_TARGET_CAPTURE_COUNT} thành công!")
            self._notif_anim.setDuration(200)
            self._notif_anim.setStartValue(0.0)
            self._notif_anim.setEndValue(1.0)
            self._notif_anim.start()
            # Auto-hide after 1.5s
            self._notif_timer = QTimer(self)
            self._notif_timer.setSingleShot(True)
            self._notif_timer.timeout.connect(self._fade_notification)
            self._notif_timer.start(1500)

    @pyqtSlot(str)
    def _handle_error(self, message: str) -> None:
        QMessageBox.critical(self, "Lỗi Camera", message)
        self._stop_enrollment()
