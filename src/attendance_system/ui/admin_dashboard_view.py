"""Admin dashboard view: tabs for enrollment, users, settings, history.

Propagates the startup-resolved
:class:`attendance_system.core.config.SystemConfig` to child widgets
(``EnrollmentWidget``, ``SettingsWidget``, ...) so the admin session
uses the same camera / model / threshold values as user mode.  See plan
0005 (archived 2026-06-05) for the resolution design.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QHeaderView,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from attendance_system.ui.constants import FONT_H3, FONT_TAB
from attendance_system.ui.settings_widget import SettingsWidget
from attendance_system.ui.user_management_widget import UserManagementWidget
from attendance_system.ui.enrollment_widget import EnrollmentWidget
from attendance_system.ui.attendance_history_widget import AttendanceHistoryWidget
from attendance_system.ui.styles import (
    ACCENT_PRIMARY,
    BG_CARD,
    BG_SIDEBAR,
    BG_WINDOW,
    FONT_H1,
    FONT_H2,
    FONT_SMALL,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    TEXT_ON_DARK,
    TEXT_ON_DARK_MUTED,
)

if TYPE_CHECKING:
    from attendance_system.repositories.caching_face_reference_repository import (
        CachingFaceReferenceRepository,
    )
    from attendance_system.repositories.face_reference_repository import (
        FaceReferenceRepository,
    )
    from attendance_system.services.settings_service import SettingsService
    from attendance_system.core.config import SystemConfig
    from attendance_system.core.db import Database
    from attendance_system.services.ai_pipeline import FaceRecognizer, LivenessChecker
    from attendance_system.services.head_pose import HeadPoseEstimator

_IDX_WELCOME = 0
_IDX_SETTINGS = 1
_IDX_USERS = 2
_IDX_ENROLLMENT = 3
_IDX_HISTORY = 4


class _NavItem(QFrame):
    clicked = pyqtSignal()

    def __init__(self, icon: str, text: str, tooltip: str, *, logout: bool = False, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._logout = logout
        self._selected = False
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(72)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 8, 4, 8)
        layout.setSpacing(4)

        self._icon_lbl = QLabel(icon)
        self._icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._text_lbl = QLabel(text)
        self._text_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._text_lbl.setFont(FONT_TAB)

        layout.addWidget(self._icon_lbl)
        layout.addWidget(self._text_lbl)
        self.setToolTip(tooltip)
        self._apply_style()

    def set_selected(self, selected: bool) -> None:
        self._selected = selected
        self._apply_style()

    def enterEvent(self, event) -> None:  # type: ignore[override]
        self._apply_style(hover=True)
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:  # type: ignore[override]
        self._apply_style()
        super().leaveEvent(event)

    def mousePressEvent(self, event) -> None:  # type: ignore[override]
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)

    def _apply_style(self, hover: bool = False) -> None:
        if self._logout:
            bg = "#334155" if hover else "transparent"
            color = "#fca5a5" if hover else "#f87171"
            border = f"3px solid {color}" if self._selected else "3px solid transparent"
            self.setStyleSheet(f"background-color: {bg}; border-left: {border}; border-radius: 8px;")
            self._icon_lbl.setStyleSheet(f"font-size: 22px; color: {color};")
            self._text_lbl.setStyleSheet(f"color: {color}; font-size: 13px;")
            return

        bg = "#334155" if hover else ("#0f172a" if self._selected else "transparent")
        border = f"3px solid {ACCENT_PRIMARY}" if self._selected else "3px solid transparent"
        self.setStyleSheet(f"background-color: {bg}; border-left: {border}; border-radius: 8px;")
        icon_color = TEXT_ON_DARK if self._selected or hover else TEXT_ON_DARK_MUTED
        text_color = TEXT_ON_DARK if self._selected or hover else TEXT_ON_DARK_MUTED
        self._icon_lbl.setStyleSheet(f"font-size: 22px; color: {icon_color};")
        self._text_lbl.setStyleSheet(f"color: {text_color}; font-size: 13px;")


class AdminDashboardView(QWidget):
    """
    Admin dashboard shell.

    Contains a sidebar for navigation and a content area.
    Hosts Users management, Enrollment, and Settings.
    Emits ``logout_requested`` when the admin clicks "Đăng Xuất".
    """

    logout_requested = pyqtSignal()

    def __init__(
        self,
        settings_service: SettingsService,
        database: Database,
        liveness_checker: LivenessChecker,
        face_recognizer: FaceRecognizer,
        head_pose_estimator: HeadPoseEstimator | None,
        config: "SystemConfig",
        face_repo: FaceReferenceRepository | CachingFaceReferenceRepository | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._settings_service = settings_service
        self._database = database
        self._liveness_checker = liveness_checker
        self._face_recognizer = face_recognizer
        self._head_pose_estimator = head_pose_estimator
        self._config = config
        self._face_repo = face_repo
        self._nav_items: list[_NavItem] = []
        self._build_ui()

    def _build_ui(self) -> None:
        root_layout = QHBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        root_layout.addWidget(self._build_sidebar())
        root_layout.addWidget(self._build_content_area(), stretch=1)

    def _build_sidebar(self) -> QWidget:
        sidebar = QWidget()
        sidebar.setFixedWidth(90)
        sidebar.setStyleSheet(f"background-color: {BG_SIDEBAR};")

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(8, 12, 8, 12)
        layout.setSpacing(8)

        title = QLabel("🔰 Admin")
        title.setFont(FONT_H3)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet(f"color: {TEXT_ON_DARK}; padding: 12px 0 16px 0;")
        title.setToolTip("Quản Trị Hệ Thống")
        layout.addWidget(title)

        nav_items = [
            ("📊", "Tổng quan", "Tổng Quan Hệ Thống", _IDX_WELCOME),
            ("👤", "Người dùng", "Quản lý Người Dùng", _IDX_USERS),
            ("📷", "Đăng ký", "Đăng Ký Khuôn Mặt", _IDX_ENROLLMENT),
            ("📋", "Lịch sử", "Lịch Sử Điểm Danh", _IDX_HISTORY),
            ("⚙️", "Cài đặt", "Cài Đặt Hệ Thống", _IDX_SETTINGS),
        ]
        for icon, text, tooltip, index in nav_items:
            btn = _NavItem(icon, text, tooltip, parent=self)
            btn.clicked.connect(lambda _=False, i=index, b=btn: self._handle_nav_click(i, b))
            self._nav_items.append(btn)
            layout.addWidget(btn)

        layout.addStretch()

        btn_logout = _NavItem("🚪", "Thoát", "Đăng Xuất", logout=True, parent=self)
        btn_logout.clicked.connect(self.logout_requested.emit)
        layout.addWidget(btn_logout)

        return sidebar

    def _handle_nav_click(self, index: int, btn: _NavItem) -> None:
        self._content_stack.setCurrentIndex(index)
        for item in self._nav_items:
            item.set_selected(item is btn)

    def _build_content_area(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)

        self._content_stack = QStackedWidget()

        self._content_stack.addWidget(self._build_welcome_page())

        settings_page = QWidget()
        settings_layout = QVBoxLayout(settings_page)
        settings_layout.setContentsMargins(32, 32, 32, 32)
        settings_layout.addWidget(SettingsWidget(self._settings_service, parent=self))
        self._content_stack.addWidget(settings_page)

        users_page = QWidget()
        users_layout = QVBoxLayout(users_page)
        users_layout.setContentsMargins(32, 32, 32, 32)
        users_layout.addWidget(
            UserManagementWidget(self._database, parent=self, face_repo=self._face_repo)
        )
        self._content_stack.addWidget(users_page)

        enrollment_page = QWidget()
        enrollment_layout = QVBoxLayout(enrollment_page)
        enrollment_layout.setContentsMargins(32, 32, 32, 32)
        self._enrollment_widget = EnrollmentWidget(
            database=self._database,
            liveness_checker=self._liveness_checker,
            face_recognizer=self._face_recognizer,
            settings_service=self._settings_service,
            head_pose_estimator=self._head_pose_estimator,
            config=self._config,
            face_refs=self._face_repo,
            parent=self,
        )
        enrollment_layout.addWidget(self._enrollment_widget)
        self._content_stack.addWidget(enrollment_page)

        history_page = QWidget()
        history_layout = QVBoxLayout(history_page)
        history_layout.setContentsMargins(32, 32, 32, 32)
        history_layout.addWidget(AttendanceHistoryWidget(self._database, parent=self))
        self._content_stack.addWidget(history_page)

        self._content_stack.setCurrentIndex(_IDX_WELCOME)
        layout.addWidget(self._content_stack)
        return container

    def _build_welcome_page(self) -> QWidget:
        page = QWidget()
        page.setStyleSheet(f"background-color: {BG_WINDOW};")

        layout = QVBoxLayout(page)
        layout.setContentsMargins(32, 28, 32, 32)
        layout.setSpacing(20)

        title = QLabel("📊 Tổng Quan Hệ Thống")
        title.setFont(FONT_H2)
        title.setStyleSheet(f"color: {TEXT_PRIMARY};")
        layout.addWidget(title)

        cards_row = QHBoxLayout()
        cards_row.setSpacing(16)

        total_users, total_sessions, registered_faces, today_sessions = self._load_dashboard_stats()
        cards_row.addWidget(self._build_stat_card("👥", total_users, "Người Dùng"))
        cards_row.addWidget(self._build_stat_card("📋", total_sessions, "Phiên Điểm Danh"))
        cards_row.addWidget(self._build_stat_card("📸", registered_faces, "Đã ĐK Khuôn Mặt"))
        cards_row.addWidget(self._build_stat_card("📅", today_sessions, "Hôm Nay"))
        layout.addLayout(cards_row)

        sessions_header = QLabel("Phiên Gần Đây")
        sessions_header.setFont(FONT_H3)
        sessions_header.setStyleSheet(f"color: {TEXT_PRIMARY}; margin-top: 4px;")
        layout.addWidget(sessions_header)

        layout.addWidget(self._build_recent_sessions())
        return page

    def _load_dashboard_stats(self) -> tuple[int, int, int, int]:
        with self._database.session() as conn:
            total_users = conn.execute("SELECT COUNT(*) as c FROM users WHERE is_active = 1").fetchone()["c"]
            total_sessions = conn.execute("SELECT COUNT(*) as c FROM sessions").fetchone()["c"]
            registered_faces = conn.execute(
                "SELECT COUNT(*) as c FROM users WHERE face_registered = 1 AND is_active = 1"
            ).fetchone()["c"]
            today_sessions = conn.execute(
                "SELECT COUNT(*) as c FROM sessions WHERE date(start_time) = date('now')"
            ).fetchone()["c"]
        return int(total_users), int(total_sessions), int(registered_faces), int(today_sessions)

    def _build_stat_card(self, icon: str, value: int, label: str) -> QFrame:
        card = QFrame()
        card.setMinimumSize(180, 120)
        card.setStyleSheet(
            f"""
            QFrame {{
                background-color: {BG_CARD};
                border-radius: 12px;
            }}
            """
        )

        shadow = QGraphicsDropShadowEffect(card)
        shadow.setBlurRadius(16)
        shadow.setOffset(0, 2)
        shadow.setColor(QColor(0, 0, 0, 15))
        card.setGraphicsEffect(shadow)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(6)
        layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        icon_label = QLabel(icon)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label.setStyleSheet("font-size: 26px; line-height: 1;")

        value_label = QLabel(str(value))
        value_label.setFont(FONT_H1)
        value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        value_label.setStyleSheet(f"color: {TEXT_PRIMARY};")

        text_label = QLabel(label)
        text_label.setFont(FONT_SMALL)
        text_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        text_label.setStyleSheet(f"color: {TEXT_SECONDARY}; letter-spacing: 0.2px;")

        layout.addStretch(1)
        layout.addWidget(icon_label)
        layout.addWidget(value_label)
        layout.addWidget(text_label)
        layout.addStretch(1)
        return card

    def _build_recent_sessions(self) -> QTableWidget:
        table = QTableWidget(0, 4)
        table.setHorizontalHeaderLabels(["Môn Học", "Lớp", "Thời Gian", "Số Lượng"])
        table.setShowGrid(False)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.verticalHeader().setVisible(False)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        table.setAlternatingRowColors(True)
        table.setMinimumHeight(240)

        with self._database.session() as conn:
            rows = conn.execute(
                """
                SELECT
                    s.subject_name,
                    s.class_name,
                    s.start_time,
                    COUNT(ar.id) AS attendance_count
                FROM sessions s
                LEFT JOIN attendance_records ar ON ar.session_id = s.id
                GROUP BY s.id
                ORDER BY s.start_time DESC
                LIMIT 5
                """
            ).fetchall()

        table.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            values = [
                row["subject_name"],
                row["class_name"],
                row["start_time"],
                str(int(row["attendance_count"])),
            ]
            for column_index, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                table.setItem(row_index, column_index, item)

        return table
