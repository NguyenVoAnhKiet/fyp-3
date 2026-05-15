from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import cv2
import numpy as np

from attendance_system.services.ai_pipeline import LivenessChecker
from attendance_system.ui.enrollment_camera_thread import (
    EnrollmentCameraThread,
    _HOLD_FRAMES,
)


def _make_face() -> np.ndarray:
    return np.array(
        [100, 100, 160, 160, 0, 0, 100, 0, 50, 50, 0, 0, 0, 0, 0],
        dtype=np.float32,
    )


@patch("cv2.FaceDetectorYN.create")
def test_pose_sequence_advances_on_success(mock_detector_create) -> None:
    detector = MagicMock()
    detector.setInputSize.return_value = None
    mock_detector_create.return_value = detector

    head_pose = MagicMock()
    head_pose.estimate.return_value = (0.0, 0.0, 0.0)
    liveness = MagicMock()
    recognizer = MagicMock()
    recognizer.get_embedding.return_value = np.ones(128, dtype=np.float32)
    recognizer.average_embeddings.return_value = np.ones(128, dtype=np.float32)

    thread = EnrollmentCameraThread(
        camera_index=0,
        liveness_checker=liveness,
        face_recognizer=recognizer,
        head_pose_estimator=head_pose,
        detector_model_path=Path("fake.onnx"),
    )
    thread._pose_hold_counter = 4
    thread._current_pose_index = 0
    thread._attempt_pose_capture = MagicMock(return_value=True)

    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    color = thread._handle_pose_frame(frame, _make_face(), 100, 100, 160, 160)

    assert thread._current_pose_index == 1
    assert thread._pose_hold_counter == 0
    assert color == (0, 255, 0)


@patch("cv2.FaceDetectorYN.create")
def test_pose_hold_resets_on_mismatch(mock_detector_create) -> None:
    detector = MagicMock()
    detector.setInputSize.return_value = None
    mock_detector_create.return_value = detector

    head_pose = MagicMock()
    head_pose.estimate.return_value = (25.0, 25.0, 0.0)
    liveness = MagicMock()
    recognizer = MagicMock()

    thread = EnrollmentCameraThread(
        camera_index=0,
        liveness_checker=liveness,
        face_recognizer=recognizer,
        head_pose_estimator=head_pose,
        detector_model_path=Path("fake.onnx"),
    )
    thread._pose_hold_counter = 3
    thread._current_pose_index = 0

    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    color = thread._handle_pose_frame(frame, _make_face(), 100, 100, 160, 160)

    assert thread._current_pose_index == 0
    assert thread._pose_hold_counter == 0
    assert color == (255, 0, 0)


@patch("cv2.FaceDetectorYN.create")
def test_legacy_fallback_keeps_old_flow(mock_detector_create) -> None:
    detector = MagicMock()
    detector.setInputSize.return_value = None
    mock_detector_create.return_value = detector

    liveness = MagicMock()
    liveness.check.return_value = MagicMock(is_real=True)
    recognizer = MagicMock()
    recognizer.get_embedding.return_value = np.ones(128, dtype=np.float32)

    thread = EnrollmentCameraThread(
        camera_index=0,
        liveness_checker=liveness,
        face_recognizer=recognizer,
        head_pose_estimator=None,
        detector_model_path=Path("fake.onnx"),
    )
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    thread._handle_legacy_frame(frame, frame_rgb, _make_face(), 100, 100, 160, 160)

    assert len(thread._captured_embeddings) == 1
    assert thread._current_pose_index == 0


@patch("cv2.FaceDetectorYN.create")
def test_pose_hold_resets_on_capture_failure(mock_detector_create) -> None:
    """Counter phải reset về 0 khi _attempt_pose_capture thất bại (liveness/embedding fail)."""
    detector = MagicMock()
    detector.setInputSize.return_value = None
    mock_detector_create.return_value = detector

    head_pose = MagicMock()
    head_pose.estimate.return_value = (0.0, 0.0, 0.0)
    liveness = MagicMock()
    recognizer = MagicMock()

    thread = EnrollmentCameraThread(
        camera_index=0,
        liveness_checker=liveness,
        face_recognizer=recognizer,
        head_pose_estimator=head_pose,
        detector_model_path=Path("fake.onnx"),
    )
    thread._pose_hold_counter = 4
    thread._current_pose_index = 0
    thread._attempt_pose_capture = MagicMock(return_value=False)

    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    thread._handle_pose_frame(frame, _make_face(), 100, 100, 160, 160)

    assert thread._pose_hold_counter == 0
    assert thread._current_pose_index == 0


@patch("cv2.FaceDetectorYN.create")
def test_pose_hold_counter_capped_at_hold_frames(mock_detector_create) -> None:
    """Counter không được vượt quá _HOLD_FRAMES dù pose khớp nhiều frame liên tiếp."""
    detector = MagicMock()
    detector.setInputSize.return_value = None
    mock_detector_create.return_value = detector

    head_pose = MagicMock()
    head_pose.estimate.return_value = (0.0, 0.0, 0.0)
    liveness = MagicMock()
    recognizer = MagicMock()
    recognizer.get_embedding.return_value = None

    thread = EnrollmentCameraThread(
        camera_index=0,
        liveness_checker=liveness,
        face_recognizer=recognizer,
        head_pose_estimator=head_pose,
        detector_model_path=Path("fake.onnx"),
    )
    thread._current_pose_index = 0

    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    face = _make_face()

    for _ in range(20):
        thread._handle_pose_frame(frame, face, 100, 100, 160, 160)

    assert thread._pose_hold_counter <= _HOLD_FRAMES


@patch("cv2.FaceDetectorYN.create")
def test_enrollment_succeeds_without_liveness(mock_detector_create) -> None:
    """Enrollment should succeed even when liveness would normally fail on angled poses."""
    detector = MagicMock()
    detector.setInputSize.return_value = None
    mock_detector_create.return_value = detector

    head_pose = MagicMock()
    head_pose.estimate.return_value = (0.0, -30.0, 0.0)  # Nghiêng trái (negative yaw = left turn)
    liveness = MagicMock()
    liveness.check.return_value = MagicMock(is_real=False)  # Would normally fail
    recognizer = MagicMock()
    recognizer.get_embedding.return_value = np.ones(128, dtype=np.float32)
    recognizer.average_embeddings.return_value = np.ones(128, dtype=np.float32)

    # Use LivenessChecker(None) which bypasses liveness
    bypass_liveness = LivenessChecker(None)

    thread = EnrollmentCameraThread(
        camera_index=0,
        liveness_checker=bypass_liveness,
        face_recognizer=recognizer,
        head_pose_estimator=head_pose,
        detector_model_path=Path("fake.onnx"),
    )
    thread._pose_hold_counter = 4
    # Set index to 1 ("Nghiêng trái", yaw=-30) to match the mocked head pose
    thread._current_pose_index = 1

    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    thread._handle_pose_frame(frame, _make_face(), 100, 100, 160, 160)

    # Should advance to next pose because liveness is bypassed
    assert thread._current_pose_index == 2
    assert len(thread._captured_embeddings) == 1


@patch("cv2.FaceDetectorYN.create")
def test_enrollment_liveness_bypass_still_checks_embedding(mock_detector_create) -> None:
    """With liveness bypass, embedding extraction still matters - if it fails, capture should fail."""
    detector = MagicMock()
    detector.setInputSize.return_value = None
    mock_detector_create.return_value = detector

    head_pose = MagicMock()
    head_pose.estimate.return_value = (0.0, 0.0, 0.0)
    liveness = MagicMock()
    bypass_liveness = LivenessChecker(None)
    recognizer = MagicMock()
    recognizer.get_embedding.return_value = None  # Embedding extraction fails

    thread = EnrollmentCameraThread(
        camera_index=0,
        liveness_checker=bypass_liveness,
        face_recognizer=recognizer,
        head_pose_estimator=head_pose,
        detector_model_path=Path("fake.onnx"),
    )
    thread._pose_hold_counter = 4
    thread._current_pose_index = 0

    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    thread._handle_pose_frame(frame, _make_face(), 100, 100, 160, 160)

    # Should NOT advance - embedding extraction failed
    assert thread._current_pose_index == 0
    assert len(thread._captured_embeddings) == 0


@patch("cv2.FaceDetectorYN.create")
def test_pose_sequence_yaw_sign_convention(mock_detector_create) -> None:
    """Verify yaw signs: negative yaw = head turned left, positive yaw = head turned right."""
    from attendance_system.ui.enrollment_camera_thread import _POSE_SEQUENCE

    left_pose = next(p for p in _POSE_SEQUENCE if "trái" in p.name)
    right_pose = next(p for p in _POSE_SEQUENCE if "phải" in p.name)

    # "Nghiêng trái" should have negative yaw (model convention: left = negative)
    assert left_pose.yaw < 0, f"Nghiêng trái should have negative yaw, got {left_pose.yaw}"

    # "Nghiêng phải" should have positive yaw (model convention: right = positive)
    assert right_pose.yaw > 0, f"Nghiêng phải should have positive yaw, got {right_pose.yaw}"


@patch("cv2.FaceDetectorYN.create")
def test_enrollment_accepts_correct_yaw_direction(mock_detector_create) -> None:
    """Enrollment should accept user turning left when asked to turn left (negative yaw)."""
    detector = MagicMock()
    detector.setInputSize.return_value = None
    mock_detector_create.return_value = detector

    # When user turns LEFT, the head pose model outputs NEGATIVE yaw
    head_pose = MagicMock()
    head_pose.estimate.return_value = (0.0, -30.0, 0.0)  # Negative yaw = left turn
    liveness = LivenessChecker(None)
    recognizer = MagicMock()
    recognizer.get_embedding.return_value = np.ones(128, dtype=np.float32)
    recognizer.average_embeddings.return_value = np.ones(128, dtype=np.float32)

    thread = EnrollmentCameraThread(
        camera_index=0,
        liveness_checker=liveness,
        face_recognizer=recognizer,
        head_pose_estimator=head_pose,
        detector_model_path=Path("fake.onnx"),
    )
    thread._current_pose_index = 1  # "Nghiêng trái"
    thread._pose_hold_counter = 4

    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    thread._handle_pose_frame(frame, _make_face(), 100, 100, 160, 160)

    # Should advance because user's left turn matches "Nghiêng trái" (yaw=-30)
    assert thread._current_pose_index == 2


@patch("cv2.FaceDetectorYN.create")
def test_enrollment_rejects_opposite_yaw_direction(mock_detector_create) -> None:
    """Enrollment should NOT accept user turning opposite to what system asks."""
    detector = MagicMock()
    detector.setInputSize.return_value = None
    mock_detector_create.return_value = detector

    # When user turns RIGHT, model outputs POSITIVE yaw
    head_pose = MagicMock()
    head_pose.estimate.return_value = (0.0, 30.0, 0.0)  # Positive yaw = right turn
    liveness = LivenessChecker(None)
    recognizer = MagicMock()

    thread = EnrollmentCameraThread(
        camera_index=0,
        liveness_checker=liveness,
        face_recognizer=recognizer,
        head_pose_estimator=head_pose,
        detector_model_path=Path("fake.onnx"),
    )
    thread._current_pose_index = 1  # "Nghiêng trái" requires yaw=-30
    thread._pose_hold_counter = 4

    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    thread._handle_pose_frame(frame, _make_face(), 100, 100, 160, 160)

    # Should NOT advance because user's right turn (yaw=+30) doesn't match "Nghiêng trái" (yaw=-30)
    assert thread._current_pose_index == 1
    assert thread._pose_hold_counter == 0  # Reset because pose doesn't match


@patch("cv2.FaceDetectorYN.create")
def test_mirrored_frame_flipped_before_processing(mock_detector_create) -> None:
    """Camera frame should be flipped horizontally so display is like a mirror."""
    import inspect

    source = inspect.getsource(EnrollmentCameraThread.run)
    # Verify that cv2.flip with axis=1 is called in the run method
    assert "cv2.flip(frame, 1)" in source or "flip(frame, 1)" in source
