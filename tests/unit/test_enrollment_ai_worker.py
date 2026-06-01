"""Comprehensive unit tests for EnrollmentAIWorker (QThread)."""

from __future__ import annotations

import time
from unittest.mock import MagicMock

import numpy as np
import pytest
from PyQt5.QtCore import Qt

from attendance_system.services.ai_pipeline import FaceRecognizer, LivenessChecker, LivenessResult
from attendance_system.services.exceptions import PoseInferenceError
from attendance_system.services.head_pose import HeadPoseEstimator
from attendance_system.ui.enrollment_ai_worker import EnrollmentAIWorker, _SENTINEL


def _make_face() -> np.ndarray:
    """15-element YuNet face row: x, y, w, h, landmarks (5 pts), confidence."""
    return np.array(
        [100, 100, 160, 160, 120, 140, 180, 140, 150, 160, 130, 180, 170, 180, 0.99],
        dtype=np.float32,
    )


# ---------------------------------------------------------------------------
# 1. Queue backpressure — submit_task returns False when queue is full
# ---------------------------------------------------------------------------


def test_queue_backpressure() -> None:
    worker = EnrollmentAIWorker(
        head_pose_estimator=MagicMock(spec=HeadPoseEstimator),
        liveness_checker=MagicMock(spec=LivenessChecker),
        face_recognizer=MagicMock(spec=FaceRecognizer),
    )
    frame_bgr = np.zeros((480, 640, 3), dtype=np.uint8)
    face_row = _make_face()

    # First submit should succeed
    res1 = worker.submit_task(frame_bgr, face_row, do_capture=False)
    assert res1 is True
    assert worker._queue.qsize() == 1

    # Second submit should fail — queue is full (maxsize=1)
    res2 = worker.submit_task(frame_bgr, face_row, do_capture=False)
    assert res2 is False
    assert worker._queue.qsize() == 1

    worker.stop()


# ---------------------------------------------------------------------------
# 2. Sentinel termination — stop() drains queue and pushes sentinel
# ---------------------------------------------------------------------------


def test_sentinel_termination() -> None:
    worker = EnrollmentAIWorker(
        head_pose_estimator=MagicMock(spec=HeadPoseEstimator),
        liveness_checker=MagicMock(spec=LivenessChecker),
        face_recognizer=MagicMock(spec=FaceRecognizer),
    )
    frame_bgr = np.zeros((480, 640, 3), dtype=np.uint8)
    face_row = _make_face()

    worker.submit_task(frame_bgr, face_row, do_capture=False)
    assert worker._queue.qsize() == 1

    # Stop drains the queue and places _SENTINEL
    worker.stop()
    assert worker._queue.qsize() == 1
    assert worker._queue.get_nowait() is _SENTINEL
    assert not worker.isRunning()


# ---------------------------------------------------------------------------
# 3. Pose estimation only (do_capture=False)
# ---------------------------------------------------------------------------


def test_pose_estimation_only() -> None:
    head_pose = MagicMock(spec=HeadPoseEstimator)
    head_pose.estimate.return_value = (10.0, 20.0, 5.0)
    liveness = MagicMock(spec=LivenessChecker)
    recognizer = MagicMock(spec=FaceRecognizer)

    worker = EnrollmentAIWorker(
        head_pose_estimator=head_pose,
        liveness_checker=liveness,
        face_recognizer=recognizer,
    )

    pose_results: list[tuple[float, float, float]] = []
    capture_results: list[tuple] = []

    worker.pose_estimated.connect(
        lambda *a: pose_results.append(a), Qt.ConnectionType.DirectConnection
    )
    worker.capture_complete.connect(
        lambda *a: capture_results.append(a), Qt.ConnectionType.DirectConnection
    )

    frame_bgr = np.zeros((480, 640, 3), dtype=np.uint8)
    face_row = _make_face()

    worker.start()
    worker.submit_task(frame_bgr, face_row, do_capture=False)

    start = time.time()
    while len(pose_results) == 0 and time.time() - start < 3.0:
        time.sleep(0.01)

    assert len(pose_results) == 1
    pitch, yaw, roll = pose_results[0]
    assert (pitch, yaw, roll) == (10.0, 20.0, 5.0)

    # capture_complete should NOT have been emitted
    assert len(capture_results) == 0
    # Liveness + recognizer should never have been called
    liveness.check.assert_not_called()
    recognizer.get_embedding.assert_not_called()

    worker.stop()


# ---------------------------------------------------------------------------
# 4. Capture complete — success path (liveness real + embedding)
# ---------------------------------------------------------------------------


def test_capture_complete_success() -> None:
    head_pose = MagicMock(spec=HeadPoseEstimator)
    head_pose.estimate.return_value = (0.0, 0.0, 0.0)
    liveness = MagicMock(spec=LivenessChecker)
    liveness.check.return_value = LivenessResult(is_real=True, score=0.95)
    recognizer = MagicMock(spec=FaceRecognizer)
    expected_emb = np.ones(128, dtype=np.float32)
    recognizer.get_embedding.return_value = expected_emb

    worker = EnrollmentAIWorker(
        head_pose_estimator=head_pose,
        liveness_checker=liveness,
        face_recognizer=recognizer,
        liveness_threshold=0.5,
    )

    pose_results: list[tuple[float, float, float]] = []
    capture_results: list[tuple] = []

    worker.pose_estimated.connect(
        lambda *a: pose_results.append(a), Qt.ConnectionType.DirectConnection
    )
    worker.capture_complete.connect(
        lambda *a: capture_results.append(a), Qt.ConnectionType.DirectConnection
    )

    frame_bgr = np.zeros((480, 640, 3), dtype=np.uint8)
    face_row = _make_face()

    worker.start()
    worker.submit_task(frame_bgr, face_row, do_capture=True)

    # Wait for both signals (allow up to 5 s total)
    start = time.time()
    while (len(pose_results) == 0 or len(capture_results) == 0) and time.time() - start < 5.0:
        time.sleep(0.01)

    assert len(pose_results) == 1
    assert len(capture_results) == 1

    success, emb, score = capture_results[0]
    assert success is True
    assert isinstance(emb, np.ndarray)
    assert np.array_equal(emb, expected_emb)
    assert score == pytest.approx(0.95)

    worker.stop()


# ---------------------------------------------------------------------------
# 5. Capture — embedding returns None
# ---------------------------------------------------------------------------


def test_capture_embedding_failure() -> None:
    head_pose = MagicMock(spec=HeadPoseEstimator)
    head_pose.estimate.return_value = (0.0, 0.0, 0.0)
    liveness = MagicMock(spec=LivenessChecker)
    liveness.check.return_value = LivenessResult(is_real=True, score=0.95)
    recognizer = MagicMock(spec=FaceRecognizer)
    recognizer.get_embedding.return_value = None  # embedding failure

    worker = EnrollmentAIWorker(
        head_pose_estimator=head_pose,
        liveness_checker=liveness,
        face_recognizer=recognizer,
        liveness_threshold=0.5,
    )

    capture_results: list[tuple] = []

    worker.capture_complete.connect(
        lambda *a: capture_results.append(a), Qt.ConnectionType.DirectConnection
    )

    frame_bgr = np.zeros((480, 640, 3), dtype=np.uint8)
    face_row = _make_face()

    worker.start()
    worker.submit_task(frame_bgr, face_row, do_capture=True)

    start = time.time()
    while len(capture_results) == 0 and time.time() - start < 3.0:
        time.sleep(0.01)

    assert len(capture_results) == 1
    success, emb, score = capture_results[0]
    assert success is False
    assert emb is None
    assert score == pytest.approx(0.95)

    worker.stop()


# ---------------------------------------------------------------------------
# 6. Circuit breaker — 30 consecutive PoseInferenceError triggers camera_error
# ---------------------------------------------------------------------------


def test_circuit_breaker_pose_error() -> None:
    head_pose = MagicMock(spec=HeadPoseEstimator)
    head_pose.estimate.side_effect = PoseInferenceError("model error")
    liveness = MagicMock(spec=LivenessChecker)
    recognizer = MagicMock(spec=FaceRecognizer)

    worker = EnrollmentAIWorker(
        head_pose_estimator=head_pose,
        liveness_checker=liveness,
        face_recognizer=recognizer,
    )

    camera_errors: list[str] = []
    warnings: list[str] = []

    worker.camera_error.connect(
        lambda msg: camera_errors.append(msg), Qt.ConnectionType.DirectConnection
    )
    worker.inference_warning.connect(
        lambda msg: warnings.append(msg), Qt.ConnectionType.DirectConnection
    )

    frame_bgr = np.zeros((480, 640, 3), dtype=np.uint8)
    face_row = _make_face()

    worker.start()

    # Submit 30 tasks — each triggers a PoseInferenceError
    for i in range(30):
        current_warnings = len(warnings)
        while not worker.submit_task(frame_bgr, face_row, do_capture=False):
            time.sleep(0.001)

        start_t = time.monotonic()
        while (
            len(warnings) == current_warnings
            and len(camera_errors) == 0
            and time.monotonic() - start_t < 2.0
        ):
            time.sleep(0.002)

    # The 30th consecutive failure should emit camera_error and stop the thread
    assert len(camera_errors) == 1
    assert "Mô hình AI gặp lỗi" in camera_errors[0]
    assert worker._running is False

    worker.stop()


# ---------------------------------------------------------------------------
# 7. Circuit breaker resets — successful pose resets counter
# ---------------------------------------------------------------------------


def test_circuit_breaker_recovers() -> None:
    """Consecutive-failure counter resets on successful pose estimation,
    so the circuit breaker never trips even though errors occur in bursts.
    """
    call_count: int = 0

    def head_pose_side_effect(_crop: np.ndarray) -> tuple[float, float, float]:
        nonlocal call_count
        call_count += 1
        # Raise error for the first 5 calls
        if call_count <= 5:
            raise PoseInferenceError("model error")
        # Succeed on the 6th call
        if call_count == 6:
            return (0.0, 0.0, 0.0)
        # Raise error for the next 5 calls (7-11)
        raise PoseInferenceError("model error")

    head_pose = MagicMock(spec=HeadPoseEstimator)
    head_pose.estimate.side_effect = head_pose_side_effect
    liveness = MagicMock(spec=LivenessChecker)
    recognizer = MagicMock(spec=FaceRecognizer)

    worker = EnrollmentAIWorker(
        head_pose_estimator=head_pose,
        liveness_checker=liveness,
        face_recognizer=recognizer,
    )

    camera_errors: list[str] = []
    warnings: list[str] = []
    pose_results: list[tuple[float, float, float]] = []

    worker.camera_error.connect(
        lambda msg: camera_errors.append(msg), Qt.ConnectionType.DirectConnection
    )
    worker.inference_warning.connect(
        lambda msg: warnings.append(msg), Qt.ConnectionType.DirectConnection
    )
    worker.pose_estimated.connect(
        lambda *a: pose_results.append(a), Qt.ConnectionType.DirectConnection
    )

    frame_bgr = np.zeros((480, 640, 3), dtype=np.uint8)
    face_row = _make_face()

    worker.start()

    # Phase 1 — 5 errors (each emits a warning)
    for _ in range(5):
        current_warns = len(warnings)
        while not worker.submit_task(frame_bgr, face_row, do_capture=False):
            time.sleep(0.001)
        start_t = time.monotonic()
        while len(warnings) == current_warns and time.monotonic() - start_t < 2.0:
            time.sleep(0.002)

    assert len(warnings) >= 5
    assert len(camera_errors) == 0  # breaker not tripped yet

    # Phase 2 — 1 success (counter resets, pose_estimated emitted)
    current_poses = len(pose_results)
    while not worker.submit_task(frame_bgr, face_row, do_capture=False):
        time.sleep(0.001)
    start_t = time.monotonic()
    while len(pose_results) == current_poses and time.monotonic() - start_t < 2.0:
        time.sleep(0.002)

    assert len(pose_results) == current_poses + 1
    assert worker._consecutive_failures == 0  # counter was reset

    # Phase 3 — 5 more errors (counter climbs from 0 → 5, still < 30)
    for _ in range(5):
        current_warns = len(warnings)
        while not worker.submit_task(frame_bgr, face_row, do_capture=False):
            time.sleep(0.001)
        start_t = time.monotonic()
        while len(warnings) == current_warns and time.monotonic() - start_t < 2.0:
            time.sleep(0.002)

    # circuit breaker should NOT have tripped
    assert len(camera_errors) == 0
    # We should have 10 warnings total (5 + 5)
    assert len(warnings) >= 10

    worker.stop()


# ---------------------------------------------------------------------------
# 8. Frame copy — submitted arrays are not shared with originals
# ---------------------------------------------------------------------------


def test_frame_copy() -> None:
    worker = EnrollmentAIWorker(
        head_pose_estimator=MagicMock(spec=HeadPoseEstimator),
        liveness_checker=MagicMock(spec=LivenessChecker),
        face_recognizer=MagicMock(spec=FaceRecognizer),
    )

    original_bgr = np.zeros((480, 640, 3), dtype=np.uint8)
    original_face = _make_face()

    worker.submit_task(original_bgr, original_face, do_capture=False)

    do_capture, queued_bgr, queued_face = worker._queue.get_nowait()

    assert not np.shares_memory(original_bgr, queued_bgr)
    assert not np.shares_memory(original_face, queued_face)

    worker.stop()
