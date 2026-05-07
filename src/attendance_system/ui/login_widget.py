from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QMessageBox,
)
from attendance_system.ui.constants import FONT_TITLE, FONT_BODY

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
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(64, 40, 64, 40)

        # Center everything
        layout.addStretch()

        # Title
        title = QLabel("Đăng Nhập Quản Trị")
        title.setFont(FONT_TITLE)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        layout.addSpacing(20)

        # Username
        user_lbl = QLabel("Tên Đăng Nhập:")
        user_lbl.setFont(FONT_BODY)
        layout.addWidget(user_lbl)

        self._user_input = QLineEdit()
        self._user_input.setFont(FONT_BODY)
        self._user_input.setPlaceholderText("Nhập tên quản trị viên")
        self._user_input.returnPressed.connect(self._on_login_clicked)
        layout.addWidget(self._user_input)

        # Password
        pass_lbl = QLabel("Mật Khẩu:")
        pass_lbl.setFont(FONT_BODY)
        layout.addWidget(pass_lbl)

        self._pass_input = QLineEdit()
        self._pass_input.setFont(FONT_BODY)
        self._pass_input.setPlaceholderText("Nhập mật khẩu")
        self._pass_input.setEchoMode(QLineEdit.EchoMode.Password)
        self._pass_input.returnPressed.connect(self._on_login_clicked)
        layout.addWidget(self._pass_input)

        layout.addSpacing(24)

        # Login button
        self._btn_login = QPushButton("Đăng Nhập")
        self._btn_login.setFont(FONT_BODY)
        self._btn_login.setMinimumHeight(44)
        # Use a slightly more premium style for the primary button
        self._btn_login.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QPushButton:pressed {
                background-color: #2471a3;
            }
        """)
        self._btn_login.clicked.connect(self._on_login_clicked)
        layout.addWidget(self._btn_login)

        # Back button
        self._btn_back = QPushButton("Quay Lại")
        self._btn_back.setFont(FONT_BODY)
        self._btn_back.setMinimumHeight(44)
        self._btn_back.clicked.connect(self.cancel_requested.emit)
        layout.addWidget(self._btn_back)

        layout.addStretch()

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
