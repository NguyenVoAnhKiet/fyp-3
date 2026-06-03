"""Comprehensive unit tests for camera_worker_base base classes.

Tests cover:
- AIWorkerBase: task processing, queue drain, circuit breaker, copy semantics
- CameraThreadBase: retry-read with exponential backoff, pause/resume
"""

from __future__ import annotations

import time
from unittest.mock import MagicMock, patch

import cv2
import numpy as np
import pytest
from PyQt5.QtCore import Qt

from attendance_system.ui.camera_worker_base import AIWorkerBase, CameraThreadBase, _SENTINEL


def _make_face() -> np.ndarray:
    """15-element YuNet face row: x, y, w, h, landmarks (5 pts), confidence."""
    return np.array(
        [100, 100, 160, 160, 120, 140, 180, 140, 150, 160, 130, 180, 170, 180, 0.99],
        dtype=np.float32,
    )


# ===================================================================
# Stub subclasses for testing
# ===================================================================


class StubWorker(AIWorkerBase):
    """Tracks every task passed to _process_frame."""

    def __init__(self) -> None:
        super().__init__(pipeline=None)
        self.processed: list = []

    def _process_frame(self, task) -> None:
        self.processed.append(task)


class ErrorWorker(AIWorkerBase):
    """Raises RuntimeError on every _process_frame call."""

    def __init__(self) -> None:
        super().__init__(pipeline=None)

    def _process_frame(self, task) -> None:
        raise RuntimeError("test inference error")

    def _inference_error_types(self):
        return (RuntimeError,)


class ResetWorker(AIWorkerBase):
    """Fails the first 29 _process_frame calls, succeeds on the 30th."""

    def __init__(self) -> None:
        super().__init__(pipeline=None)
        self.call_count = 0
        self.succeeded = False

    def _process_frame(self, task) -> None:
        self.call_count += 1
        if self.call_count < 30:
            raise RuntimeError("test error")
        self.succeeded = True

    def _inference_error_types(self):
        return (RuntimeError,)


class StubCameraThread(CameraThreadBase):
    """Minimal concrete subclass — no-op _process_frame."""

    def _process_frame(
        self, frame: np.ndarray, faces: np.ndarray | None, frame_counter: int
    ) -> None:
        pass


# ===================================================================
# AIWorkerBase tests
# ===================================================================


class TestAIWorkerBase:
    """Tests for AIWorkerBase lifecycle and queue mechanics."""

    # ------------------------------------------------------------------
    # 1. Basic task processing
    # ------------------------------------------------------------------

    def test_processes_submitted_frame(self) -> None:
        """Submit a task, start the worker, verify _process_frame is called."""
        worker = StubWorker()
        task = ("hello", 42)

        worker.submit_task(*task)
        worker.start()

        try:
            start = time.monotonic()
            while len(worker.processed) == 0 and time.monotonic() - start < 3.0:
                time.sleep(0.005)

            assert len(worker.processed) == 1
            # The task tuple is stored in the queue; _process_frame receives it
            assert worker.processed[0] == task
        finally:
            worker.stop()

    def test_drains_queue_on_stop(self) -> None:
        """Submit a task then stop without starting — task is drained,
        sentinel placed, and the worker reports not running."""
        worker = StubWorker()
        worker.submit_task("hello", 42)

        # Stop without starting: drain + sentinel
        worker.stop()

        assert worker._queue.qsize() == 1
        assert worker._queue.get_nowait() is _SENTINEL
        assert not worker.isRunning()

    # ------------------------------------------------------------------
    # 2. Circuit breaker
    # ------------------------------------------------------------------

    def test_circuit_breaker_kills_thread_after_threshold_failures(self) -> None:
        """30 consecutive inference errors emits camera_error and stops the
        worker."""
        worker = ErrorWorker()

        camera_errors: list[str] = []

        worker.camera_error.connect(
            lambda msg: camera_errors.append(msg),
            Qt.ConnectionType.DirectConnection,
        )

        worker.start()

        try:
            # Submit 30 tasks — each triggers RuntimeError caught by the
            # circuit breaker.
            for i in range(30):
                while not worker.submit_task(f"task_{i}"):
                    time.sleep(0.001)

                # Wait for this error to be processed (or for camera_error)
                start_t = time.monotonic()
                while (
                    len(camera_errors) == 0
                    and time.monotonic() - start_t < 2.0
                ):
                    time.sleep(0.002)

            # The 30th consecutive failure should have tripped the breaker
            assert len(camera_errors) == 1
            assert "Mô hình AI gặp lỗi" in camera_errors[0]
            assert worker._running is False
        finally:
            worker.stop()

    def test_circuit_breaker_resets_on_success(self) -> None:
        """Consecutive-failure counter resets when a call succeeds, so 30
        intermittent errors never trip the breaker."""
        worker = ResetWorker()

        camera_errors: list[str] = []
        warnings: list[str] = []

        worker.camera_error.connect(
            lambda msg: camera_errors.append(msg),
            Qt.ConnectionType.DirectConnection,
        )
        worker.inference_warning.connect(
            lambda msg: warnings.append(msg),
            Qt.ConnectionType.DirectConnection,
        )

        worker.start()

        try:
            # Phase 1 — 29 consecutive errors (each emits a warning)
            for _ in range(29):
                current_warns = len(warnings)
                while not worker.submit_task("x"):
                    time.sleep(0.001)
                start_t = time.monotonic()
                while (
                    len(warnings) == current_warns
                    and time.monotonic() - start_t < 2.0
                ):
                    time.sleep(0.002)

            # Phase 2 — 30th call succeeds → counter resets
            current_warns = len(warnings)
            while not worker.submit_task("x"):
                time.sleep(0.001)

            # Wait for the success to be processed
            start_t = time.monotonic()
            while (
                not worker.succeeded
                and time.monotonic() - start_t < 2.0
            ):
                time.sleep(0.002)

            assert worker.succeeded is True
            # Counter was reset back to zero on success
            assert worker._consecutive_failures == 0
            # No camera_error should have been emitted
            assert len(camera_errors) == 0
        finally:
            worker.stop()

    # ------------------------------------------------------------------
    # 3. Sentinel terminates idle worker
    # ------------------------------------------------------------------

    def test_sentinel_terminates_idle_worker(self) -> None:
        """An idle worker (blocked on queue.get timeout) exits promptly when
        stop() is called."""
        worker = StubWorker()

        worker.start()
        # Give the thread time to enter the run loop and block on queue.get
        time.sleep(0.05)

        assert worker.isRunning()

        worker.stop()

        assert not worker.isRunning()

    # ------------------------------------------------------------------
    # 4. NumPy array copy semantics
    # ------------------------------------------------------------------

    def test_numpy_arrays_copied(self) -> None:
        """submit_task copies numpy arrays so the caller can safely mutate
        originals without affecting the queued data."""
        worker = StubWorker()

        original_arr = np.array([1.0, 2.0, 3.0], dtype=np.float64)
        original_face = _make_face()

        worker.submit_task(original_arr, original_face)

        queued_arr, queued_face = worker._queue.get_nowait()

        assert not np.shares_memory(original_arr, queued_arr)
        assert not np.shares_memory(original_face, queued_face)

        # Verify values are identical
        assert np.array_equal(original_arr, queued_arr)
        assert np.array_equal(original_face, queued_face)

        worker.stop()


# ===================================================================
# CameraThreadBase tests
# ===================================================================


class TestCameraThreadBase:
    """Tests for CameraThreadBase retry-read and pause/resume."""

    # ------------------------------------------------------------------
    # 5. Retry-read succeeds after failures
    # ------------------------------------------------------------------

    @patch("attendance_system.ui.camera_worker_base.time.sleep")
    @patch("attendance_system.ui.camera_worker_base.cv2.VideoCapture")
    @patch("attendance_system.ui.camera_worker_base._create_face_detector")
    def test_retry_read_success(
        self,
        mock_detector: MagicMock,
        mock_vc_cls: MagicMock,
        mock_sleep: MagicMock,
    ) -> None:
        """_retry_read reconnects and succeeds on the third attempt."""
        mock_detector.return_value = MagicMock()

        # Build three distinct VideoCapture mocks
        caps = [MagicMock() for _ in range(3)]
        for i, cap in enumerate(caps):
            cap.isOpened.return_value = True
            # First two attempts fail to read; third succeeds
            if i < 2:
                cap.read.return_value = (False, None)
            else:
                cap.read.return_value = (True, np.zeros((480, 640, 3), dtype=np.uint8))
        mock_vc_cls.side_effect = caps

        old_cap = MagicMock()
        thread = StubCameraThread(camera_index=0)
        thread._running = True

        success, ret_cap, frame = thread._retry_read(old_cap)

        assert success is True
        assert ret_cap is caps[2]
        assert frame is not None
        # The old cap was released once at the start of iteration 1
        old_cap.release.assert_called_once()
        # Failed caps from iterations 1 and 2 were also released
        caps[0].release.assert_called_once()
        caps[1].release.assert_called_once()
        # The final (successful) cap should NOT have been released
        assert caps[2].release.call_count == 0

    # ------------------------------------------------------------------
    # 6. Retry-read gives up
    # ------------------------------------------------------------------

    @patch("attendance_system.ui.camera_worker_base.time.sleep")
    @patch("attendance_system.ui.camera_worker_base.cv2.VideoCapture")
    @patch("attendance_system.ui.camera_worker_base._create_face_detector")
    def test_retry_read_gives_up(
        self,
        mock_detector: MagicMock,
        mock_vc_cls: MagicMock,
        mock_sleep: MagicMock,
    ) -> None:
        """_retry_read returns (False, cap, None) when all attempts fail."""
        mock_detector.return_value = MagicMock()

        caps = [MagicMock() for _ in range(3)]
        for cap in caps:
            cap.isOpened.return_value = True
            cap.read.return_value = (False, None)
        mock_vc_cls.side_effect = caps

        old_cap = MagicMock()
        thread = StubCameraThread(camera_index=0)
        thread._running = True

        success, ret_cap, frame = thread._retry_read(old_cap)

        assert success is False
        assert ret_cap is caps[2]  # last created cap (never succeeded)
        assert frame is None

    # ------------------------------------------------------------------
    # 7. Pause / resume
    # ------------------------------------------------------------------

    @patch("attendance_system.ui.camera_worker_base._create_face_detector")
    def test_pause_resume(
        self,
        mock_detector: MagicMock,
    ) -> None:
        """pause() and resume() toggle the _paused flag."""
        mock_detector.return_value = MagicMock()

        thread = StubCameraThread(camera_index=0)

        assert thread._paused is False

        thread.pause()
        assert thread._paused is True

        thread.resume()
        assert thread._paused is False

        # Toggle again to confirm idempotent behaviour
        thread.pause()
        assert thread._paused is True

        thread.pause()
        assert thread._paused is True  # already paused

        thread.resume()
        assert thread._paused is False
