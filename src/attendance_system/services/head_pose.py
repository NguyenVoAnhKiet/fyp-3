from __future__ import annotations

import math
from pathlib import Path
from typing import NamedTuple

import numpy as np
import onnxruntime as ort

from attendance_system.services.exceptions import PoseInferenceError
from attendance_system.services.face_preprocessor import FacePreprocessor
from attendance_system.services.preprocessing_configs import HEAD_POSE_CONFIG

__all__ = ["HeadPoseEstimator", "PoseAngles"]


class PoseAngles(NamedTuple):
    pitch: float
    yaw: float
    roll: float


class HeadPoseEstimator:
    """Estimate head pose from a cropped face using an ONNX model."""

    def __init__(self, model_path: Path | str) -> None:
        self._model_path = Path(model_path)
        self._session = ort.InferenceSession(str(self._model_path))

        inputs = self._session.get_inputs()
        if not inputs:
            raise RuntimeError("Head pose model does not expose any inputs")
        self._input_name = inputs[0].name

        # Composable preprocessing pipeline (extracted as part of plan 0007).
        # Owns BGR->RGB, direct resize, ImageNet normalize, to_tensor.
        self._preprocessor = FacePreprocessor(HEAD_POSE_CONFIG)

    def estimate(self, face_crop_bgr: np.ndarray) -> tuple[float, float, float]:
        """Return pitch, yaw, and roll in degrees for a BGR face crop."""
        tensor = self._preprocess(face_crop_bgr)
        try:
            raw_output = self._session.run(None, {self._input_name: tensor})[0]
        except Exception as exc:
            raise PoseInferenceError(
                f"Head pose inference failed: {exc}",
                input_shape=tensor.shape,
                model_path=str(self._model_path),
            ) from exc
        rotation_matrix = self._rotation_matrix(raw_output)
        return self._matrix_to_euler(rotation_matrix)

    def _preprocess(
        self,
        face_crop_bgr: np.ndarray,
        bbox: tuple[int, int, int, int] | None = None,
    ) -> np.ndarray:
        """Preprocess a BGR face crop into the head-pose input tensor.

        Delegates to the shared `FacePreprocessor` (plan 0007). The
        optional `bbox` argument enables the crop step; existing
        callers pre-crop with `_crop_face` and pass ``bbox=None``,
        so behavior is unchanged.

        Returns:
            float32 tensor of shape ``(1, 3, 224, 224)``, ImageNet-normalized.
        """
        if face_crop_bgr.size == 0:
            raise ValueError("face_crop_bgr is empty")
        return self._preprocessor(face_crop_bgr, bbox)

    @staticmethod
    def _rotation_matrix(raw_output: np.ndarray) -> np.ndarray:
        matrix = np.asarray(raw_output, dtype=np.float32)
        if matrix.ndim == 3 and matrix.shape[0] == 1:
            matrix = matrix[0]
        if matrix.shape == (3, 3):
            return matrix
        if matrix.size == 9:
            return matrix.reshape(3, 3)
        raise ValueError(f"Unexpected head pose output shape: {matrix.shape}")

    @staticmethod
    def _matrix_to_euler(rotation_matrix: np.ndarray) -> tuple[float, float, float]:
        if rotation_matrix.shape != (3, 3):
            raise ValueError("rotation_matrix must be 3x3")

        r = rotation_matrix
        pitch = math.degrees(math.atan2(r[2, 1], r[2, 2]))
        yaw = math.degrees(
            math.atan2(-r[2, 0], math.sqrt(r[2, 1] ** 2 + r[2, 2] ** 2))
        )
        roll = math.degrees(math.atan2(r[1, 0], r[0, 0]))
        return (pitch, yaw, roll)
