from __future__ import annotations

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from attendance_system.ui.constants import FONT_BODY, FONT_TITLE


class AdminDashboardView(QWidget):
    """
    Admin dashboard shell.

    Contains a sidebar for navigation and a content area for future admin
    screens (Users, Enrollment, History, Settings).
    Emits ``logout_requested`` when the admin clicks "Đăng Xuất".
    """

    logout_requested = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
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

        # Navigation items (Emoji icon, Tooltip text)
        nav_items = [
            ("👤", "Quản lý Người Dùng"),
            ("📷", "Đăng Ký Khuôn Mặt"),
            ("📋", "Lịch Sử Điểm Danh"),
            ("⚙️", "Cài Đặt Hệ Thống"),
        ]
        for icon, tooltip in nav_items:
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
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(32, 32, 32, 32)

        placeholder = QLabel("Chào mừng đến Trang Quản Trị.\nChọn chức năng từ thanh bên.")
        placeholder.setFont(FONT_BODY)
        placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        placeholder.setStyleSheet("color: #7f8c8d;")
        layout.addWidget(placeholder, alignment=Qt.AlignmentFlag.AlignCenter)

        return content
