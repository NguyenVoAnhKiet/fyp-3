from __future__ import annotations

from pathlib import Path


from PyQt5.QtCore import Qt
from PyQt5.QtGui import QKeyEvent
from PyQt5.QtWidgets import (
    QLabel,
    QMainWindow,
    QMessageBox,
    QStackedWidget,
)

from attendance_system.core.db import Database
from attendance_system.services.ai_pipeline import FaceRecognizer, LivenessChecker
from attendance_system.services.head_pose import HeadPoseEstimator
from attendance_system.services.attendance_service import AttendanceService
from attendance_system.services.authentication_service import AuthenticationService
from attendance_system.services.settings_service import SettingsService
from attendance_system.ui.admin_dashboard_view import AdminDashboardView
from attendance_system.ui.login_widget import LoginWidget
from attendance_system.ui.styles import BG_WINDOW, GLOBAL_QSS
from attendance_system.ui.user_mode_view import UserModeView

# Master stack indices
_IDX_USER_MODE = 0
_IDX_LOGIN = 1
_IDX_ADMIN_DASHBOARD = 2


class MainWindow(QMainWindow):
    """
    Master application window.

    Acts as a router between three top-level views via a QStackedWidget:
      - UserModeView      (index 0) — the attendance camera screen
      - LoginWidget       (index 1) — admin login form
      - AdminDashboardView(index 2) — admin control panel

    All business logic lives in the individual view components.
    """

    def __init__(
        self,
        attendance_service: AttendanceService,
        settings_service: SettingsService,
        authentication_service: AuthenticationService,
        liveness_checker: LivenessChecker,
        face_recognizer: FaceRecognizer,
        head_pose_estimator: HeadPoseEstimator | None,
        database: Database,
        camera_index: int = 0,
        detector_model_path: Path | None = None,
    ) -> None:
        super().__init__()
        self._auth = authentication_service
        self._database = database
        self._camera_index = camera_index

        self.setWindowTitle("Hệ Thống Điểm Danh Khuôn Mặt")
        self.setMinimumSize(1024, 720)
        self.setStyleSheet(f"QMainWindow {{ background-color: {BG_WINDOW}; }}\n{GLOBAL_QSS}")

        # --- Build views ---
        self._user_mode = UserModeView(
            attendance_service=attendance_service,
            settings_service=settings_service,
            liveness_checker=liveness_checker,
            face_recognizer=face_recognizer,
            camera_index=camera_index,
            detector_model_path=detector_model_path,
            parent=self,
        )
        self._login_widget = LoginWidget(parent=self)
        self._admin_dashboard = AdminDashboardView(
            settings_service=settings_service,
            database=database,
            liveness_checker=liveness_checker,
            face_recognizer=face_recognizer,
            head_pose_estimator=head_pose_estimator,
            detector_model_path=detector_model_path,
            parent=self,
        )

        # --- Master stack ---
        self._stack = QStackedWidget()
        self._stack.addWidget(self._user_mode)       # _IDX_USER_MODE
        self._stack.addWidget(self._login_widget)    # _IDX_LOGIN
        self._stack.addWidget(self._admin_dashboard) # _IDX_ADMIN_DASHBOARD
        self._stack.setCurrentIndex(_IDX_USER_MODE)
        self.setCentralWidget(self._stack)

        # --- Status bar ---
        self._setup_status_bar()

        # --- Wire signals ---
        self._user_mode.login_requested.connect(self._show_login)
        self._login_widget.cancel_requested.connect(self._show_user_mode)
        self._login_widget.login_requested.connect(self._handle_login)
        self._admin_dashboard.logout_requested.connect(self._handle_logout)

    # ------------------------------------------------------------------
    # Status bar
    # ------------------------------------------------------------------

    def _setup_status_bar(self) -> None:
        sb = self.statusBar()
        sb.setStyleSheet("""
            QStatusBar {
                background-color: #ffffff;
                border-top: 1px solid #e2e8f0;
                font-size: 13px;
                color: #64748b;
            }
        """)

        db_path_str = str(self._database.config.path)
        self._status_camera = QLabel(f"📷 Camera: {self._camera_index}")
        self._status_db = QLabel(f"💾 DB: {db_path_str}")
        self._status_session = QLabel("⏸ IDLE")

        for widget in [self._status_camera, self._status_db, self._status_session]:
            widget.setContentsMargins(8, 2, 8, 2)
            sb.addPermanentWidget(widget)

    def update_status_bar(
        self,
        camera_index: int | None = None,
        db_path: str | None = None,
        session_info: str | None = None,
    ) -> None:
        if camera_index is not None:
            self._status_camera.setText(f"📷 Camera: {camera_index}")
        if db_path is not None:
            self._status_db.setText(f"💾 DB: {db_path}")
        if session_info is not None:
            self._status_session.setText(session_info)

    # ------------------------------------------------------------------
    # Routing helpers
    # ------------------------------------------------------------------

    def _show_login(self) -> None:
        self._login_widget.clear_inputs()
        self._stack.setCurrentIndex(_IDX_LOGIN)

    def _show_user_mode(self) -> None:
        self._stack.setCurrentIndex(_IDX_USER_MODE)

    def _handle_login(self, username: str, password: str) -> None:
        if self._auth.authenticate(username, password):
            self._stack.setCurrentIndex(_IDX_ADMIN_DASHBOARD)
        else:
            QMessageBox.warning(
                self,
                "Đăng Nhập Thất Bại",
                "Tên đăng nhập hoặc mật khẩu không đúng.",
            )

    def _handle_logout(self) -> None:
        self._login_widget.clear_inputs()
        self._stack.setCurrentIndex(_IDX_USER_MODE)

    # ------------------------------------------------------------------
    # Global keyboard shortcuts
    # ------------------------------------------------------------------

    def keyPressEvent(self, a0: QKeyEvent | None) -> None:
        if a0 is None:
            return
        key = a0.key()

        # Q quits from any view (but not while a session is active — the
        # UserModeView handles that gracefully via stop_camera).
        if key == Qt.Key.Key_Q:
            self._quit()
            return

        # Delegate all other shortcuts to the currently visible view.
        current = self._stack.currentWidget()
        if current is not None:
            current.keyPressEvent(a0)
        else:
            super().keyPressEvent(a0)

    # ------------------------------------------------------------------
    # Application lifecycle
    # ------------------------------------------------------------------

    def _quit(self) -> None:
        self._user_mode.stop_camera()
        self.close()

    def closeEvent(self, event) -> None:  # type: ignore[override]
        self._user_mode.stop_camera()
        super().closeEvent(event)
