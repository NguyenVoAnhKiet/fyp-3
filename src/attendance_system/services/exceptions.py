"""ONNX inference exceptions for graceful degradation."""

from __future__ import annotations

__all__ = ["ONNXInferenceError", "PoseInferenceError", "LivenessInferenceError"]


class ONNXInferenceError(Exception):
    """Base exception for ONNX inference failures in attendance services.

    Carries optional context for logging: input tensor shape and model path.
    """

    def __init__(
        self,
        message: str,
        input_shape: tuple[int, ...] | None = None,
        model_path: str | None = None,
    ) -> None:
        self.input_shape = input_shape
        self.model_path = model_path
        super().__init__(message)


class PoseInferenceError(ONNXInferenceError):
    """Head-pose estimation ONNX inference failed."""


class LivenessInferenceError(ONNXInferenceError):
    """Liveness detection ONNX inference failed."""
