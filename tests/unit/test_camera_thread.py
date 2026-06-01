from __future__ import annotations

import queue
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import cv2
import numpy as np
import pytest
from PyQt5.QtCore import Qt

from attendance_system.ui.camera_thread import AIWorker, CameraThread, _SENTINEL
from attendance_system.ui.enrollment_camera_thread import EnrollmentCameraThread
from attendance_system.services.ai_pipeline import LivenessChecker, FaceRecognizer, LivenessResult, RecognitionResult
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
    
    worker = AIWorker(
        liveness_threshold=0.5,
        similarity_threshold=0.6,
        liveness_checker=liveness,
        face_recognizer=recognizer,
    )
    
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
    
    worker = AIWorker(
        liveness_threshold=0.5,
        similarity_threshold=0.6,
        liveness_checker=liveness,
        face_recognizer=recognizer,
    )
    
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
    )
    
    # They should have created separate detector instances
    assert camera_thread._detector is not enrollment_thread._detector
    assert mock_detector_create.call_count == 2

def test_ai_worker_circuit_breaker() -> None:
    liveness = MagicMock(spec=LivenessChecker)
    liveness.check.side_effect = LivenessInferenceError("ONNX Error")
    
    recognizer = MagicMock(spec=FaceRecognizer)
    
    worker = AIWorker(
        liveness_threshold=0.5,
        similarity_threshold=0.6,
        liveness_checker=liveness,
        face_recognizer=recognizer,
    )
    
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
    assert "Liveness model failed" in camera_errors[0]
    assert worker._running is False
    worker.stop()

def test_ai_worker_recognition_cooldown() -> None:
    liveness = MagicMock(spec=LivenessChecker)
    liveness.check.return_value = LivenessResult(is_real=True, score=0.9)
    
    recognizer = MagicMock(spec=FaceRecognizer)
    # Mock identify to return a user match
    match = RecognitionResult(user_id=42, full_name="John Doe", student_id="SV001", similarity=0.85)
    recognizer.identify.return_value = match
    
    worker = AIWorker(
        liveness_threshold=0.5,
        similarity_threshold=0.6,
        liveness_checker=liveness,
        face_recognizer=recognizer,
    )
    
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

