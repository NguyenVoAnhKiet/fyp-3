"""Face enrollment widget: capture multiple angles, persist embeddings.

Receives :class:`attendance_system.core.config.SystemConfig` from the
admin dashboard and threads its fields (``camera_index``,
``detection_model_path``, ``liveness_threshold``,
``similarity_threshold``) into :class:`EnrollmentCameraThread`.  No
hardcoded thresholds — every value is sourced from the resolved config
object.  See plan 0005 (archived 2026-06-05).
"""

from __future__ import annotations

import logging

import numpy as np
from typing import TYPE_CHECKING

from PyQt5.QtCore import Qt, pyqtSlot, QPropertyAnimation, QTimer
from PyQt5.QtGui import QColor, QImage, QPainter, QPen, QPixmap
from PyQt5.QtWidgets import (
    QComboBox,
    QFrame,
    QGraphicsDropShadowEffect,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QStyle,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from attendance_system.ui.constants import FONT_BODY, FONT_TITLE
from attendance_system.ui.styles import BG_CARD, BG_INPUT, STATUS_INFO, STATUS_SUCCESS, TEXT_MUTED, TEXT_SECONDARY
from attendance_system.repositories.caching_face_reference_repository import (
    CachingFaceReferenceRepository,
)
from attendance_system.repositories.face_reference_repository import (
    FaceReferenceRepository,
)
from attendance_system.repositories.user_repository import UserRepository
from attendance_system.services.enrollment_service import EnrollmentService
from attendance_system.services.ai_pipeline import LivenessChecker
from attendance_system.ui.enrollment_camera_thread import EnrollmentCameraThread

if TYPE_CHECKING:
    from attendance_system.core.config import SystemConfig
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
        config: "SystemConfig",
        face_refs: FaceReferenceRepository | CachingFaceReferenceRepository | None = None,
        parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self._database = database
        self._liveness_checker = liveness_checker
        self._face_recognizer = face_recognizer
        self._settings_service = settings_service
        self._head_pose_estimator = head_pose_estimator
        self._config = config

        self._user_repo = UserRepository(database)
        # Pass the shared CachingFaceReferenceRepository from the composition
        # root so enrollment invalidates the recognizer's cache atomically.
        # Fall back to a bare repo for tests / legacy callers.
        self._enroll_service = EnrollmentService(database, references=face_refs)
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
        
        self._refresh_btn = QToolButton()
        refresh_icon = self.style().standardIcon(QStyle.SP_BrowserReload)
        self._refresh_btn.setIcon(refresh_icon)
        self._refresh_btn.setToolTip("Làm mới danh sách")
        self._refresh_btn.setFixedWidth(40)
        self._refresh_btn.setFixedHeight(40)
        self._refresh_btn.setStyleSheet("""
            QToolButton {
                background-color: #2563eb;
                border: none;
                border-radius: 6px;
                padding: 6px;
            }
            QToolButton:hover {
                background-color: #1d4ed8;
            }
            QToolButton:pressed {
                background-color: #1e40af;
            }
        """)
        self._refresh_btn.clicked.connect(self.refresh_users)
        selection_layout.addWidget(self._refresh_btn)
        
        selection_layout.addStretch()
        layout.addLayout(selection_layout)

        # Camera card with shadow
        self._camera_card = QFrame()
        self._camera_card.setObjectName("cameraCard")
        self._camera_card.setStyleSheet(
            "QFrame#cameraCard {"
            f"  background-color: {BG_CARD};"
            "  border-radius: 12px;"
            "  padding: 12px;"
            "}"
        )
        card_shadow = QGraphicsDropShadowEffect()
        card_shadow.setBlurRadius(20)
        card_shadow.setOffset(0, 4)
        card_shadow.setColor(QColor(0, 0, 0, 20))
        self._camera_card.setGraphicsEffect(card_shadow)

        card_layout = QVBoxLayout(self._camera_card)
        card_layout.setContentsMargins(12, 12, 12, 12)

        # Camera Area
        self._camera_label = QLabel("Camera Feed")
        self._camera_label.setFixedSize(640, 480)
        self._camera_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._camera_label.setStyleSheet("background-color: black; color: white; border-radius: 8px;")
        card_layout.addWidget(self._camera_label)

        layout.addWidget(self._camera_card, alignment=Qt.AlignmentFlag.AlignCenter)

        # Step circles (1-5) connected by lines
        steps_layout = QHBoxLayout()
        steps_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        steps_layout.setSpacing(0)
        self._step_circles: list[QLabel] = []
        self._step_lines: list[QFrame] = []
        for i in range(_TARGET_CAPTURE_COUNT):
            if i > 0:
                line = QFrame()
                line.setFixedSize(40, 3)
                line.setStyleSheet("background-color: #D0D0D0; border: none;")
                self._step_lines.append(line)
                steps_layout.addWidget(line)

            circle = QLabel(str(i + 1))
            circle.setFixedSize(32, 32)
            circle.setAlignment(Qt.AlignmentFlag.AlignCenter)
            circle.setStyleSheet(
                "background-color: #D0D0D0; color: white; border-radius: 16px; "
                "font-weight: bold; font-size: 16px;"
            )
            self._step_circles.append(circle)
            steps_layout.addWidget(circle)

        layout.addLayout(steps_layout)

        # Pose icon + labels row
        info_row = QHBoxLayout()
        info_row.setSpacing(16)

        self._pose_icon_label = QLabel()
        self._pose_icon_label.setFixedSize(120, 120)
        self._pose_icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._pose_icon_label.setStyleSheet(
            f"background-color: {BG_INPUT}; border-radius: 8px;"
        )
        info_row.addWidget(self._pose_icon_label)

        labels_col = QVBoxLayout()
        labels_col.setSpacing(8)

        self._guidance_label = QLabel("Hướng dẫn: -")
        self._guidance_label.setFont(FONT_BODY)
        labels_col.addWidget(self._guidance_label)

        self._angles_label = QLabel("Góc: -")
        self._angles_label.setFont(FONT_BODY)
        labels_col.addWidget(self._angles_label)

        info_row.addLayout(labels_col)
        info_row.addStretch()
        layout.addLayout(info_row)

        # Progress bar
        self._progress_bar = QProgressBar()
        self._progress_bar.setMaximum(_TARGET_CAPTURE_COUNT)
        self._progress_bar.setValue(0)
        self._progress_bar.setTextVisible(False)
        self._progress_bar.setFixedHeight(10)
        layout.addWidget(self._progress_bar)

        # Notification label (hidden by default)
        self._notification_label = QLabel()
        self._notification_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._notification_label.setStyleSheet(
            f"background-color: {STATUS_SUCCESS}; color: white; border-radius: 8px; "
            "font-weight: bold; padding: 6px;"
        )
        self._opacity_effect = QGraphicsOpacityEffect()
        self._opacity_effect.setOpacity(0.0)
        self._notification_label.setGraphicsEffect(self._opacity_effect)
        self._notification_label.setFixedHeight(32)
        self._notification_label.hide()
        layout.addWidget(self._notification_label)

        # Fade animation
        self._notif_anim = QPropertyAnimation(self._opacity_effect, b"opacity")
        self._notif_anim.setDuration(200)
        self._notif_timer: QTimer | None = None

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
        self._stop_btn.clicked.connect(self._confirm_and_stop)

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

        # Camera index: prefer admin's last choice in DB, fall back to
        # ``SystemConfig.camera_index`` (resolved at startup).
        saved_cam = self._settings_service.get("camera_index")
        cam_idx = int(saved_cam) if saved_cam is not None else self._config.camera_index

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
            liveness_threshold=self._config.liveness_threshold,
            similarity_threshold=self._config.similarity_threshold,
            detector_model_path=self._config.detection_model_path,
            parent=self
        )
        self._camera_thread.frame_ready.connect(self.update_frame)
        self._camera_thread.capture_progress.connect(self.set_progress)
        self._camera_thread.enrollment_complete.connect(self._handle_complete)
        self._camera_thread.camera_error.connect(self._handle_error)
        self._camera_thread.inference_warning.connect(self._handle_inference_warning)
        self._camera_thread.sample_captured.connect(self._on_sample_captured)
        self._reset_steps()
        
        self._camera_thread.start()
        
        # Update UI state
        self._start_btn.setEnabled(False)
        self._stop_btn.setEnabled(True)
        self._user_dropdown.setEnabled(False)
        self._refresh_btn.setEnabled(False)

    def _confirm_and_stop(self) -> None:
        """Show confirmation dialog before stopping (user-initiated)."""
        if self._camera_thread is None:
            return
        result = QMessageBox.question(
            self,
            "Xác nhận",
            "Bạn có chắc chắn muốn hủy quá trình đăng ký khuôn mặt? "
            "Dữ liệu các mẫu đã chụp sẽ bị mất.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if result == QMessageBox.Yes:
            self._stop_enrollment()

    def _stop_enrollment(self) -> None:
        if self._camera_thread is not None:
            # Disconnect all signals BEFORE stopping to prevent pending
            # signals from re-writing the cleared camera label.
            # try/except TypeError is the canonical PyQt5 pattern for safe
            # disconnect — receivers() is a QObject method, not a bound-signal
            # method, so it does not work reliably in all PyQt5 versions.
            try:
                self._camera_thread.frame_ready.disconnect(self.update_frame)
            except TypeError:
                pass
            try:
                self._camera_thread.capture_progress.disconnect(self.set_progress)
            except TypeError:
                pass
            try:
                self._camera_thread.enrollment_complete.disconnect(self._handle_complete)
            except TypeError:
                pass
            try:
                self._camera_thread.camera_error.disconnect(self._handle_error)
            except TypeError:
                pass
            try:
                self._camera_thread.inference_warning.disconnect(self._handle_inference_warning)
            except TypeError:
                pass
            try:
                self._camera_thread.sample_captured.disconnect(self._on_sample_captured)
            except TypeError:
                pass
            self._camera_thread.stop()
            self._camera_thread = None

        self._camera_label.clear()
        self._camera_label.setText("Camera Feed")
        self.set_progress(0)
        self._reset_steps()

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
        """Update progress, labels, and pose icon."""
        if total > 0:
            self._progress_bar.setMaximum(total)
        self._progress_bar.setValue(current)
        self._angles_label.setText(f"Góc: {angles_text or '-'}")
        guidance = guidance_text or hold_text or "-"
        self._guidance_label.setText(f"Hướng dẫn: {guidance}")
        self._draw_pose_icon(guidance)

    def _reset_steps(self) -> None:
        """Reset all step circles and lines to gray."""
        for circle in self._step_circles:
            circle.setStyleSheet(
                "background-color: #D0D0D0; color: white; border-radius: 16px; "
                "font-weight: bold; font-size: 16px;"
            )
        for line in self._step_lines:
            line.setStyleSheet("background-color: #D0D0D0; border: none;")
        self._notification_label.hide()
        self._draw_pose_icon("")

    def _draw_pose_icon(self, guidance: str) -> None:
        """Draw a face icon indicating the target pose direction on a 120x120 pixmap."""
        pixmap = QPixmap(120, 120)
        pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Determine direction offset from guidance text
        guidance_lower = guidance.lower()
        dx, dy = 0, 0
        if "nghiêng trái" in guidance_lower or "trái" in guidance_lower:
            dx = -10
        if "nghiêng phải" in guidance_lower or "phải" in guidance_lower:
            dx = 10
        if "ngửa lên" in guidance_lower or "lên" in guidance_lower:
            dy = -10
        if "cúi xuống" in guidance_lower or "xuống" in guidance_lower:
            dy = 10

        # Face outline
        painter.setPen(QPen(QColor(TEXT_MUTED), 2))
        painter.setBrush(QColor(BG_INPUT))
        painter.drawEllipse(10, 10, 100, 100)

        # Eyes
        eye_color = QColor(TEXT_SECONDARY)
        painter.setPen(QPen(eye_color, 2))
        painter.setBrush(eye_color)
        painter.drawEllipse(38 + dx, 42 + dy, 8, 8)   # left eye
        painter.drawEllipse(74 + dx, 42 + dy, 8, 8)   # right eye

        # Nose
        painter.setPen(QPen(QColor(STATUS_INFO), 2))
        painter.drawEllipse(58, 60, 4, 4)

        # Mouth
        painter.setPen(QPen(eye_color, 2))
        painter.drawArc(46, 68, 28, 16, 0, -180 * 16)

        # Direction indicator dot when not center
        if dx != 0 or dy != 0:
            painter.setPen(QPen(QColor(STATUS_INFO), 2))
            painter.setBrush(QColor(STATUS_INFO))
            cx, cy = 60 + dx * 3, 60 + dy * 3
            painter.drawEllipse(cx - 5, cy - 5, 10, 10)

        painter.end()
        self._pose_icon_label.setPixmap(pixmap)

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

    @pyqtSlot(dict)
    def _handle_complete(self, pose_embeddings: dict[str, np.ndarray]) -> None:
        """Finalize enrollment after success effect plays."""
        user_id = self._user_dropdown.currentData()
        # Delay final save + dialog by 1.5s so success effect is visible
        QTimer.singleShot(1500, lambda: self._finalize_enrollment(user_id, pose_embeddings))

    def _finalize_enrollment(self, user_id: int, pose_embeddings: dict[str, np.ndarray]) -> None:
        """Save five pose embeddings and show result (called after success effect)."""
        try:
            pose_bytes = {
                pose: emb.tobytes() for pose, emb in pose_embeddings.items()
            }
            first_emb = next(iter(pose_embeddings.values()))
            self._enroll_service.save_face_references(
                user_id=user_id,
                pose_embeddings=pose_bytes,
                model_name="SFace",
                vector_length=len(first_emb),
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
        """Animate step circles and notification on successful capture."""
        # Cancel pending fade timer from previous sample
        if self._notif_timer is not None:
            self._notif_timer.stop()
            self._notif_timer = None
        try:
            self._notif_anim.finished.disconnect()
        except TypeError:
            pass

        # Mark completed steps green (count is 1-based)
        completed = count
        for i, circle in enumerate(self._step_circles):
            if i < completed:
                circle.setStyleSheet(
                    f"background-color: {STATUS_SUCCESS}; color: white; "
                    "border-radius: 16px; font-weight: bold; font-size: 16px;"
                )
            else:
                circle.setStyleSheet(
                    "background-color: #D0D0D0; color: white; "
                    "border-radius: 16px; font-weight: bold; font-size: 16px;"
                )
        # Connect completed steps with green lines
        for i, line in enumerate(self._step_lines):
            if i + 1 < completed:
                line.setStyleSheet(
                    f"background-color: {STATUS_SUCCESS}; border: none;"
                )
            else:
                line.setStyleSheet("background-color: #D0D0D0; border: none;")

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
