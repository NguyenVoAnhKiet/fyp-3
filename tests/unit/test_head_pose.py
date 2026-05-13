from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from attendance_system.services.head_pose import HeadPoseEstimator


@patch("onnxruntime.InferenceSession")
def test_head_pose_preprocess_and_estimate_identity(mock_session_cls) -> None:
    mock_session = MagicMock()
    mock_input = MagicMock()
    mock_input.name = "input"
    mock_session.get_inputs.return_value = [mock_input]
    mock_session.run.return_value = [np.array([np.eye(3, dtype=np.float32)])]
    mock_session_cls.return_value = mock_session

    estimator = HeadPoseEstimator(Path("fake.onnx"))
    crop = np.zeros((40, 60, 3), dtype=np.uint8)

    tensor = estimator._preprocess(crop)
    assert tensor.shape == (1, 3, 224, 224)
    assert tensor.dtype == np.float32

    pitch, yaw, roll = estimator.estimate(crop)
    assert pitch == pytest.approx(0.0)
    assert yaw == pytest.approx(0.0)
    assert roll == pytest.approx(0.0)


@patch("onnxruntime.InferenceSession")
def test_head_pose_estimate_converts_rotation_matrix(mock_session_cls) -> None:
    mock_session = MagicMock()
    mock_input = MagicMock()
    mock_input.name = "input"
    mock_session.get_inputs.return_value = [mock_input]
    rotation = np.array(
        [
            [0.8660254, -0.5, 0.0],
            [0.5, 0.8660254, 0.0],
            [0.0, 0.0, 1.0],
        ],
        dtype=np.float32,
    )
    mock_session.run.return_value = [rotation[np.newaxis, ...]]
    mock_session_cls.return_value = mock_session

    estimator = HeadPoseEstimator(Path("fake.onnx"))
    crop = np.zeros((32, 32, 3), dtype=np.uint8)

    pitch, yaw, roll = estimator.estimate(crop)
    assert pitch == pytest.approx(0.0, abs=1e-4)
    assert yaw == pytest.approx(0.0, abs=1e-4)
    assert roll == pytest.approx(30.0, abs=1e-3)
