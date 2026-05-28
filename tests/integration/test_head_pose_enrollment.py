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
    liveness = MagicMock()
    recognizer = MagicMock()

    thread = EnrollmentCameraThread(
        camera_index=0,
        liveness_checker=liveness,
        face_recognizer=recognizer,
        head_pose_estimator=head_pose,
        detector_model_path=Path("fake.onnx"),
    )
    thread._current_pose_index = 0
    from attendance_system.ui.enrollment_camera_thread import _POSE_SEQUENCE
    thread._captured_embeddings_by_pose = {
        _POSE_SEQUENCE[i].storage_label: np.ones(128, dtype=np.float32)
        for i in range(4)
    }

    # Call the signal handler directly (simulates EnrollmentAIWorker completing capture)
    emb = np.ones(128, dtype=np.float32)
    thread._on_capture_complete(True, emb, 0.95)

    assert thread._current_pose_index == 1
    assert thread._capture_in_progress is False


@patch("cv2.FaceDetectorYN.create")
def test_pose_hold_resets_on_mismatch(mock_detector_create) -> None:
    detector = MagicMock()
    detector.setInputSize.return_value = None
    mock_detector_create.return_value = detector

    head_pose = MagicMock()
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
    thread._current_pose_index = 0  # Target: (0, 0)

    # Call signal handler with non-matching pose (25, 25) — far from target (0, 0)
    thread._on_pose_estimated(25.0, 25.0, 0.0)

    assert thread._current_pose_index == 0
    assert thread._pose_hold_counter == 0  # Reset because pose doesn't match


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

    assert len(thread._captured_embeddings_by_pose) == 1
    assert thread._current_pose_index == 0


@patch("cv2.FaceDetectorYN.create")
def test_pose_hold_resets_on_capture_failure(mock_detector_create) -> None:
    """Counter phải reset về 0 khi capture thất bại (liveness/embedding fail)."""
    detector = MagicMock()
    detector.setInputSize.return_value = None
    mock_detector_create.return_value = detector

    head_pose = MagicMock()
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

    # Simulate capture failure
    thread._on_capture_complete(False, None, 0.0)

    assert thread._pose_hold_counter == 0
    assert thread._current_pose_index == 0
    assert thread._capture_in_progress is False


@patch("cv2.FaceDetectorYN.create")
def test_pose_hold_counter_capped_at_hold_frames(mock_detector_create) -> None:
    """Counter không được vượt quá _HOLD_FRAMES dù pose khớp nhiều frame liên tiếp."""
    detector = MagicMock()
    detector.setInputSize.return_value = None
    mock_detector_create.return_value = detector

    head_pose = MagicMock()
    liveness = MagicMock()
    recognizer = MagicMock()

    thread = EnrollmentCameraThread(
        camera_index=0,
        liveness_checker=liveness,
        face_recognizer=recognizer,
        head_pose_estimator=head_pose,
        detector_model_path=Path("fake.onnx"),
    )
    thread._current_pose_index = 0  # Target: (0, 0)

    for _ in range(20):
        thread._on_pose_estimated(0.0, 0.0, 0.0)

    assert thread._pose_hold_counter <= _HOLD_FRAMES


@patch("cv2.FaceDetectorYN.create")
def test_enrollment_succeeds_without_liveness(mock_detector_create) -> None:
    """Enrollment should succeed even when liveness would normally fail on angled poses."""
    detector = MagicMock()
    detector.setInputSize.return_value = None
    mock_detector_create.return_value = detector

    head_pose = MagicMock()
    liveness = MagicMock()
    recognizer = MagicMock()

    bypass_liveness = LivenessChecker(None)

    thread = EnrollmentCameraThread(
        camera_index=0,
        liveness_checker=bypass_liveness,
        face_recognizer=recognizer,
        head_pose_estimator=head_pose,
        detector_model_path=Path("fake.onnx"),
    )
    thread._current_pose_index = 1  # "Nghiêng phải"

    # Simulate capture completing successfully (liveness bypass means is_real=True always)
    emb = np.ones(128, dtype=np.float32)
    thread._on_capture_complete(True, emb, 1.0)

    # Should advance to next pose
    assert thread._current_pose_index == 2
    assert len(thread._captured_embeddings_by_pose) == 1


@patch("cv2.FaceDetectorYN.create")
def test_enrollment_liveness_bypass_still_checks_embedding(mock_detector_create) -> None:
    """With liveness bypass, embedding extraction still matters - if it fails, capture should fail."""
    detector = MagicMock()
    detector.setInputSize.return_value = None
    mock_detector_create.return_value = detector

    head_pose = MagicMock()
    liveness = MagicMock()
    bypass_liveness = LivenessChecker(None)
    recognizer = MagicMock()

    thread = EnrollmentCameraThread(
        camera_index=0,
        liveness_checker=bypass_liveness,
        face_recognizer=recognizer,
        head_pose_estimator=head_pose,
        detector_model_path=Path("fake.onnx"),
    )
    thread._current_pose_index = 0

    # Simulate capture failure (embedding extraction failed in worker)
    thread._on_capture_complete(False, None, 1.0)

    assert thread._current_pose_index == 0
    assert len(thread._captured_embeddings_by_pose) == 0


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
    """Enrollment should accept user turning right when asked to turn right (positive yaw)."""
    detector = MagicMock()
    detector.setInputSize.return_value = None
    mock_detector_create.return_value = detector

    head_pose = MagicMock()
    liveness = LivenessChecker(None)
    recognizer = MagicMock()

    thread = EnrollmentCameraThread(
        camera_index=0,
        liveness_checker=liveness,
        face_recognizer=recognizer,
        head_pose_estimator=head_pose,
        detector_model_path=Path("fake.onnx"),
    )
    thread._current_pose_index = 1  # "Nghiêng phải" (yaw=30)

    # Step 1: pose estimated with matching yaw (30)
    thread._on_pose_estimated(0.0, 30.0, 0.0)
    assert thread._pose_hold_counter == 1  # hold starts building

    # After enough hold frames, capture succeeds
    emb = np.ones(128, dtype=np.float32)
    thread._on_capture_complete(True, emb, 1.0)
    assert thread._current_pose_index == 2


@patch("cv2.FaceDetectorYN.create")
def test_enrollment_rejects_opposite_yaw_direction(mock_detector_create) -> None:
    """Enrollment should NOT accept user turning opposite to what system asks."""
    detector = MagicMock()
    detector.setInputSize.return_value = None
    mock_detector_create.return_value = detector

    head_pose = MagicMock()
    liveness = LivenessChecker(None)
    recognizer = MagicMock()

    thread = EnrollmentCameraThread(
        camera_index=0,
        liveness_checker=liveness,
        face_recognizer=recognizer,
        head_pose_estimator=head_pose,
        detector_model_path=Path("fake.onnx"),
    )
    thread._current_pose_index = 1  # "Nghiêng phải" requires yaw=30
    thread._pose_hold_counter = 4

    # Pose estimated with OPPOSITE yaw (-30, left turn instead of right)
    thread._on_pose_estimated(0.0, -30.0, 0.0)

    assert thread._current_pose_index == 1
    assert thread._pose_hold_counter == 0


@patch("cv2.FaceDetectorYN.create")
def test_mirrored_frame_flipped_before_processing(mock_detector_create) -> None:
    """Camera frame should be flipped horizontally so display is like a mirror."""
    import inspect

    source = inspect.getsource(EnrollmentCameraThread.run)
    # Verify that cv2.flip with axis=1 is called in the run method
    assert "cv2.flip(frame, 1)" in source or "flip(frame, 1)" in source
