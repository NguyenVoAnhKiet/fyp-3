from __future__ import annotations

import math
from pathlib import Path
from typing import Final, NamedTuple

import cv2
import numpy as np
import onnxruntime as ort

__all__ = ["HeadPoseEstimator", "PoseAngles"]

_INPUT_SIZE: Final[tuple[int, int]] = (224, 224)
_IMAGENET_MEAN: Final[np.ndarray] = np.array(
    [0.485, 0.456, 0.406], dtype=np.float32
)
_IMAGENET_STD: Final[np.ndarray] = np.array(
    [0.229, 0.224, 0.225], dtype=np.float32
)


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

    def estimate(self, face_crop_bgr: np.ndarray) -> tuple[float, float, float]:
        """Return pitch, yaw, and roll in degrees for a BGR face crop."""
        tensor = self._preprocess(face_crop_bgr)
        raw_output = self._session.run(None, {self._input_name: tensor})[0]
        rotation_matrix = self._rotation_matrix(raw_output)
        return self._matrix_to_euler(rotation_matrix)

    def _preprocess(self, face_crop_bgr: np.ndarray) -> np.ndarray:
        if face_crop_bgr.size == 0:
            raise ValueError("face_crop_bgr is empty")
        if face_crop_bgr.ndim != 3 or face_crop_bgr.shape[2] != 3:
            raise ValueError("face_crop_bgr must be an HxWx3 BGR image")

        face_rgb = cv2.cvtColor(face_crop_bgr, cv2.COLOR_BGR2RGB)
        resized = cv2.resize(face_rgb, _INPUT_SIZE, interpolation=cv2.INTER_LINEAR)
        normalized = resized.astype(np.float32) / 255.0
        normalized = (normalized - _IMAGENET_MEAN) / _IMAGENET_STD
        chw = np.transpose(normalized, (2, 0, 1))
        return chw[np.newaxis, ...]

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
