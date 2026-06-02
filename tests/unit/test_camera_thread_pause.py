"""Unit tests for CameraThread pause/resume functionality.

Tests the public ``pause()`` / ``resume()`` API and the ``_paused`` flag.
Uses ``unittest.mock`` to avoid needing a real camera device.

Following the pattern in ``test_camera_thread.py``: real ``CameraThread``
instances are constructed with mocked ``LivenessChecker``, ``FaceRecognizer``,
and a patched ``cv2.FaceDetectorYN.create``.
"""

from __future__ import annotations

import time as _TIME_MODULE
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np

from attendance_system.services.ai_pipeline import FaceRecognizer, LivenessChecker
from attendance_system.ui.camera_thread import CameraThread

# Save a reference to the real sleep BEFORE any patch can replace it.
_ORIGINAL_SLEEP = _TIME_MODULE.sleep


# ============================================================================
# Helpers
# ============================================================================

def _make_thread() -> CameraThread:
    """Build a CameraThread with mocked dependencies (no real camera)."""
    liveness = MagicMock(spec=LivenessChecker)
    recognizer = MagicMock(spec=FaceRecognizer)

    with patch("cv2.FaceDetectorYN.create") as mock_detector_create:
        mock_detector_create.side_effect = lambda *args, **kwargs: MagicMock()
        return CameraThread(
            session_id=1,
            liveness_threshold=0.5,
            similarity_threshold=0.6,
            liveness_checker=liveness,
            face_recognizer=recognizer,
            detector_model_path=Path("fake.onnx"),
        )


# ============================================================================
# Tests
# ============================================================================

def test_initial_state_is_not_paused() -> None:
    """A freshly constructed CameraThread has ``_paused is False``."""
    thread = _make_thread()
    assert thread._paused is False


def test_pause_sets_flag() -> None:
    """``pause()`` sets ``self._paused = True``."""
    thread = _make_thread()
    thread.pause()
    assert thread._paused is True


def test_resume_clears_flag() -> None:
    """``resume()`` sets ``self._paused = False``."""
    thread = _make_thread()
    thread._paused = True
    thread.resume()
    assert thread._paused is False


def test_pause_is_idempotent() -> None:
    """Calling ``pause()`` twice does not raise and keeps the flag set."""
    thread = _make_thread()
    thread.pause()
    thread.pause()  # should not raise
    assert thread._paused is True


@patch("cv2.VideoCapture")
@patch("time.sleep")
@patch("cv2.FaceDetectorYN.create")
def test_run_loop_skips_read_while_paused(
    mock_detector_create: MagicMock,
    mock_sleep: MagicMock,
    mock_video_capture_cls: MagicMock,
) -> None:
    """When ``_paused`` is True, ``cap.read()`` is never called inside the
    ``run()`` loop — the loop sleep-skips instead."""
    mock_detector_create.side_effect = lambda *args, **kwargs: MagicMock()

    mock_cap = MagicMock()
    mock_cap.isOpened.return_value = True
    mock_cap.read.return_value = (True, np.zeros((480, 640, 3), dtype=np.uint8))
    mock_video_capture_cls.return_value = mock_cap

    liveness = MagicMock(spec=LivenessChecker)
    recognizer = MagicMock(spec=FaceRecognizer)

    thread = CameraThread(
        session_id=1,
        liveness_threshold=0.5,
        similarity_threshold=0.6,
        liveness_checker=liveness,
        face_recognizer=recognizer,
        detector_model_path=Path("fake.onnx"),
    )
    thread._paused = True  # freeze before starting

    # Allow tiny real sleeps so the test doesn't busy-spin; the patched
    # ``time.sleep(0.05)`` inside the paused loop is capped to 1 ms.
    # We use ``_ORIGINAL_SLEEP`` (captured at module level before patching)
    # to avoid infinite recursion through the mock.
    mock_sleep.side_effect = lambda s: _ORIGINAL_SLEEP(min(s, 0.001))

    thread.start()
    _ORIGINAL_SLEEP(0.3)  # give thread time to set up and enter the loop
    thread.stop()

    # cap.read() should never be reached — the loop continues past it
    # while _paused is True.
    mock_cap.read.assert_not_called()
