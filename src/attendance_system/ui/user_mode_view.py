from __future__ import annotations

import logging
import time
from pathlib import Path


from PyQt5.QtCore import QTimer, Qt, pyqtSignal
from PyQt5.QtGui import QImage, QKeyEvent, QPixmap
from PyQt5.QtWidgets import (
    QFrame,
    QGraphicsDropShadowEffect,
    QGridLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QSizePolicy,
    QVBoxLayout,
    QHBoxLayout,
    QWidget,
)

from attendance_system.services.ai_pipeline import FaceRecognizer, LivenessChecker
from attendance_system.services.attendance_service import AttendanceService
from attendance_system.services.settings_service import SettingsService
from attendance_system.ui.camera_thread import CameraThread
from attendance_system.ui.styles import (
    ACCENT_HOVER,
    ACCENT_PRIMARY,
    BG_CARD,
    BG_INPUT,
    BORDER,
    FONT_BODY,
    FONT_BUTTON,
    FONT_H1,
    FONT_H2,
    FONT_SMALL,
    FONT_STATS,
    STATUS_ERROR,
    STATUS_INFO,
    STATUS_SUCCESS,
    TEXT_MUTED,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
)
from attendance_system.utils.time_utils import utc_now_iso, utc_to_local

logger = logging.getLogger(__name__)

_DEFAULT_LIVENESS_THRESHOLD = 0.3
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
        self._session_started_monotonic: float | None = None



        self._stats_total: int = 0
        self._stats_success: int = 0
        self._stats_spoof: int = 0
        self._stats_unrecognized: int = 0

        self._build_ui()
        self._stats_timer = QTimer(self)
        self._stats_timer.setInterval(1000)
        self._stats_timer.timeout.connect(self._refresh_stats_display)

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(0)

        self._stack = QStackedWidget()
        layout.addWidget(self._stack)

        self._stack.addWidget(self._build_idle_panel())   # _IDX_IDLE
        self._stack.addWidget(self._build_active_panel()) # _IDX_ACTIVE
        self._stack.setCurrentIndex(_IDX_IDLE)

    def _build_idle_panel(self) -> QWidget:
        panel = QWidget()
        outer = QVBoxLayout(panel)
        outer.setContentsMargins(24, 24, 24, 24)
        outer.setSpacing(0)

        outer.addStretch(1)

        title = QLabel("Hệ Thống Điểm Danh Khuôn Mặt")
        title.setFont(FONT_H1)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet(f"color: {TEXT_PRIMARY};")
        outer.addWidget(title)

        outer.addSpacing(18)

        card = QFrame()
        card.setObjectName("idleCard")
        card.setFixedWidth(480)
        card.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Maximum)
        card.setStyleSheet(
            f"QFrame#idleCard {{ background: {BG_CARD}; border: 1px solid {BORDER}; border-radius: 12px; }}"
        )
        shadow = QGraphicsDropShadowEffect(card)
        shadow.setBlurRadius(28)
        shadow.setXOffset(0)
        shadow.setYOffset(8)
        shadow.setColor(Qt.GlobalColor.black)
        card.setGraphicsEffect(shadow)

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(28, 28, 28, 24)
        card_layout.setSpacing(14)

        subject_lbl = QLabel("Tên Môn Học")
        subject_lbl.setFont(FONT_BODY)
        subject_lbl.setStyleSheet(f"color: {TEXT_PRIMARY}; font-weight: 600;")
        card_layout.addWidget(subject_lbl)

        self._subject_input = QLineEdit()
        self._subject_input.setFont(FONT_BODY)
        self._subject_input.setPlaceholderText("▶ Ví dụ: Trí Tuệ Nhân Tạo")
        self._subject_input.setStyleSheet(f"background: {BG_INPUT}; color: {TEXT_PRIMARY};")
        card_layout.addWidget(self._subject_input)

        class_lbl = QLabel("Tên Lớp")
        class_lbl.setFont(FONT_BODY)
        class_lbl.setStyleSheet(f"color: {TEXT_PRIMARY}; font-weight: 600;")
        card_layout.addWidget(class_lbl)

        self._class_input = QLineEdit()
        self._class_input.setFont(FONT_BODY)
        self._class_input.setPlaceholderText("▶ Ví dụ: IT01")
        self._class_input.setStyleSheet(f"background: {BG_INPUT}; color: {TEXT_PRIMARY};")
        card_layout.addWidget(self._class_input)

        btn_start = QPushButton("Bắt Đầu Phiên [S]")
        btn_start.setFont(FONT_BUTTON)
        btn_start.setFixedHeight(44)
        btn_start.setStyleSheet(
            f"QPushButton {{ background: {ACCENT_PRIMARY}; color: white; border: none; border-radius: 10px; }}"
            f"QPushButton:hover {{ background: {ACCENT_HOVER}; }}"
        )
        btn_start.clicked.connect(self._start_session)
        card_layout.addWidget(btn_start)

        btn_admin = QPushButton("Đăng Nhập Quản Trị")
        btn_admin.setFont(FONT_BODY)
        btn_admin.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_admin.setFlat(True)
        btn_admin.setStyleSheet(
            f"QPushButton {{ background: transparent; border: none; color: {TEXT_SECONDARY}; padding: 4px; }}"
            f"QPushButton:hover {{ color: {ACCENT_PRIMARY}; background: transparent; }}"
        )
        btn_admin.clicked.connect(self.login_requested.emit)
        card_layout.addWidget(btn_admin, alignment=Qt.AlignmentFlag.AlignCenter)

        outer.addWidget(card, alignment=Qt.AlignmentFlag.AlignHCenter)

        self._idle_status_label = QLabel("Trạng thái: IDLE")
        self._idle_status_label.setFont(FONT_BODY)
        self._idle_status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._idle_status_label.setStyleSheet(f"color: {TEXT_MUTED};")
        outer.addSpacing(16)
        outer.addWidget(self._idle_status_label)

        outer.addStretch(2)
        return panel

    def _build_active_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(20, 16, 20, 18)
        layout.setSpacing(14)

        header = QWidget()
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(4)

        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)
        top_row.setSpacing(12)

        title = QLabel("Hệ Thống Điểm Danh Khuôn Mặt")
        title.setFont(FONT_H2)
        title.setStyleSheet(f"color: {TEXT_PRIMARY};")
        top_row.addWidget(title)
        top_row.addStretch(1)
        header_layout.addLayout(top_row)

        self._session_info_label = QLabel("")
        self._session_info_label.setFont(FONT_BODY)
        self._session_info_label.setStyleSheet(f"color: {TEXT_SECONDARY};")
        header_layout.addWidget(self._session_info_label)
        layout.addWidget(header)

        content_layout = QHBoxLayout()
        content_layout.setSpacing(16)
        layout.addLayout(content_layout, stretch=1)

        camera_area = QVBoxLayout()
        camera_area.setSpacing(12)
        content_layout.addLayout(camera_area, stretch=2)

        self._camera_label = QLabel("[ Đang khởi động camera… ]")
        self._camera_label.setFont(FONT_BODY)
        self._camera_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._camera_label.setStyleSheet(
            f"background-color: #0f172a; color: #e2e8f0; border: 1px solid {BORDER}; border-radius: 14px;"
        )
        self._camera_label.setMinimumSize(640, 480)
        self._camera_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._camera_label.setScaledContents(False)
        camera_area.addWidget(self._camera_label, stretch=1)



        sidebar_area = QVBoxLayout()
        sidebar_area.setSpacing(12)
        content_layout.addLayout(sidebar_area, stretch=1)

        stats_title = QLabel("📊 Thống Kê")
        stats_title.setFont(FONT_BODY)
        stats_title.setStyleSheet(f"color: {TEXT_PRIMARY}; font-weight: 700;")
        sidebar_area.addWidget(stats_title)

        stats_card = QFrame()
        stats_card.setStyleSheet(
            f"background: {BG_CARD}; border: 1px solid {BORDER}; border-radius: 12px;"
        )
        stats_layout = QGridLayout(stats_card)
        stats_layout.setContentsMargins(12, 12, 12, 12)
        stats_layout.setSpacing(10)
        self._stat_success = self._make_stat_card("Đã ĐD", STATUS_SUCCESS)
        self._stat_unrecognized = self._make_stat_card("Chưa ĐD", STATUS_ERROR)
        self._stat_spoof = self._make_stat_card("Giả Mạo", STATUS_ERROR)
        self._stat_time = self._make_stat_card("Thời Gian", STATUS_INFO)
        stats_layout.addWidget(self._stat_success, 0, 0)
        stats_layout.addWidget(self._stat_unrecognized, 0, 1)
        stats_layout.addWidget(self._stat_spoof, 1, 0)
        stats_layout.addWidget(self._stat_time, 1, 1)
        sidebar_area.addWidget(stats_card)

        list_title = QLabel("📋 Danh Sách Điểm Danh")
        list_title.setFont(FONT_BODY)
        list_title.setStyleSheet(f"color: {TEXT_PRIMARY}; font-weight: 700;")
        sidebar_area.addWidget(list_title)

        self._attendance_list = QListWidget()
        self._attendance_list.setFont(FONT_SMALL)
        self._attendance_list.setStyleSheet(
            f"background: {BG_CARD}; border: 1px solid {BORDER}; border-radius: 12px; padding: 6px;"
        )
        sidebar_area.addWidget(self._attendance_list, stretch=1)

        btn_end = QPushButton("Kết Thúc Phiên [E]")
        btn_end.setFont(FONT_BUTTON)
        btn_end.setFixedHeight(44)
        btn_end.setStyleSheet(
            f"QPushButton {{ background: {STATUS_ERROR}; color: white; border: none; border-radius: 10px; }}"
            f"QPushButton:hover {{ background: #b91c1c; }}"
        )
        btn_end.clicked.connect(self._end_session)
        layout.addWidget(btn_end)

        self._refresh_stats_display()
        return panel

    def _make_stat_card(self, label: str, colour: str) -> QFrame:
        card = QFrame()
        card.setStyleSheet(
            f"background: {BG_CARD}; border: none; border-radius: 10px;"
        )
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(12, 10, 12, 10)
        card_layout.setSpacing(2)

        value = QLabel("0")
        value.setAlignment(Qt.AlignmentFlag.AlignCenter)
        value.setFont(FONT_STATS)
        value.setStyleSheet(f"color: {colour}; line-height: 1;")

        title = QLabel(label)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setFont(FONT_SMALL)
        title.setStyleSheet(f"color: {TEXT_SECONDARY}; font-weight: 700;")

        card_layout.addWidget(value)
        card_layout.addWidget(title)

        card._value_label = value  # type: ignore[attr-defined]
        return card

    def _refresh_stats_display(self) -> None:
        if self._session_started_monotonic is not None:
            elapsed_seconds = max(0, int(time.monotonic() - self._session_started_monotonic))
            elapsed_text = f"{elapsed_seconds // 60:02d}:{elapsed_seconds % 60:02d}"
        else:
            elapsed_text = "00:00"

        unresolved = self._stats_unrecognized + self._stats_spoof
        self._stat_success._value_label.setText(str(self._stats_success))  # type: ignore[attr-defined]
        self._stat_unrecognized._value_label.setText(str(unresolved))  # type: ignore[attr-defined]
        self._stat_spoof._value_label.setText(str(self._stats_spoof))  # type: ignore[attr-defined]
        self._stat_time._value_label.setText(elapsed_text)  # type: ignore[attr-defined]

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)

    def _reset_stats(self) -> None:
        self._stats_total = 0
        self._stats_success = 0
        self._stats_spoof = 0
        self._stats_unrecognized = 0
        self._session_started_monotonic = time.monotonic()
        self._refresh_stats_display()

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
        self._attendance_list.clear()
        self._reset_stats()
        self._stats_timer.start()

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
        self._stats_timer.stop()
        self._subject_input.clear()
        self._class_input.clear()
        self._attendance_list.clear()
        self._stack.setCurrentIndex(_IDX_IDLE)

    def stop_camera(self) -> None:
        """Stop the camera thread if running. Called by MainWindow on close."""
        if self._camera_thread is not None:
            self._camera_thread.stop()
            self._camera_thread = None
        self._stats_timer.stop()

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
        matched_pose_label: str = "",
    ) -> None:
        if self._session_id is None:
            return

        now = utc_now_iso()

        if result_type == "success":
            details = f"matched_pose={matched_pose_label}" if matched_pose_label else None
            try:
                self._attendance.record_success(
                    session_id=self._session_id,
                    user_id=user_id,
                    event_time=now,
                    liveness_score=liveness_score,
                    similarity_score=similarity_score,
                    details=details,
                )
                self._add_to_sidebar(full_name, now)
                self._stats_success += 1
            except Exception:
                self._attendance.record_duplicate(self._session_id, user_id, now, details=details)

        elif result_type == "spoof":
            self._attendance.record_spoof_warning(
                self._session_id, now, details=f"liveness={liveness_score:.3f}"
            )
            self._stats_spoof += 1

        elif result_type == "unrecognized":
            self._attendance.record_unrecognized(
                self._session_id, now, details=f"liveness={liveness_score:.3f}"
            )
            self._stats_unrecognized += 1

        self._stats_total += 1
        self._refresh_stats_display()

    def _on_inference_warning(self, message: str) -> None:
        """Log an inference warning."""
        logger.info("Inference warning: %s", message)

    def _on_camera_error(self, message: str) -> None:
        QMessageBox.critical(self, "Lỗi Camera", message)
        self._end_session()


