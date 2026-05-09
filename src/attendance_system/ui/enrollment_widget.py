from __future__ import annotations

import numpy as np
from pathlib import Path
from typing import TYPE_CHECKING

from PyQt5.QtCore import Qt, pyqtSignal, pyqtSlot
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

from attendance_system.ui.constants import FONT_BODY, FONT_TITLE
from attendance_system.repositories.user_repository import UserRepository
from attendance_system.services.enrollment_service import EnrollmentService
from attendance_system.ui.enrollment_camera_thread import EnrollmentCameraThread

if TYPE_CHECKING:
    from attendance_system.core.db import Database
    from attendance_system.services.ai_pipeline import FaceRecognizer, LivenessChecker
    from attendance_system.services.settings_service import SettingsService


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
        detector_model_path: Path | None = None,
        parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self._database = database
        self._liveness_checker = liveness_checker
        self._face_recognizer = face_recognizer
        self._settings_service = settings_service
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

        # Progress Bar for capture
        progress_layout = QVBoxLayout()
        self._progress_label = QLabel("Tiến trình: 0/5 ảnh")
        self._progress_label.setFont(FONT_BODY)
        progress_layout.addWidget(self._progress_label)
        
        self._progress_bar = QProgressBar()
        self._progress_bar.setMaximum(5)
        self._progress_bar.setValue(0)
        self._progress_bar.setTextVisible(False)
        self._progress_bar.setFixedHeight(10)
        progress_layout.addWidget(self._progress_bar)
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

        # Start thread
        self._camera_thread = EnrollmentCameraThread(
            camera_index=cam_idx,
            liveness_checker=self._liveness_checker,
            face_recognizer=self._face_recognizer,
            liveness_threshold=liveness_thresh,
            detector_model_path=self._detector_model_path,
            parent=self
        )
        self._camera_thread.frame_ready.connect(self.update_frame)
        self._camera_thread.capture_progress.connect(self.set_progress)
        self._camera_thread.enrollment_complete.connect(self._handle_complete)
        self._camera_thread.camera_error.connect(self._handle_error)
        
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
        
        # Reset UI state
        self._start_btn.setEnabled(True)
        self._stop_btn.setEnabled(False)
        self._user_dropdown.setEnabled(True)
        self._refresh_btn.setEnabled(True)

    @pyqtSlot(QImage)
    def update_frame(self, image: QImage) -> None:
        """Update the camera label with a new frame."""
        self._camera_label.setPixmap(QPixmap.fromImage(image))

    def set_progress(self, current: int, total: int = 5) -> None:
        """Update progress bar and label."""
        self._progress_bar.setValue(current)
        self._progress_label.setText(f"Tiến trình: {current}/{total} ảnh")

    @pyqtSlot(np.ndarray)
    def _handle_complete(self, avg_embedding: np.ndarray) -> None:
        user_id = self._user_dropdown.currentData()
        try:
            # Save embedding
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
    def _handle_error(self, message: str) -> None:
        QMessageBox.critical(self, "Lỗi Camera", message)
        self._stop_enrollment()
