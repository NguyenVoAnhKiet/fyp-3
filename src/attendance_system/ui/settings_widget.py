"""Admin Settings widget for configuring hardware and AI parameters (UC-10)."""

from __future__ import annotations

from typing import TYPE_CHECKING

import cv2
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from attendance_system.ui.constants import FONT_BODY
from attendance_system.ui.styles import FONT_H1

if TYPE_CHECKING:
    from attendance_system.services.settings_service import SettingsService

# DB keys
_KEY_CAMERA_INDEX = "camera_index"
_KEY_LIVENESS_THRESHOLD = "liveness_threshold"
_KEY_SIMILARITY_THRESHOLD = "similarity_threshold"

_DEFAULT_LIVENESS = 0.5
_DEFAULT_SIMILARITY = 0.6

# Range of camera indices to probe (0-4 inclusive)
_CAMERA_SCAN_MAX = 5


class _CameraScanThread(QThread):
    """Probe camera indices in a background thread to avoid blocking the UI.

    On Windows, ``cv2.VideoCapture(i)`` on a non-existent index can block for
    several seconds.  Running the scan off the main thread keeps the Settings
    page responsive.
    """

    finished = pyqtSignal(list)  # list[int] — available indices

    def run(self) -> None:
        available: list[int] = []
        for i in range(_CAMERA_SCAN_MAX):
            cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
            if cap.isOpened():
                available.append(i)
                cap.release()
        self.finished.emit(available)


class SettingsWidget(QWidget):
    """Form for editing system-wide settings (camera, thresholds)."""

    def __init__(self, settings_service: SettingsService, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._settings = settings_service
        self._scan_thread: _CameraScanThread | None = None
        self._build_ui()
        self._load_values()
        self._scan_cameras()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(20)

        title = QLabel("Cài Đặt Hệ Thống")
        title.setFont(FONT_H1)
        root.addWidget(title)

        # --- Camera group ---
        cam_group = QGroupBox("Camera")
        cam_group.setFont(FONT_BODY)
        cam_form = QFormLayout(cam_group)

        self._camera_combo = QComboBox()
        self._camera_combo.setFont(FONT_BODY)
        self._camera_combo.addItem("Đang quét…", -1)
        self._camera_combo.setEnabled(False)
        cam_form.addRow("Camera:", self._camera_combo)

        btn_rescan = QPushButton("Quét lại")
        btn_rescan.setFont(FONT_BODY)
        btn_rescan.clicked.connect(self._scan_cameras)
        cam_form.addRow("", btn_rescan)

        root.addWidget(cam_group)

        # --- AI thresholds group ---
        ai_group = QGroupBox("Ngưỡng AI")
        ai_group.setFont(FONT_BODY)
        ai_form = QFormLayout(ai_group)

        self._liveness_spin = QDoubleSpinBox()
        self._liveness_spin.setFont(FONT_BODY)
        self._liveness_spin.setRange(0.0, 1.0)
        self._liveness_spin.setSingleStep(0.05)
        self._liveness_spin.setDecimals(2)
        ai_form.addRow("Ngưỡng Liveness:", self._liveness_spin)

        self._similarity_spin = QDoubleSpinBox()
        self._similarity_spin.setFont(FONT_BODY)
        self._similarity_spin.setRange(0.0, 1.0)
        self._similarity_spin.setSingleStep(0.05)
        self._similarity_spin.setDecimals(2)
        ai_form.addRow("Ngưỡng Similarity:", self._similarity_spin)

        root.addWidget(ai_group)

        # --- Save button ---
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        btn_save = QPushButton("Lưu Cài Đặt")
        btn_save.setFont(FONT_BODY)
        btn_save.clicked.connect(self._save)
        btn_row.addWidget(btn_save)

        root.addLayout(btn_row)
        root.addStretch()

    # ------------------------------------------------------------------
    # Data loading / saving
    # ------------------------------------------------------------------

    def _load_values(self) -> None:
        liveness = self._settings.get(_KEY_LIVENESS_THRESHOLD)
        self._liveness_spin.setValue(float(liveness) if liveness else _DEFAULT_LIVENESS)

        similarity = self._settings.get(_KEY_SIMILARITY_THRESHOLD)
        self._similarity_spin.setValue(float(similarity) if similarity else _DEFAULT_SIMILARITY)

    def _save(self) -> None:
        # Camera index
        cam_idx = self._camera_combo.currentData()
        if cam_idx is not None and cam_idx >= 0:
            self._settings.set(_KEY_CAMERA_INDEX, str(cam_idx), "int")

        # Thresholds
        self._settings.set(
            _KEY_LIVENESS_THRESHOLD,
            str(self._liveness_spin.value()),
            "float",
        )
        self._settings.set(
            _KEY_SIMILARITY_THRESHOLD,
            str(self._similarity_spin.value()),
            "float",
        )

        QMessageBox.information(self, "Cài Đặt", "Đã lưu cài đặt thành công.")

    # ------------------------------------------------------------------
    # Camera scanning
    # ------------------------------------------------------------------

    def _scan_cameras(self) -> None:
        if self._scan_thread is not None and self._scan_thread.isRunning():
            return

        self._camera_combo.clear()
        self._camera_combo.addItem("Đang quét…", -1)
        self._camera_combo.setEnabled(False)

        self._scan_thread = _CameraScanThread(self)
        self._scan_thread.finished.connect(self._on_scan_finished)
        self._scan_thread.start()

    def _on_scan_finished(self, available: list[int]) -> None:
        self._camera_combo.clear()

        if not available:
            self._camera_combo.addItem("Không tìm thấy camera", -1)
            self._camera_combo.setEnabled(False)
            return

        for idx in available:
            self._camera_combo.addItem(f"Camera {idx}", idx)
        self._camera_combo.setEnabled(True)

        # Select the currently saved index (if it exists in the list)
        saved = self._settings.get(_KEY_CAMERA_INDEX)
        if saved is not None:
            saved_idx = int(saved)
            combo_pos = self._camera_combo.findData(saved_idx)
            if combo_pos >= 0:
                self._camera_combo.setCurrentIndex(combo_pos)
