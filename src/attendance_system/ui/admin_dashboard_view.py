from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from attendance_system.ui.constants import FONT_BODY, FONT_TITLE
from attendance_system.ui.settings_widget import SettingsWidget
from attendance_system.ui.user_management_widget import UserManagementWidget

if TYPE_CHECKING:
    from attendance_system.services.settings_service import SettingsService
    from attendance_system.core.db import Database

# Content-area stack indices
_IDX_WELCOME = 0
_IDX_SETTINGS = 1
_IDX_USERS = 2


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
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._settings_service = settings_service
        self._database = database
        self._build_ui()

    def _build_ui(self) -> None:
        root_layout = QHBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        root_layout.addWidget(self._build_sidebar())
        root_layout.addWidget(self._build_content_area(), stretch=1)

    def _build_sidebar(self) -> QWidget:
        sidebar = QWidget()
        sidebar.setFixedWidth(80)
        sidebar.setStyleSheet("background-color: #2c3e50;")

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        # Sidebar title - compact version
        title = QLabel("AD")
        title.setFont(FONT_TITLE)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("color: white; padding: 20px 0;")
        title.setToolTip("Quản Trị Hệ Thống")
        layout.addWidget(title)

        # Navigation items (Emoji icon, Tooltip text, click handler)
        nav_items = [
            ("👤", "Quản lý Người Dùng", lambda: self._content_stack.setCurrentIndex(_IDX_USERS)),
            ("📷", "Đăng Ký Khuôn Mặt", None),
            ("📋", "Lịch Sử Điểm Danh", None),
            ("⚙️", "Cài Đặt Hệ Thống", lambda: self._content_stack.setCurrentIndex(_IDX_SETTINGS)),
        ]
        for icon, tooltip, handler in nav_items:
            btn = QPushButton(icon)
            btn.setFont(FONT_TITLE)
            btn.setToolTip(tooltip)
            btn.setStyleSheet("""
                QPushButton {
                    color: #bdc3c7;
                    background: transparent;
                    border: none;
                    padding: 15px 0;
                    text-align: center;
                }
                QPushButton:hover {
                    background-color: #34495e;
                    color: white;
                }
            """)
            if handler is not None:
                btn.clicked.connect(handler)
            layout.addWidget(btn)

        layout.addStretch()

        # Logout button at the bottom
        btn_logout = QPushButton("🚪")
        btn_logout.setFont(FONT_TITLE)
        btn_logout.setToolTip("Đăng Xuất")
        btn_logout.setStyleSheet("""
            QPushButton {
                color: #e74c3c;
                background: transparent;
                border: none;
                border-top: 1px solid #34495e;
                padding: 20px 0;
                text-align: center;
            }
            QPushButton:hover {
                background-color: #34495e;
            }
        """)
        btn_logout.clicked.connect(self.logout_requested.emit)
        layout.addWidget(btn_logout)

        return sidebar

    def _build_content_area(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)

        self._content_stack = QStackedWidget()

        # Welcome / placeholder page
        welcome = QWidget()
        welcome_layout = QVBoxLayout(welcome)
        welcome_layout.setContentsMargins(32, 32, 32, 32)
        placeholder = QLabel("Chào mừng đến Trang Quản Trị.\nChọn chức năng từ thanh bên.")
        placeholder.setFont(FONT_BODY)
        placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        placeholder.setStyleSheet("color: #7f8c8d;")
        welcome_layout.addWidget(placeholder, alignment=Qt.AlignmentFlag.AlignCenter)
        self._content_stack.addWidget(welcome)  # _IDX_WELCOME

        # Settings page
        settings_page = QWidget()
        settings_layout = QVBoxLayout(settings_page)
        settings_layout.setContentsMargins(32, 32, 32, 32)
        settings_layout.addWidget(SettingsWidget(self._settings_service, parent=self))
        self._content_stack.addWidget(settings_page)  # _IDX_SETTINGS

        # Users page
        users_page = QWidget()
        users_layout = QVBoxLayout(users_page)
        users_layout.setContentsMargins(32, 32, 32, 32)
        users_layout.addWidget(UserManagementWidget(self._database, parent=self))
        self._content_stack.addWidget(users_page)  # _IDX_USERS

        self._content_stack.setCurrentIndex(_IDX_WELCOME)
        layout.addWidget(self._content_stack)

        return container
