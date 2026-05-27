from __future__ import annotations

import logging
from pathlib import Path


from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QImage, QKeyEvent, QPixmap
from PyQt5.QtWidgets import (
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QHBoxLayout,
    QWidget,
)

from attendance_system.services.ai_pipeline import FaceRecognizer, LivenessChecker
from attendance_system.services.attendance_service import AttendanceService
from attendance_system.services.settings_service import SettingsService
from attendance_system.ui.camera_thread import CameraThread
from attendance_system.ui.constants import FONT_BODY, FONT_STATUS, FONT_TITLE
from attendance_system.utils.time_utils import utc_now_iso, utc_to_local

logger = logging.getLogger(__name__)

_DEFAULT_LIVENESS_THRESHOLD = 0.5
_DEFAULT_SIMILARITY_THRESHOLD = 0.6

# Stack indices for IDLE / ACTIVE sub-panels inside UserModeView
_IDX_IDLE = 0
_IDX_ACTIVE = 1


class UserModeView(QWidget):
    """
    User-facing attendance view.

    IDLE  → user fills subject/class → ACTIVE (camera feed + recognition)
    ACTIVE → E ends session → IDLE

    Emits ``login_requested`` when the admin login shortcut is triggered
    from the IDLE state.
    """

    login_requested = pyqtSignal()

    def __init__(
        self,
        attendance_service: AttendanceService,
        settings_service: SettingsService,
        liveness_checker: LivenessChecker,
        face_recognizer: FaceRecognizer,
        camera_index: int = 0,
        detector_model_path: Path | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._attendance = attendance_service
        self._settings = settings_service
        self._liveness_checker = liveness_checker
        self._face_recognizer = face_recognizer
        self._camera_index = camera_index
        self._detector_model_path = detector_model_path
        self._session_id: int | None = None
        self._camera_thread: CameraThread | None = None

        self._build_ui()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._stack = QStackedWidget()
        layout.addWidget(self._stack)

        self._stack.addWidget(self._build_idle_panel())   # _IDX_IDLE
        self._stack.addWidget(self._build_active_panel()) # _IDX_ACTIVE
        self._stack.setCurrentIndex(_IDX_IDLE)

    def _build_idle_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setSpacing(14)
        layout.setContentsMargins(48, 40, 48, 40)

        title = QLabel("Hệ Thống Điểm Danh Khuôn Mặt")
        title.setFont(FONT_TITLE)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        status = QLabel("Trạng thái: CHỜ  (IDLE)")
        status.setFont(FONT_STATUS)
        status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        status.setStyleSheet("color: #7f8c8d;")
        layout.addWidget(status)

        layout.addSpacing(12)

        subject_lbl = QLabel("Tên Môn Học:")
        subject_lbl.setFont(FONT_BODY)
        layout.addWidget(subject_lbl)

        self._subject_input = QLineEdit()
        self._subject_input.setFont(FONT_BODY)
        self._subject_input.setPlaceholderText("Ví dụ: Trí Tuệ Nhân Tạo")
        layout.addWidget(self._subject_input)

        class_lbl = QLabel("Tên Lớp:")
        class_lbl.setFont(FONT_BODY)
        layout.addWidget(class_lbl)

        self._class_input = QLineEdit()
        self._class_input.setFont(FONT_BODY)
        self._class_input.setPlaceholderText("Ví dụ: IT01")
        layout.addWidget(self._class_input)

        layout.addSpacing(12)

        btn_start = QPushButton("Bắt Đầu Phiên Điểm Danh  [S]")
        btn_start.setFont(FONT_BODY)
        btn_start.clicked.connect(self._start_session)
        layout.addWidget(btn_start)

        btn_admin = QPushButton("Đăng Nhập Quản Trị  [Ctrl+L]")
        btn_admin.setFont(FONT_BODY)
        btn_admin.setStyleSheet("color: #7f8c8d;")
        btn_admin.clicked.connect(self.login_requested.emit)
        layout.addWidget(btn_admin)

        layout.addStretch()
        return panel

    def _build_active_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setSpacing(12)
        layout.setContentsMargins(48, 24, 48, 24)

        title = QLabel("Hệ Thống Điểm Danh Khuôn Mặt")
        title.setFont(FONT_TITLE)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        active_status = QLabel("Trạng thái: ĐANG HOẠT ĐỘNG  (ACTIVE)")
        active_status.setFont(FONT_STATUS)
        active_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        active_status.setStyleSheet("color: #27ae60;")
        layout.addWidget(active_status)

        self._session_info_label = QLabel("")
        self._session_info_label.setFont(FONT_BODY)
        self._session_info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._session_info_label)

        # Content area: Camera (Left) + Sidebar (Right)
        content_layout = QHBoxLayout()
        content_layout.setSpacing(16)
        layout.addLayout(content_layout)

        # Left Column: Camera and Result Label
        camera_area = QVBoxLayout()
        camera_area.setSpacing(10)
        content_layout.addLayout(camera_area, stretch=1)

        self._camera_label = QLabel("[ Đang khởi động camera… ]")
        self._camera_label.setFont(FONT_BODY)
        self._camera_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._camera_label.setStyleSheet(
            "background-color: #2c3e50; color: #ecf0f1; border-radius: 8px;"
        )
        self._camera_label.setMinimumHeight(350)
        self._camera_label.setScaledContents(False)
        camera_area.addWidget(self._camera_label, stretch=1)

        self._result_label = QLabel("Đang chờ nhận diện…")
        self._result_label.setFont(FONT_STATUS)
        self._result_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._result_label.setMinimumHeight(56)
        self._set_result_style("neutral")
        camera_area.addWidget(self._result_label)

        # Right Column: Attendance Sidebar
        sidebar_area = QVBoxLayout()
        sidebar_area.setSpacing(6)
        content_layout.addLayout(sidebar_area)

        sidebar_header = QLabel("Danh sách điểm danh")
        sidebar_header.setFont(FONT_BODY)
        sidebar_header.setStyleSheet("font-weight: bold; color: #2c3e50; margin-bottom: 2px;")
        sidebar_area.addWidget(sidebar_header)

        self._attendance_list = QListWidget()
        self._attendance_list.setFont(FONT_BODY)
        self._attendance_list.setFixedWidth(280)
        self._attendance_list.setStyleSheet(
            "background-color: #f8f9fa; border: 1px solid #dee2e6; border-radius: 4px;"
        )
        sidebar_area.addWidget(self._attendance_list)

        btn_end = QPushButton("Kết Thúc Phiên  [E]")
        btn_end.setFont(FONT_BODY)
        btn_end.clicked.connect(self._end_session)
        layout.addWidget(btn_end)

        return panel

    # ------------------------------------------------------------------
    # Keyboard shortcuts — called by MainWindow.keyPressEvent
    # ------------------------------------------------------------------

    def keyPressEvent(self, a0: QKeyEvent | None) -> None:
        if a0 is None:
            return
        key = a0.key()
        modifiers = a0.modifiers()

        if key == Qt.Key.Key_S and self._stack.currentIndex() == _IDX_IDLE:
            self._start_session()
        elif key == Qt.Key.Key_E and self._stack.currentIndex() == _IDX_ACTIVE:
            self._end_session()
        elif (
            key == Qt.Key.Key_L
            and modifiers == Qt.KeyboardModifier.ControlModifier
            and self._stack.currentIndex() == _IDX_IDLE
        ):
            self.login_requested.emit()
        else:
            super().keyPressEvent(a0)

    # ------------------------------------------------------------------
    # Session lifecycle
    # ------------------------------------------------------------------

    def _start_session(self) -> None:
        if self._session_id is not None:
            return

        subject = self._subject_input.text().strip()
        class_name = self._class_input.text().strip()
        if not subject or not class_name:
            QMessageBox.warning(
                self,
                "Thiếu Thông Tin",
                "Vui lòng nhập Tên Môn Học và Tên Lớp trước khi bắt đầu.",
            )
            return

        liveness_threshold = float(
            self._settings.get("liveness_threshold") or _DEFAULT_LIVENESS_THRESHOLD
        )
        similarity_threshold = float(
            self._settings.get("similarity_threshold") or _DEFAULT_SIMILARITY_THRESHOLD
        )

        self._session_id = self._attendance.start_session(
            subject_name=subject,
            class_name=class_name,
            liveness_threshold_snapshot=liveness_threshold,
            similarity_threshold_snapshot=similarity_threshold,
            start_time=utc_now_iso(),
        )

        self._session_info_label.setText(f"Môn: {subject}  |  Lớp: {class_name}")
        self._result_label.setText("Đang chờ nhận diện…")
        self._set_result_style("neutral")
        self._attendance_list.clear()

        # Populate sidebar if there are existing success records for this session
        try:
            records = self._attendance.attendance.fetch_all(
                """
                SELECT u.full_name, ar.recorded_at 
                FROM attendance_records ar
                JOIN users u ON ar.user_id = u.id
                WHERE ar.session_id = ? AND ar.status = 'success'
                ORDER BY ar.recorded_at DESC
                """,
                (self._session_id,),
            )
            for rec in reversed(records):  # Reverse because _add_to_sidebar prepends
                self._add_to_sidebar(rec["full_name"], rec["recorded_at"])
        except Exception:
            pass

        self._stack.setCurrentIndex(_IDX_ACTIVE)

        # Read camera index from DB settings (admin may have changed it)
        saved_cam = self._settings.get("camera_index")
        active_camera = int(saved_cam) if saved_cam is not None else self._camera_index

        self._camera_thread = CameraThread(
            session_id=self._session_id,
            liveness_threshold=liveness_threshold,
            similarity_threshold=similarity_threshold,
            liveness_checker=self._liveness_checker,
            face_recognizer=self._face_recognizer,
            camera_index=active_camera,
            detector_model_path=self._detector_model_path,
            parent=self,
        )
        self._camera_thread.frame_ready.connect(self._update_camera_frame)
        self._camera_thread.recognition_result.connect(self._on_recognition_result)
        self._camera_thread.camera_error.connect(self._on_camera_error)
        self._camera_thread.inference_warning.connect(self._on_inference_warning)
        self._camera_thread.start()

    def _end_session(self) -> None:
        if self._session_id is None:
            return

        if self._camera_thread is not None:
            self._camera_thread.stop()
            self._camera_thread = None

        self._attendance.end_session(self._session_id, end_time=utc_now_iso())
        self._session_id = None
        self._subject_input.clear()
        self._class_input.clear()
        self._attendance_list.clear()
        self._stack.setCurrentIndex(_IDX_IDLE)

    def stop_camera(self) -> None:
        """Stop the camera thread if running. Called by MainWindow on close."""
        if self._camera_thread is not None:
            self._camera_thread.stop()
            self._camera_thread = None

    # ------------------------------------------------------------------
    # Camera thread slots
    # ------------------------------------------------------------------

    def _update_camera_frame(self, frame: QImage) -> None:
        pixmap = QPixmap.fromImage(frame).scaled(
            self._camera_label.width(),
            self._camera_label.height(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self._camera_label.setPixmap(pixmap)

    def _add_to_sidebar(self, name: str, time_str: str) -> None:
        """Prepend a check-in record to the sidebar list."""
        # Convert UTC ISO to local timezone before displaying
        local_time = utc_to_local(time_str)
        display_time = local_time
        if "T" in local_time:
            try:
                # Extract HH:mm:ss from ISO
                display_time = local_time.split("T")[1].split(".")[0]
            except Exception:
                pass
        
        item_text = f"[{display_time}]  {name}"
        self._attendance_list.insertItem(0, item_text)
        self._attendance_list.scrollToTop()

    def _on_recognition_result(
        self,
        result_type: str,
        user_id: int,
        full_name: str,
        liveness_score: float,
        similarity_score: float | None,
    ) -> None:
        if self._session_id is None:
            return

        now = utc_now_iso()

        if result_type == "success":
            try:
                self._attendance.record_success(
                    session_id=self._session_id,
                    user_id=user_id,
                    event_time=now,
                    liveness_score=liveness_score,
                    similarity_score=similarity_score,
                )
                self._show_result_success(full_name)
                self._add_to_sidebar(full_name, now)
            except Exception:
                self._attendance.record_duplicate(self._session_id, user_id, now)
                self._show_result_duplicate(full_name)

        elif result_type == "spoof":
            self._attendance.record_spoof_warning(
                self._session_id, now, details=f"liveness={liveness_score:.3f}"
            )
            self._show_result_spoof()

        elif result_type == "unrecognized":
            self._attendance.record_unrecognized(
                self._session_id, now, details=f"liveness={liveness_score:.3f}"
            )
            self._show_result_unrecognized()

    def _on_inference_warning(self, message: str) -> None:
        """Show a temporary inference warning in the result label."""
        logger.info("Inference warning: %s", message)
        self._result_label.setText(f"⚠ {message}")
        self._set_result_style("neutral")
        # The next recognition_result or frame will overwrite this

    def _on_camera_error(self, message: str) -> None:
        QMessageBox.critical(self, "Lỗi Camera", message)
        self._end_session()

    # ------------------------------------------------------------------
    # Recognition result display
    # ------------------------------------------------------------------

    def _show_result_success(self, name: str) -> None:
        self._result_label.setText(f"✅  {name}")
        self._set_result_style("success")

    def _show_result_duplicate(self, name: str) -> None:
        self._result_label.setText(f"⚠  {name} – Đã điểm danh")
        self._set_result_style("duplicate")

    def _show_result_spoof(self) -> None:
        self._result_label.setText("🚫  Cảnh báo: Giả mạo")
        self._set_result_style("spoof")

    def _show_result_unrecognized(self) -> None:
        self._result_label.setText("❌  Không nhận diện được")
        self._set_result_style("unrecognized")

    def _set_result_style(self, kind: str) -> None:
        colours = {
            "neutral": ("#95a5a6", "white"),
            "success": ("#27ae60", "white"),
            "duplicate": ("#f39c12", "white"),
            "spoof": ("#e74c3c", "white"),
            "unrecognized": ("#f1c40f", "black"),
        }
        bg, fg = colours.get(kind, colours["neutral"])
        self._result_label.setStyleSheet(
            f"background-color: {bg}; color: {fg}; border-radius: 6px; padding: 8px;"
        )
