"""
Unit tests for ``UserModeView._on_recognition_result()`` callback.

All tests mock ``AttendanceService`` to avoid database writes and mock
``CameraThread`` so no camera device is opened.  The callback is invoked
directly without a Qt event loop.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch, call

import pytest
from PyQt5.QtWidgets import QApplication

from attendance_system.core.config import SystemConfig
from attendance_system.core import defaults
from attendance_system.services.exceptions import SessionClosedError
from attendance_system.ui.user_mode_view import UserModeView


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture(scope="session")
def qapp():
    """Return a shared QApplication instance (created once per session)."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture
def mock_service() -> MagicMock:
    """Return a mock AttendanceService."""
    return MagicMock()


def _make_test_config() -> SystemConfig:
    """Build a SystemConfig with defaults for tests."""
    return SystemConfig(
        database_path=Path("test.db"),
        detection_model_path=defaults.DEFAULT_DETECTOR_MODEL_PATH,
        recognition_model_path=defaults.DEFAULT_RECOGNITION_MODEL_PATH,
        liveness_model_path=None,
        headpose_model_path=defaults.DEFAULT_HEADPOSE_MODEL_PATH,
        camera_index=0,
        antispoof_enabled=True,
        headpose_enabled=True,
        liveness_threshold=defaults.DEFAULT_LIVENESS_THRESHOLD,
        similarity_threshold=defaults.DEFAULT_SIMILARITY_THRESHOLD,
        attendance_freeze_seconds=defaults.DEFAULT_ATTENDANCE_FREEZE_SECONDS,
        attendance_freeze_sound_enabled=defaults.DEFAULT_ATTENDANCE_FREEZE_SOUND_ENABLED,
        timezone=defaults.DEFAULT_TIMEZONE,
    )


@pytest.fixture
def view(mock_service, qapp) -> UserModeView:
    """Build a UserModeView with mocked service and no real camera."""
    with patch(
        "attendance_system.ui.user_mode_view.CameraThread",
        autospec=True,
    ):
        view = UserModeView(
            attendance_service=mock_service,
            settings_service=MagicMock(),
            liveness_checker=MagicMock(),
            face_recognizer=MagicMock(),
            config=_make_test_config(),
        )
    # Simulate an active session
    view._session_id = 42
    return view


# ============================================================================
# Helpers
# ============================================================================

def _invoke_callback(
    view: UserModeView,
    result_type: str = "success",
    user_id: int = 1,
    full_name: str = "Test User",
    liveness_score: float = 0.9,
    similarity_score: float | None = 0.85,
    matched_pose_label: str = "",
) -> None:
    """Invoke ``_on_recognition_result`` directly with the given arguments."""
    view._on_recognition_result(
        result_type,
        user_id,
        full_name,
        liveness_score,
        similarity_score,
        matched_pose_label,
    )


# ============================================================================
# Tests
# ============================================================================

def test_on_recognition_result_success_calls_record_success(view, mock_service) -> None:
    """``success`` result must call ``AttendanceService.record_success()``."""
    _invoke_callback(view, "success", user_id=1, full_name="Alice")

    mock_service.record_success.assert_called_once()
    call_kwargs = mock_service.record_success.call_args[1]
    assert call_kwargs["session_id"] == 42
    assert call_kwargs["user_id"] == 1
    assert "event_time" in call_kwargs


def test_on_recognition_result_duplicate_calls_record_duplicate(view, mock_service) -> None:
    """``success`` result when it fails with IntegrityError calls ``record_duplicate()``.

    The callback does NOT have an explicit ``"duplicate"`` result type.
    Instead, when ``record_success()`` raises any ``Exception`` (except
    ``SessionClosedError``), the callback falls back to ``record_duplicate()``.
    """
    # Make record_success raise IntegrityError (duplicate key scenario)
    mock_service.record_success.side_effect = Exception("Duplicate UNIQUE constraint")

    _invoke_callback(view, "success", user_id=2, full_name="Bob")

    # record_success should have been attempted
    mock_service.record_success.assert_called_once()
    # record_duplicate should have been called as the fallback
    mock_service.record_duplicate.assert_called_once()


def test_on_recognition_result_spoof_calls_record_spoof_warning(view, mock_service) -> None:
    """``spoof`` result must call ``AttendanceService.record_spoof_warning()``."""
    _invoke_callback(view, "spoof", user_id=0, full_name="", liveness_score=0.3)

    mock_service.record_spoof_warning.assert_called_once()
    call_kwargs = mock_service.record_spoof_warning.call_args[0]
    assert call_kwargs[0] == 42  # session_id


def test_on_recognition_result_unrecognized_calls_record_unrecognized(view, mock_service) -> None:
    """``unrecognized`` result must call ``AttendanceService.record_unrecognized()``."""
    _invoke_callback(view, "unrecognized", user_id=0, full_name="", liveness_score=0.2)

    mock_service.record_unrecognized.assert_called_once()
    call_kwargs = mock_service.record_unrecognized.call_args[0]
    assert call_kwargs[0] == 42  # session_id


def test_on_recognition_result_catches_service_exception(view, mock_service) -> None:
    """Callback must not propagate service exceptions; calls record_duplicate instead."""
    mock_service.record_success.side_effect = RuntimeError("Unexpected DB error")

    # Should not raise
    _invoke_callback(view, "success", user_id=1, full_name="Eve")

    # After the error, record_duplicate was called as fallback
    mock_service.record_duplicate.assert_called_once()


@patch("attendance_system.ui.user_mode_view.QMessageBox")
def test_on_recognition_result_catches_session_closed_error(mock_qmessagebox, view, mock_service) -> None:
    """Callback must catch ``SessionClosedError`` and NOT fall through to duplicate."""
    mock_service.record_success.side_effect = SessionClosedError("Session 42 is closed")

    # Should not raise
    _invoke_callback(view, "success", user_id=1, full_name="Frank")

    # QMessageBox.warning must have been called
    mock_qmessagebox.warning.assert_called_once()
    # record_duplicate must NOT be called (session closed is not a duplicate scenario)
    mock_service.record_duplicate.assert_not_called()

