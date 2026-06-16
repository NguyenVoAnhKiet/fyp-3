"""Admin Settings widget for configuring hardware and AI parameters (UC-10).

Reads initial spinbox values from :mod:`attendance_system.core.defaults`
(single source of truth for tunables) and persists user edits via
:class:`attendance_system.services.settings_service.SettingsService`
(DB CRUD wrapper).  The widget does **not** know about CLI / env
precedence — that lives in
:class:`attendance_system.core.config.SettingsResolver`.

See plan 0005 (archived 2026-06-05) for the full design.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import time

import numpy as np

import cv2
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from attendance_system.core import defaults
from attendance_system.ui.constants import FONT_BODY
from attendance_system.ui.styles import FONT_H1
from attendance_system.utils.time_utils import format_tz_label, set_timezone_config

if TYPE_CHECKING:
    from attendance_system.services.settings_service import SettingsService

# DB keys
_KEY_CAMERA_INDEX = "camera_index"
_KEY_LIVENESS_THRESHOLD = "liveness_threshold"
_KEY_SIMILARITY_THRESHOLD = "similarity_threshold"
_KEY_TIMEZONE = "timezone"

_KEY_FREEZE_SECONDS = "attendance_freeze_seconds"
_KEY_FREEZE_SOUND_ENABLED = "attendance_freeze_sound_enabled"

# Range of camera indices to probe (0-4 inclusive)
_CAMERA_SCAN_MAX = 5

# Timezone choices in display order (first is default, UTC is last)
TIMEZONE_CHOICES: list[str] = [
    "Asia/Ho_Chi_Minh",
    "Asia/Bangkok",
    "Asia/Singapore",
    "Asia/Tokyo",
    "Asia/Seoul",
    "Asia/Shanghai",
    "Asia/Kolkata",
    "Australia/Sydney",
    "Europe/London",
    "Europe/Paris",
    "America/New_York",
    "America/Los_Angeles",
    "UTC",
]


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
                ret1, frame1 = cap.read()
                if ret1 and frame1 is not None:
                    time.sleep(0.15)
                    ret2, frame2 = cap.read()
                    if ret2 and frame2 is not None and not np.array_equal(frame1, frame2):
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

        # --- Display group ---
        display_group = QGroupBox("Hiển Thị")
        display_group.setFont(FONT_BODY)
        display_form = QFormLayout(display_group)

        self._tz_combo = QComboBox()
        self._tz_combo.setFont(FONT_BODY)
        self._tz_combo.setEditable(False)
        for name in TIMEZONE_CHOICES:
            self._tz_combo.addItem(format_tz_label(name), userData=name)
        display_form.addRow("Múi giờ:", self._tz_combo)

        root.addWidget(display_group)

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

        # --- Attendance Freeze group ---
        freeze_group = QGroupBox("Điểm Danh")
        freeze_group.setFont(FONT_BODY)
        freeze_form = QFormLayout(freeze_group)

        self._freeze_spin = QSpinBox()
        self._freeze_spin.setFont(FONT_BODY)
        self._freeze_spin.setRange(0, 10)
        self._freeze_spin.setSingleStep(1)
        self._freeze_spin.setSuffix(" giây")
        freeze_form.addRow("Thời gian đóng băng:", self._freeze_spin)

        freeze_hint = QLabel("Đặt 0 để tắt hiệu ứng đóng băng khi điểm danh thành công")
        freeze_hint.setFont(FONT_BODY)
        freeze_hint.setStyleSheet("color: #888888;")
        freeze_form.addRow("", freeze_hint)

        self._freeze_sound_check = QCheckBox("Phát âm thanh khi điểm danh thành công")
        self._freeze_sound_check.setFont(FONT_BODY)
        freeze_form.addRow("", self._freeze_sound_check)

        root.addWidget(freeze_group)

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
        tz_raw = self._settings.get(_KEY_TIMEZONE)
        tz_name = tz_raw if tz_raw else defaults.DEFAULT_TIMEZONE
        try:
            idx = TIMEZONE_CHOICES.index(tz_name)
        except ValueError:
            idx = 0  # fall back to first choice
        self._tz_combo.setCurrentIndex(idx)

        liveness = self._settings.get(_KEY_LIVENESS_THRESHOLD)
        self._liveness_spin.setValue(
            float(liveness) if liveness else defaults.DEFAULT_LIVENESS_THRESHOLD
        )

        similarity = self._settings.get(_KEY_SIMILARITY_THRESHOLD)
        self._similarity_spin.setValue(
            float(similarity) if similarity else defaults.DEFAULT_SIMILARITY_THRESHOLD
        )

        freeze_seconds = self._settings.get(_KEY_FREEZE_SECONDS)
        self._freeze_spin.setValue(
            int(freeze_seconds) if freeze_seconds else defaults.DEFAULT_ATTENDANCE_FREEZE_SECONDS
        )
        freeze_sound = self._settings.get(_KEY_FREEZE_SOUND_ENABLED)
        self._freeze_sound_check.setChecked(
            freeze_sound is not None
            and freeze_sound.lower() in {"1", "true", "yes", "on"}
        )

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

        # Freeze settings
        self._settings.set(_KEY_FREEZE_SECONDS, str(self._freeze_spin.value()), "int")
        self._settings.set(
            _KEY_FREEZE_SOUND_ENABLED,
            "true" if self._freeze_sound_check.isChecked() else "false",
            "bool",
        )

        # Timezone — persist & apply immediately
        tz_iana = self._tz_combo.currentData()
        self._settings.set(_KEY_TIMEZONE, tz_iana, "str")
        set_timezone_config(tz_iana)

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
