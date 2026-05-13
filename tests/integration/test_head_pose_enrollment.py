from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import cv2
import numpy as np

from attendance_system.ui.enrollment_camera_thread import EnrollmentCameraThread


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
