"""Unit tests for the UserModeView freeze/pause feedback feature.

Tests ``_trigger_freeze()``, ``_end_freeze()``, and the integration with
``_on_recognition_result()`` and ``_end_session()``.

All tests use ``unittest.mock`` to avoid needing real services, AI models,
or camera devices.  Follows the exact same pattern as
``test_attendance_callbacks.py``: same ``qapp``, ``mock_service``, and
``view`` fixtures.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QApplication

from attendance_system.core.config import SystemConfig
from attendance_system.core import defaults
from attendance_system.ui.user_mode_view import UserModeView


# ============================================================================
# Fixtures (same pattern as test_attendance_callbacks.py)
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
        hybrid_voting_window=defaults.DEFAULT_HYBRID_VOTING_WINDOW,
        hybrid_boost_amount=defaults.DEFAULT_HYBRID_BOOST_AMOUNT,
        hybrid_liveness_enabled=defaults.DEFAULT_HYBRID_LIVENESS_ENABLED,
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
# Freeze behaviour tests
# ============================================================================

def test_freeze_triggers_on_first_recognition_in_session(
    view: UserModeView,
    mock_service: MagicMock,
) -> None:
    """First ``success`` for a new user must trigger the freeze sequence:
    ``camera_thread.pause()``, overlay shown, and a timer scheduled, and
    ``QApplication.beep()`` NOT called when sound is disabled.
    """
    view._camera_thread = MagicMock()
    view._settings.get.return_value = "4"  # freeze enabled (4 seconds)

    with (
        patch.object(view._freeze_overlay, "show") as mock_show,
        patch("attendance_system.ui.user_mode_view.QApplication.beep") as mock_beep,
    ):
        _invoke_callback(view, "success", user_id=1, full_name="Alice")

        view._camera_thread.pause.assert_called_once()
        mock_show.assert_called_once()
        assert view._freeze_timer is not None
        assert view._freeze_timer.isActive()
        mock_beep.assert_not_called()


def test_freeze_does_not_retrigger_for_same_user(
    view: UserModeView,
    mock_service: MagicMock,
) -> None:
    """A second ``success`` for the same ``user_id`` must NOT call
    ``pause()`` again — the freeze fires only once per user per session.
    """
    view._camera_thread = MagicMock()
    view._settings.get.return_value = "4"

    # First recognition — should trigger freeze
    _invoke_callback(view, "success", user_id=1, full_name="Alice")
    assert view._camera_thread.pause.call_count == 1

    # Second recognition (same user) — must NOT trigger again
    _invoke_callback(view, "success", user_id=1, full_name="Alice")
    assert view._camera_thread.pause.call_count == 1  # still 1


def test_freeze_disabled_when_seconds_is_zero(
    view: UserModeView,
    mock_service: MagicMock,
) -> None:
    """When ``attendance_freeze_seconds`` is ``"0"``, the freeze is disabled:
    no ``pause()`` call, no overlay show, no timer created, no beep sound.
    """
    view._camera_thread = MagicMock()
    view._settings.get.return_value = "0"  # freeze disabled

    with (
        patch.object(view._freeze_overlay, "show") as mock_show,
        patch("attendance_system.ui.user_mode_view.QApplication.beep") as mock_beep,
    ):
        _invoke_callback(view, "success", user_id=1, full_name="Alice")

        view._camera_thread.pause.assert_not_called()
        mock_show.assert_not_called()
        assert view._freeze_timer is None
        mock_beep.assert_not_called()


def test_freeze_overlay_hides_when_timer_fires(
    view: UserModeView,
    mock_service: MagicMock,
) -> None:
    """When ``_end_freeze()`` is called (timer fires), the overlay is hidden,
    the camera is resumed, and ``_freeze_timer`` is cleared.
    """
    view._camera_thread = MagicMock()

    with patch.object(view._freeze_overlay, "hide") as mock_hide:
        view._end_freeze()

        view._camera_thread.resume.assert_called_once()
        mock_hide.assert_called_once()
        assert view._freeze_timer is None


def test_end_session_cancels_pending_freeze(
    view: UserModeView,
    mock_service: MagicMock,
) -> None:
    """``_end_session()`` must cancel any active ``_freeze_timer``, hide the
    overlay, call ``resume()`` on the camera thread, and then stop it.

    Note: we save a reference to ``camera_thread`` *before* calling
    ``_end_session()`` because that method sets ``self._camera_thread = None``
    after stopping it.
    """
    camera_thread = MagicMock()
    view._camera_thread = camera_thread
    mock_timer = MagicMock(spec=QTimer)
    view._freeze_timer = mock_timer

    with patch.object(view._freeze_overlay, "hide") as mock_hide:
        view._end_session()

        mock_timer.stop.assert_called_once()
        assert view._freeze_timer is None
        mock_hide.assert_called_once()
        camera_thread.resume.assert_called_once()
        camera_thread.stop.assert_called_once()


def test_freeze_sound_when_enabled(
    view: UserModeView,
    mock_service: MagicMock,
) -> None:
    """When ``attendance_freeze_sound_enabled`` is ``"true"``,
    ``QApplication.beep()`` is called once at freeze start.
    """
    view._camera_thread = MagicMock()
    view._settings.get.side_effect = lambda key: {
        "attendance_freeze_seconds": "4",
        "attendance_freeze_sound_enabled": "true",
    }.get(key)

    with patch("attendance_system.ui.user_mode_view.QApplication.beep") as mock_beep:
        _invoke_callback(view, "success", user_id=1, full_name="Alice")

        mock_beep.assert_called_once()


def test_no_sound_when_disabled(
    view: UserModeView,
    mock_service: MagicMock,
) -> None:
    """By default (sound disabled), ``QApplication.beep()`` is NOT called."""
    view._camera_thread = MagicMock()
    view._settings.get.return_value = "4"  # freeze enabled, sound disabled

    with patch("attendance_system.ui.user_mode_view.QApplication.beep") as mock_beep:
        _invoke_callback(view, "success", user_id=1, full_name="Alice")

        mock_beep.assert_not_called()
