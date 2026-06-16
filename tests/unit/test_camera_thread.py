"""Unit tests for ``CameraThread`` + ``AIWorker`` (attendance flow) and
``EnrollmentCameraThread`` (enrollment flow).

After plan 0005 ``EnrollmentCameraThread.__init__`` requires explicit
``liveness_threshold`` and ``similarity_threshold`` — those values are
plumbed in this file via a small helper that builds a
:class:`attendance_system.core.config.SystemConfig` from
:mod:`attendance_system.core.defaults`.  See plan 0005 (archived
2026-06-05).
"""

from __future__ import annotations

import queue
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import cv2
import numpy as np
import pytest
from PyQt5.QtCore import Qt

from attendance_system.ui.camera_thread import AIWorker, CameraThread
from attendance_system.ui.camera_worker_base import _SENTINEL
from attendance_system.ui.enrollment_camera_thread import EnrollmentCameraThread
from attendance_system.services.ai_pipeline import AIPipeline, LivenessChecker, FaceRecognizer, LivenessResult, RecognitionResult
from attendance_system.services.pipeline_result import PipelineResult
from attendance_system.services.exceptions import LivenessInferenceError

def _make_face() -> np.ndarray:
    # 15 elements: x, y, w, h, eye1_x, eye1_y, eye2_x, eye2_y, nose_x, nose_y, mouth1_x, mouth1_y, mouth2_x, mouth2_y, confidence
    return np.array(
        [100, 100, 160, 160, 120, 140, 180, 140, 150, 160, 130, 180, 170, 180, 0.99],
        dtype=np.float32,
    )

def test_ai_worker_queue_backpressure() -> None:
    liveness = MagicMock(spec=LivenessChecker)
    recognizer = MagicMock(spec=FaceRecognizer)
    
    pipeline = AIPipeline(
        liveness_checker=liveness,
        face_recognizer=recognizer,
        liveness_threshold=0.5,
        similarity_threshold=0.6,
    )
    worker = AIWorker(pipeline=pipeline)
    
    frame_bgr = np.zeros((480, 640, 3), dtype=np.uint8)
    frame_rgb = np.zeros((480, 640, 3), dtype=np.uint8)
    face_row = _make_face()
    
    # First submit should succeed
    res1 = worker.submit_task(frame_bgr, frame_rgb, face_row, 1)
    assert res1 is True
    assert worker._queue.qsize() == 1
    
    # Second submit should fail due to backpressure (queue size = 1)
    res2 = worker.submit_task(frame_bgr, frame_rgb, face_row, 2)
    assert res2 is False
    assert worker._queue.qsize() == 1
    
    # Stop the worker
    worker.stop()

def test_ai_worker_sentinel_termination_and_drain() -> None:
    liveness = MagicMock(spec=LivenessChecker)
    recognizer = MagicMock(spec=FaceRecognizer)
    
    pipeline = AIPipeline(
        liveness_checker=liveness,
        face_recognizer=recognizer,
        liveness_threshold=0.5,
        similarity_threshold=0.6,
    )
    worker = AIWorker(pipeline=pipeline)
    
    frame_bgr = np.zeros((480, 640, 3), dtype=np.uint8)
    frame_rgb = np.zeros((480, 640, 3), dtype=np.uint8)
    face_row = _make_face()
    
    # Submit task
    worker.submit_task(frame_bgr, frame_rgb, face_row, 1)
    assert worker._queue.qsize() == 1
    
    # Stop worker. It should drain the queue and then place _SENTINEL in it.
    worker.stop()
    assert worker._queue.qsize() == 1
    assert worker._queue.get_nowait() is _SENTINEL
    assert not worker.isRunning()

@patch("cv2.FaceDetectorYN.create")
def test_camera_thread_isolation(mock_detector_create) -> None:
    mock_detector_create.side_effect = lambda *args, **kwargs: MagicMock()
    
    liveness = MagicMock(spec=LivenessChecker)
    recognizer = MagicMock(spec=FaceRecognizer)
    
    camera_thread = CameraThread(
        session_id=1,
        liveness_threshold=0.5,
        similarity_threshold=0.6,
        liveness_checker=liveness,
        face_recognizer=recognizer,
        detector_model_path=Path("fake.onnx"),
    )
    
    enrollment_thread = EnrollmentCameraThread(
        camera_index=0,
        liveness_checker=liveness,
        face_recognizer=recognizer,
        liveness_threshold=0.5,
        detector_model_path=Path("fake.onnx"),
        similarity_threshold=0.6,
    )
    
    # They should have created separate detector instances
    assert camera_thread._detector is not enrollment_thread._detector
    assert mock_detector_create.call_count == 2

def test_ai_worker_circuit_breaker() -> None:
    liveness = MagicMock(spec=LivenessChecker)
    liveness.check.side_effect = LivenessInferenceError("ONNX Error")
    
    recognizer = MagicMock(spec=FaceRecognizer)
    
    pipeline = AIPipeline(
        liveness_checker=liveness,
        face_recognizer=recognizer,
        liveness_threshold=0.5,
        similarity_threshold=0.6,
    )
    worker = AIWorker(pipeline=pipeline)
    
    camera_errors = []
    warnings = []
    
    def on_error(msg):
        camera_errors.append(msg)
        
    def on_warning(msg):
        warnings.append(msg)
        
    worker.camera_error.connect(on_error, Qt.ConnectionType.DirectConnection)
    worker.inference_warning.connect(on_warning, Qt.ConnectionType.DirectConnection)
    
    worker.start()
    
    frame_bgr = np.zeros((480, 640, 3), dtype=np.uint8)
    frame_rgb = np.zeros((480, 640, 3), dtype=np.uint8)
    face_row = _make_face()
    
    # Submit 30 tasks
    for i in range(30):
        current_len = len(warnings)
        while not worker.submit_task(frame_bgr, frame_rgb, face_row, i):
            time.sleep(0.001)
        
        # Wait for this task to be processed (up to 2 seconds)
        start_time = time.monotonic()
        while len(warnings) == current_len and len(camera_errors) == 0 and time.monotonic() - start_time < 2.0:
            time.sleep(0.002)
            
    # Once it hits 30 consecutive errors, the circuit breaker should trigger
    # Emit camera_error and stop the thread
    assert len(camera_errors) == 1
    assert "gặp lỗi" in camera_errors[0] or "failed" in camera_errors[0]
    assert worker._running is False
    worker.stop()

def test_ai_worker_recognition_cooldown() -> None:
    liveness = MagicMock(spec=LivenessChecker)
    liveness.check.return_value = LivenessResult(is_real=True, score=0.9)
    
    recognizer = MagicMock(spec=FaceRecognizer)
    # Mock identify to return a user match
    match = RecognitionResult(user_id=42, full_name="John Doe", student_id="SV001", similarity=0.85)
    recognizer.identify.return_value = match
    
    pipeline = AIPipeline(
        liveness_checker=liveness,
        face_recognizer=recognizer,
        liveness_threshold=0.5,
        similarity_threshold=0.6,
    )
    worker = AIWorker(pipeline=pipeline)
    
    results = []
    def on_result(result_type, user_id, name, liveness_score, sim_score):
        results.append((result_type, user_id, name))
        
    worker.recognition_result.connect(on_result, Qt.ConnectionType.DirectConnection)
    
    frame_bgr = np.zeros((480, 640, 3), dtype=np.uint8)
    frame_rgb = np.zeros((480, 640, 3), dtype=np.uint8)
    face_row = _make_face()
    
    # We patch time.monotonic to control cooldown
    with patch("time.monotonic") as mock_time:
        mock_time.return_value = 100.0
        worker.start()
        
        # 1. Submit first task -> should trigger success
        worker.submit_task(frame_bgr, frame_rgb, face_row, 1)
        start_time = time.time()
        while len(results) < 1 and time.time() - start_time < 2.0:
            time.sleep(0.002)
        assert len(results) == 1
        assert results[0] == ("success", 42, "John Doe")
        
        # 2. Submit second task immediately (same user) -> should be ignored due to cooldown (3s)
        # We advance mock_time by 1.0 second (less than 3.0s cooldown)
        mock_time.return_value = 101.0
        identify_calls = 0
        original_identify = recognizer.identify
        def mock_identify(*args, **kwargs):
            nonlocal identify_calls
            identify_calls += 1
            return original_identify(*args, **kwargs)
        recognizer.identify = mock_identify
        
        # Let's submit under cooldown (time = 101.0)
        worker.submit_task(frame_bgr, frame_rgb, face_row, 2)
        start_time = time.time()
        while identify_calls < 1 and time.time() - start_time < 2.0:
            time.sleep(0.002)
        assert identify_calls == 1
        # It should NOT have added to results (still length 1)
        assert len(results) == 1
        
        # 3. Submit third task after cooldown (time = 105.0)
        mock_time.return_value = 105.0
        worker.submit_task(frame_bgr, frame_rgb, face_row, 3)
        start_time = time.time()
        while identify_calls < 2 and time.time() - start_time < 2.0:
            time.sleep(0.002)
        assert identify_calls == 2
        # It SHOULD have emitted success (length 2)
        assert len(results) == 2
        assert results[1] == ("success", 42, "John Doe")
        
        worker.stop()


@patch("cv2.VideoCapture")
@patch("time.sleep")
@patch("cv2.FaceDetectorYN.create")
def test_camera_thread_retry_read_releases_old_cap(mock_detector_create, mock_sleep, mock_video_capture_cls) -> None:
    mock_detector_create.side_effect = lambda *args, **kwargs: MagicMock()
    
    liveness = MagicMock(spec=LivenessChecker)
    recognizer = MagicMock(spec=FaceRecognizer)
    
    camera_thread = CameraThread(
        session_id=1,
        liveness_threshold=0.5,
        similarity_threshold=0.6,
        liveness_checker=liveness,
        face_recognizer=recognizer,
        detector_model_path=Path("fake.onnx"),
    )
    camera_thread._running = True  # simulate running
    
    # Setup mock cap that fails to read
    mock_old_cap = MagicMock()
    mock_old_cap.release = MagicMock()
    
    # Setup mock new cap that succeeds
    mock_new_cap = MagicMock()
    mock_new_cap.isOpened.return_value = True
    mock_new_cap.read.return_value = (True, np.zeros((480, 640, 3), dtype=np.uint8))
    
    mock_video_capture_cls.return_value = mock_new_cap
    
    # Call _retry_read
    success, return_cap, frame = camera_thread._retry_read(mock_old_cap)
    
    assert success is True
    assert return_cap is mock_new_cap
    assert frame is not None
    
    # Verify that the old cap was released BEFORE VideoCapture was reinstantiated
    mock_old_cap.release.assert_called_once()
    mock_video_capture_cls.assert_called_with(camera_thread._camera_index)


# ============================================================================
# Recognition consensus tests
# ============================================================================

from collections import deque
from attendance_system.ui.camera_thread import (
    _CONSENSUS_THRESHOLD,
    _CONSENSUS_WINDOW,
)


class TestComputeConsensus:
    """Pure-function tests for ``CameraThread._compute_consensus``."""

    def test_majority_same_user(self) -> None:
        """2/3 same user → returns (uid, 'success')."""
        buf: deque[tuple[int, str]] = deque(
            [(101, "success"), (101, "success"), (0, "unrecognized")], maxlen=3
        )
        result = CameraThread._compute_consensus(buf, _CONSENSUS_THRESHOLD)
        assert result == (101, "success")

    def test_majority_all_same_user(self) -> None:
        """3/3 same user → returns (uid, 'success')."""
        buf: deque[tuple[int, str]] = deque(
            [(101, "success"), (101, "success"), (101, "success")], maxlen=3
        )
        result = CameraThread._compute_consensus(buf, _CONSENSUS_THRESHOLD)
        assert result == (101, "success")

    def test_no_majority_returns_unrecognized(self) -> None:
        """Mixed users but no real user has 2/3 → returns (0, 'unrecognized')."""
        buf: deque[tuple[int, str]] = deque(
            [(101, "success"), (102, "success"), (0, "unrecognized")], maxlen=3
        )
        result = CameraThread._compute_consensus(buf, _CONSENSUS_THRESHOLD)
        assert result == (0, "unrecognized")

    def test_majority_unrecognized_returns_unrecognized(self) -> None:
        """2/3 unrecognized entries → returns (0, 'unrecognized')."""
        buf: deque[tuple[int, str]] = deque(
            [(0, "unrecognized"), (0, "unrecognized"), (101, "success")], maxlen=3
        )
        result = CameraThread._compute_consensus(buf, _CONSENSUS_THRESHOLD)
        assert result == (0, "unrecognized")

    def test_majority_spoof_returns_spoof(self) -> None:
        """2/3 spoof entries → returns (0, 'spoof')."""
        buf: deque[tuple[int, str]] = deque(
            [(0, "spoof"), (0, "spoof"), (101, "success")], maxlen=3
        )
        result = CameraThread._compute_consensus(buf, _CONSENSUS_THRESHOLD)
        assert result == (0, "spoof")

    def test_majority_all_spoof_returns_spoof(self) -> None:
        """3/3 spoof → returns (0, 'spoof')."""
        buf: deque[tuple[int, str]] = deque(
            [(0, "spoof"), (0, "spoof"), (0, "spoof")], maxlen=3
        )
        result = CameraThread._compute_consensus(buf, _CONSENSUS_THRESHOLD)
        assert result == (0, "spoof")

    def test_mixed_spoof_unrecognized_no_majority(self) -> None:
        """Spoof not majority, no success majority → unrecognized."""
        buf: deque[tuple[int, str]] = deque(
            [(0, "spoof"), (0, "unrecognized"), (0, "unrecognized")], maxlen=3
        )
        result = CameraThread._compute_consensus(buf, _CONSENSUS_THRESHOLD)
        assert result == (0, "unrecognized")

    def test_spoof_edges_does_not_win_over_success(self) -> None:
        """Success majority beats spoof minority."""
        buf: deque[tuple[int, str]] = deque(
            [(101, "success"), (101, "success"), (0, "spoof")], maxlen=3
        )
        result = CameraThread._compute_consensus(buf, _CONSENSUS_THRESHOLD)
        assert result == (101, "success")

    def test_buffer_not_full_returns_none(self) -> None:
        """Fewer than window entries → returns None (suppress)."""
        buf: deque[tuple[int, str]] = deque(
            [(101, "success"), (102, "success")], maxlen=3
        )
        result = CameraThread._compute_consensus(buf, _CONSENSUS_THRESHOLD)
        assert result is None

    def test_empty_buffer_returns_none(self) -> None:
        """Empty buffer → returns None."""
        buf: deque[tuple[int, str]] = deque(maxlen=3)
        result = CameraThread._compute_consensus(buf, _CONSENSUS_THRESHOLD)
        assert result is None


@patch("cv2.FaceDetectorYN.create")
def test_consensus_suppresses_emission_until_window_full(mock_detector_create) -> None:
    """``_on_recognition_result`` suppresses public signal until 3 results."""
    mock_detector_create.side_effect = lambda *args, **kwargs: MagicMock()

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

    emitted: list[tuple] = []
    thread.recognition_result.connect(
        lambda *a: emitted.append(a), Qt.ConnectionType.DirectConnection
    )

    # Feed 3 consecutive success results for user 101
    for i in range(3):
        thread._on_recognition_result(
            result_type="success",
            user_id=101,
            full_name="Alice",
            liveness_score=0.9,
            similarity_score=0.85,
            matched_pose_label="front",
        )

    # Only the 3rd call should have emitted (buffer full + majority)
    assert len(emitted) == 1
    result_type, user_id = emitted[0][0], emitted[0][1]
    assert result_type == "success"
    assert user_id == 101


@patch("cv2.FaceDetectorYN.create")
def test_consensus_emits_spoof_on_spoof_majority(mock_detector_create) -> None:
    """3 consecutive spoof results → consensus emits spoof."""
    mock_detector_create.side_effect = lambda *args, **kwargs: MagicMock()

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

    emitted: list[tuple] = []
    thread.recognition_result.connect(
        lambda *a: emitted.append(a), Qt.ConnectionType.DirectConnection
    )

    for i in range(3):
        thread._on_recognition_result(
            result_type="spoof",
            user_id=0,
            full_name="",
            liveness_score=0.2,
            similarity_score=None,
            matched_pose_label="",
        )

    assert len(emitted) == 1
    assert emitted[0][0] == "spoof"
    assert emitted[0][1] == 0


@patch("cv2.FaceDetectorYN.create")
def test_consensus_resets_on_face_loss(mock_detector_create) -> None:
    """``_process_frame`` clears consensus buffer when no faces detected."""
    mock_detector_create.side_effect = lambda *args, **kwargs: MagicMock()

    liveness = MagicMock(spec=LivenessChecker)
    recognizer = MagicMock(spec=FaceRecognizer)

    frame = np.zeros((480, 640, 3), dtype=np.uint8)

    thread = CameraThread(
        session_id=1,
        liveness_threshold=0.5,
        similarity_threshold=0.6,
        liveness_checker=liveness,
        face_recognizer=recognizer,
        detector_model_path=Path("fake.onnx"),
    )

    # Fill buffer manually
    thread._consensus_buffer.append(101)
    thread._consensus_buffer.append(101)
    thread._consensus_buffer.append(101)
    assert len(thread._consensus_buffer) == 3

    # Process frame with no faces → buffer should clear
    thread._process_frame(frame, faces=None, frame_counter=42)
    assert len(thread._consensus_buffer) == 0

    # Also test with empty faces array
    thread._consensus_buffer.append(101)
    thread._process_frame(frame, faces=np.empty((0, 15)), frame_counter=43)
    assert len(thread._consensus_buffer) == 0


@patch("cv2.FaceDetectorYN.create")
def test_consensus_independent_sessions(mock_detector_create) -> None:
    """Each CameraThread has its own isolated consensus buffer."""
    mock_detector_create.side_effect = lambda *args, **kwargs: MagicMock()

    liveness1, liveness2 = MagicMock(spec=LivenessChecker), MagicMock(spec=LivenessChecker)
    recognizer1, recognizer2 = MagicMock(spec=FaceRecognizer), MagicMock(spec=FaceRecognizer)

    thread_a = CameraThread(session_id=1, liveness_threshold=0.5, similarity_threshold=0.6,
                            liveness_checker=liveness1, face_recognizer=recognizer1,
                            detector_model_path=Path("fake.onnx"))
    thread_b = CameraThread(session_id=2, liveness_threshold=0.5, similarity_threshold=0.6,
                            liveness_checker=liveness2, face_recognizer=recognizer2,
                            detector_model_path=Path("fake.onnx"))

    # Feed results to thread_a only
    for i in range(3):
        thread_a._on_recognition_result(
            result_type="success", user_id=101, full_name="Alice",
            liveness_score=0.9, similarity_score=0.85, matched_pose_label="front",
        )

    # thread_b should have empty buffer
    assert len(thread_b._consensus_buffer) == 0


@patch("cv2.FaceDetectorYN.create")
def test_hybrid_params_forwarded_to_ai_pipeline(mock_detector_create) -> None:
    """CameraThread forwards hybrid params to AIPipeline constructor."""
    mock_detector_create.side_effect = lambda *args, **kwargs: MagicMock()

    liveness = MagicMock(spec=LivenessChecker)
    recognizer = MagicMock(spec=FaceRecognizer)

    thread = CameraThread(
        session_id=1,
        liveness_threshold=0.5,
        similarity_threshold=0.6,
        liveness_checker=liveness,
        face_recognizer=recognizer,
        detector_model_path=Path("fake.onnx"),
        hybrid_liveness_enabled=True,
        hybrid_voting_window=7,
        hybrid_boost_amount=0.20,
        recognition_interval=3,
    )

    pipeline = thread._ai_worker._pipeline
    assert pipeline._hybrid_liveness_enabled is True
    assert pipeline._recognition_interval == 3
    assert pipeline._hybrid_decider._voting_window == 7
    assert pipeline._hybrid_decider._boost_amount == 0.20


@patch("cv2.FaceDetectorYN.create")
def test_consensus_emits_majority_user_data_not_current_frame(mock_detector_create) -> None:
    """Consensus emission uses majority user's auxiliary data, not current frame's."""
    mock_detector_create.side_effect = lambda *args, **kwargs: MagicMock()

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

    emitted: list[tuple] = []
    thread.recognition_result.connect(
        lambda *a: emitted.append(a), Qt.ConnectionType.DirectConnection
    )

    # Frames 1-2: user 101 (majority), Frame 3: user 102 (minority)
    thread._on_recognition_result(
        "success", 101, "Alice", 0.95, 0.88, "front"
    )
    thread._on_recognition_result(
        "success", 101, "Alice", 0.94, 0.87, "front"
    )
    thread._on_recognition_result(
        "success", 102, "Bob", 0.90, 0.76, "left"
    )

    # Buffer = [101, 101, 102] → consensus = 101
    assert len(emitted) == 1
    result_type, user_id, name, ls, ss, pose = emitted[0]
    assert result_type == "success"
    assert user_id == 101
    # Must use Alice's data (last frame for user 101), not Bob's
    assert name == "Alice"
    assert ss == 0.87  # latest similarity for user 101
    assert ls == 0.94  # latest liveness for user 101
    assert pose == "front"  # latest pose for user 101

