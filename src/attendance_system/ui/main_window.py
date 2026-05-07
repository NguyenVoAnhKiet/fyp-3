from __future__ import annotations

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QImage, QKeyEvent, QPixmap
from PyQt5.QtWidgets import (
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from attendance_system.services.ai_pipeline import FaceRecognizer, LivenessChecker
from attendance_system.services.attendance_service import AttendanceService
from attendance_system.services.settings_service import SettingsService
from attendance_system.ui.camera_thread import CameraThread
from attendance_system.utils.time_utils import utc_now_iso

_FONT_TITLE = QFont("Arial", 20, QFont.Weight.Bold)
_FONT_STATUS = QFont("Arial", 16, QFont.Weight.Bold)
_FONT_BODY = QFont("Arial", 14)

_DEFAULT_LIVENESS_THRESHOLD = 0.5
_DEFAULT_SIMILARITY_THRESHOLD = 0.6


class MainWindow(QMainWindow):
    """
    Main application window.

    IDLE  → user fills subject/class, presses S → creates DB session → ACTIVE
    ACTIVE → live camera feed + recognition result banner → E ends session → IDLE
    Q quits from either state.
    """

    def __init__(
        self,
        attendance_service: AttendanceService,
        settings_service: SettingsService,
        liveness_checker: LivenessChecker,
        face_recognizer: FaceRecognizer,
        camera_index: int = 0,
        detector_model_path: Path | None = None,
    ) -> None:
        super().__init__()
        self._attendance = attendance_service
        self._settings = settings_service
        self._liveness_checker = liveness_checker
        self._face_recognizer = face_recognizer
        self._camera_index = camera_index
        self._detector_model_path = detector_model_path
        self._session_id: int | None = None
        self._camera_thread: CameraThread | None = None

        self.setWindowTitle("Hệ Thống Điểm Danh Khuôn Mặt")
        self.setMinimumSize(700, 520)
        self._build_ui()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        self._stack = QStackedWidget()
        self.setCentralWidget(self._stack)
        self._stack.addWidget(self._build_idle_panel())  # index 0
        self._stack.addWidget(self._build_active_panel())  # index 1
        self._stack.setCurrentIndex(0)

    def _build_idle_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setSpacing(14)
        layout.setContentsMargins(48, 40, 48, 40)

        title = QLabel("Hệ Thống Điểm Danh Khuôn Mặt")
        title.setFont(_FONT_TITLE)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        status = QLabel("Trạng thái: CHỜ  (IDLE)")
        status.setFont(_FONT_STATUS)
        status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        status.setStyleSheet("color: #7f8c8d;")
        layout.addWidget(status)

        layout.addSpacing(12)

        subject_lbl = QLabel("Tên Môn Học:")
        subject_lbl.setFont(_FONT_BODY)
        layout.addWidget(subject_lbl)

        self._subject_input = QLineEdit()
        self._subject_input.setFont(_FONT_BODY)
        self._subject_input.setPlaceholderText("Ví dụ: Trí Tuệ Nhân Tạo")
        layout.addWidget(self._subject_input)

        class_lbl = QLabel("Tên Lớp:")
        class_lbl.setFont(_FONT_BODY)
        layout.addWidget(class_lbl)

        self._class_input = QLineEdit()
        self._class_input.setFont(_FONT_BODY)
        self._class_input.setPlaceholderText("Ví dụ: IT01")
        layout.addWidget(self._class_input)

        layout.addSpacing(12)

        btn_start = QPushButton("Bắt Đầu Phiên Điểm Danh  [S]")
        btn_start.setFont(_FONT_BODY)
        btn_start.clicked.connect(self._start_session)
        layout.addWidget(btn_start)

        btn_quit = QPushButton("Thoát Ứng Dụng  [Q]")
        btn_quit.setFont(_FONT_BODY)
        btn_quit.clicked.connect(self._quit)
        layout.addWidget(btn_quit)

        layout.addStretch()
        return panel

    def _build_active_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setSpacing(12)
        layout.setContentsMargins(48, 24, 48, 24)

        title = QLabel("Hệ Thống Điểm Danh Khuôn Mặt")
        title.setFont(_FONT_TITLE)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        active_status = QLabel("Trạng thái: ĐANG HOẠT ĐỘNG  (ACTIVE)")
        active_status.setFont(_FONT_STATUS)
        active_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        active_status.setStyleSheet("color: #27ae60;")
        layout.addWidget(active_status)

        self._session_info_label = QLabel("")
        self._session_info_label.setFont(_FONT_BODY)
        self._session_info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._session_info_label)

        # Live camera feed
        self._camera_label = QLabel("[ Đang khởi động camera… ]")
        self._camera_label.setFont(_FONT_BODY)
        self._camera_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._camera_label.setStyleSheet(
            "background-color: #2c3e50; color: #ecf0f1; border-radius: 8px;"
        )
        self._camera_label.setMinimumHeight(260)
        self._camera_label.setScaledContents(False)
        layout.addWidget(self._camera_label, stretch=1)

        # Recognition result banner
        self._result_label = QLabel("Đang chờ nhận diện…")
        self._result_label.setFont(_FONT_STATUS)
        self._result_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._result_label.setMinimumHeight(56)
        self._set_result_style("neutral")
        layout.addWidget(self._result_label)

        btn_end = QPushButton("Kết Thúc Phiên  [E]")
        btn_end.setFont(_FONT_BODY)
        btn_end.clicked.connect(self._end_session)
        layout.addWidget(btn_end)

        btn_quit = QPushButton("Thoát Ứng Dụng  [Q]")
        btn_quit.setFont(_FONT_BODY)
        btn_quit.clicked.connect(self._quit)
        layout.addWidget(btn_quit)

        return panel

    # ------------------------------------------------------------------
    # Keyboard shortcuts
    # ------------------------------------------------------------------

    def keyPressEvent(self, a0: QKeyEvent | None) -> None:
        if a0 is None:
            return
        key = a0.key()
        if key == Qt.Key.Key_S:
            self._start_session()
        elif key == Qt.Key.Key_E:
            self._end_session()
        elif key == Qt.Key.Key_Q:
            self._quit()
        else:
            super().keyPressEvent(a0)

    # ------------------------------------------------------------------
    # Session lifecycle (UC-02, UC-04)
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
        self._stack.setCurrentIndex(1)

        # Start camera + AI thread
        self._camera_thread = CameraThread(
            session_id=self._session_id,
            liveness_threshold=liveness_threshold,
            similarity_threshold=similarity_threshold,
            liveness_checker=self._liveness_checker,
            face_recognizer=self._face_recognizer,
            camera_index=self._camera_index,
            detector_model_path=self._detector_model_path,
            parent=self,
        )
        self._camera_thread.frame_ready.connect(self._update_camera_frame)
        self._camera_thread.recognition_result.connect(self._on_recognition_result)
        self._camera_thread.camera_error.connect(self._on_camera_error)
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
        self._stack.setCurrentIndex(0)

    def _quit(self) -> None:
        if self._camera_thread is not None:
            self._camera_thread.stop()
        self.close()

    # ------------------------------------------------------------------
    # Camera thread slots
    # ------------------------------------------------------------------

    def _update_camera_frame(self, frame: QImage) -> None:
        """Display the latest camera frame, scaled to fit the label."""
        pixmap = QPixmap.fromImage(frame).scaled(
            self._camera_label.width(),
            self._camera_label.height(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self._camera_label.setPixmap(pixmap)

    def _on_recognition_result(
        self,
        result_type: str,
        user_id: int,
        full_name: str,
        liveness_score: float,
        similarity_score: float,
    ) -> None:
        """Record event in DB and update result banner (runs in main thread)."""
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
                self.show_result_success(full_name)
            except Exception:
                # UNIQUE constraint hit → already attended this session
                self._attendance.record_duplicate(self._session_id, user_id, now)
                self.show_result_duplicate(full_name)

        elif result_type == "spoof":
            self._attendance.record_spoof_warning(
                self._session_id, now, details=f"liveness={liveness_score:.3f}"
            )
            self.show_result_spoof()

        elif result_type == "unrecognized":
            self._attendance.record_unrecognized(
                self._session_id, now, details=f"liveness={liveness_score:.3f}"
            )
            self.show_result_unrecognized()

    def _on_camera_error(self, message: str) -> None:
        QMessageBox.critical(self, "Lỗi Camera", message)
        self._end_session()

    # ------------------------------------------------------------------
    # Public: recognition result display (UC-03 color feedback)
    # ------------------------------------------------------------------

    def show_result_success(self, name: str) -> None:
        """✅ Green – face recognised, attendance recorded."""
        self._result_label.setText(f"✅  {name}")
        self._set_result_style("success")

    def show_result_duplicate(self, name: str) -> None:
        """⚠️ Yellow – already marked present this session."""
        self._result_label.setText(f"⚠  {name} – Đã điểm danh")
        self._set_result_style("duplicate")

    def show_result_spoof(self) -> None:
        """🚫 Red – liveness check failed."""
        self._result_label.setText("🚫  Cảnh báo: Giả mạo")
        self._set_result_style("spoof")

    def show_result_unrecognized(self) -> None:
        """❌ Yellow – face detected but no match found."""
        self._result_label.setText("❌  Không nhận diện được")
        self._set_result_style("unrecognized")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

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
