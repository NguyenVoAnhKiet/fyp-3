from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QFrame,
    QGraphicsDropShadowEffect,
    QMessageBox,
)
from attendance_system.ui.styles import (
    ACCENT_HOVER,
    ACCENT_PRIMARY,
    BG_CARD,
    BG_INPUT,
    BG_WINDOW,
    BORDER,
    BORDER_FOCUS,
    FONT_BODY,
    FONT_BUTTON,
    FONT_H1,
    FONT_H3,
    TEXT_SECONDARY,
    TEXT_MUTED,
    TEXT_PRIMARY,
)

class LoginWidget(QWidget):
    """
    UI for admin authentication.
    Emits login_requested(username, password) or cancel_requested().
    """
    login_requested = pyqtSignal(str, str)
    cancel_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        self.setStyleSheet(f"background-color: {BG_WINDOW};")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(32, 32, 32, 32)
        outer.setSpacing(0)
        outer.addStretch(1)

        card = QFrame()
        card.setObjectName("loginCard")
        card.setFixedWidth(400)
        card.setStyleSheet(
            f"""
            QFrame#loginCard {{
                background-color: {BG_CARD};
                border-radius: 12px;
            }}
            QLabel#appTitle {{
                color: {TEXT_PRIMARY};
            }}
            QLabel#appSubtitle {{
                color: {TEXT_SECONDARY};
            }}
            QLabel#inputIcon {{
                background-color: {BG_INPUT};
                color: {TEXT_MUTED};
                border: 1px solid {BORDER};
                border-right: none;
                border-top-left-radius: 10px;
                border-bottom-left-radius: 10px;
                min-width: 40px;
                max-width: 40px;
            }}
            QLineEdit#loginInput {{
                background-color: {BG_INPUT};
                border: 1px solid {BORDER};
                border-top-right-radius: 10px;
                border-bottom-right-radius: 10px;
                border-left: none;
                padding: 10px 14px;
                color: {TEXT_PRIMARY};
            }}
            QLineEdit#loginInput:focus {{
                background-color: #ffffff;
                border: 1px solid {BORDER_FOCUS};
                border-left: none;
            }}
            QPushButton#loginButton {{
                background-color: {ACCENT_PRIMARY};
                color: white;
                border: none;
                border-radius: 10px;
                padding: 0 16px;
            }}
            QPushButton#loginButton:hover {{
                background-color: {ACCENT_HOVER};
            }}
            QPushButton#loginButton:pressed {{
                background-color: #1e40af;
            }}
            QPushButton#backButton {{
                background: transparent;
                border: none;
                color: {TEXT_SECONDARY};
                padding: 0;
                text-decoration: none;
            }}
            QPushButton#backButton:hover {{
                color: {TEXT_PRIMARY};
                text-decoration: underline;
            }}
            """
        )

        shadow = QGraphicsDropShadowEffect(card)
        shadow.setBlurRadius(24)
        shadow.setOffset(0, 4)
        shadow.setColor(QColor(0, 0, 0, 30))
        card.setGraphicsEffect(shadow)

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(32, 32, 32, 32)
        card_layout.setSpacing(0)

        title = QLabel("Facial Attendance")
        title.setObjectName("appTitle")
        title.setFont(FONT_H1)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        subtitle = QLabel("Hệ Thống Điểm Danh Khuôn Mặt")
        subtitle.setObjectName("appSubtitle")
        subtitle.setFont(FONT_BODY)
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)

        card_layout.addWidget(title)
        card_layout.addSpacing(4)
        card_layout.addWidget(subtitle)
        card_layout.addSpacing(24)

        user_field, self._user_input = self._make_input_row("👤", "Nhập tên quản trị viên", False)
        pass_field, self._pass_input = self._make_input_row("🔒", "Nhập mật khẩu", True)
        self._user_input.returnPressed.connect(self._on_login_clicked)
        self._pass_input.returnPressed.connect(self._on_login_clicked)

        card_layout.addWidget(user_field)
        card_layout.addSpacing(12)
        card_layout.addWidget(pass_field)
        card_layout.addSpacing(16)

        self._btn_login = QPushButton("Đăng Nhập")
        self._btn_login.setObjectName("loginButton")
        self._btn_login.setFont(FONT_BUTTON)
        self._btn_login.setMinimumHeight(44)
        self._btn_login.clicked.connect(self._on_login_clicked)
        card_layout.addWidget(self._btn_login)

        card_layout.addSpacing(12)

        self._btn_back = QPushButton("Quay Lại")
        self._btn_back.setObjectName("backButton")
        self._btn_back.setFont(FONT_BODY)
        self._btn_back.setMinimumHeight(28)
        self._btn_back.clicked.connect(self.cancel_requested.emit)

        back_row = QHBoxLayout()
        back_row.setContentsMargins(0, 0, 0, 0)
        back_row.addStretch(1)
        back_row.addWidget(self._btn_back)
        back_row.addStretch(1)
        card_layout.addLayout(back_row)

        outer.addWidget(card, 0, Qt.AlignmentFlag.AlignHCenter)
        outer.addStretch(1)

    def _make_input_row(self, icon: str, placeholder: str, is_password: bool) -> tuple[QFrame, QLineEdit]:
        field = QFrame()
        field.setObjectName("loginField")

        row = QHBoxLayout(field)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(0)

        icon_lbl = QLabel(icon)
        icon_lbl.setObjectName("inputIcon")
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_lbl.setFont(FONT_H3)
        icon_lbl.setFixedHeight(44)

        input_widget = QLineEdit()
        input_widget.setObjectName("loginInput")
        input_widget.setFont(FONT_BODY)
        input_widget.setPlaceholderText(placeholder)
        input_widget.setMinimumHeight(44)
        if is_password:
            input_widget.setEchoMode(QLineEdit.EchoMode.Password)

        row.addWidget(icon_lbl)
        row.addWidget(input_widget)

        return field, input_widget

    def _on_login_clicked(self):
        user = self._user_input.text().strip()
        pw = self._pass_input.text().strip()

        if not user or not pw:
            QMessageBox.warning(
                self,
                "Thiếu Thông Tin",
                "Vui lòng nhập đầy đủ Tên đăng nhập và Mật khẩu."
            )
            return

        self.login_requested.emit(user, pw)

    def clear_inputs(self):
        self._user_input.clear()
        self._pass_input.clear()
        self._user_input.setFocus()
