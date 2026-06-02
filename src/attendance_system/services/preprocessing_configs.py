"""Preprocessing configurations for the AI pipeline models.

Each constant is a frozen `PreprocessingConfig` capturing the full
preprocessing recipe for one ONNX model:

- `LIVENESS_CONFIG`  -- MiniFASNet (anti-spoof), 128x128, [0,1], letterbox.
- `HEAD_POSE_CONFIG` -- MobileNetV2 (head-pose), 224x224, ImageNet, direct.

A new model is added by defining a new constant here -- not by editing
`LivenessChecker` or `HeadPoseEstimator`.
"""

from __future__ import annotations

from attendance_system.services.face_preprocessor import (
    InputColor,
    Normalize,
    PreprocessingConfig,
    ResizeMode,
)

__all__ = ["LIVENESS_CONFIG", "HEAD_POSE_CONFIG"]


# Matches the legacy `LivenessChecker._preprocess` (MiniFASNet training
# pipeline): scale=2.7, letterbox to 128x128, [0,1] range, no CLAHE,
# no ImageNet normalization.
LIVENESS_CONFIG = PreprocessingConfig(
    scale=2.7,
    target_size=(128, 128),
    normalize=Normalize.ZERO_ONE,
    use_clahe=False,
    input_color=InputColor.RGB,
    resize_mode=ResizeMode.LETTERBOX,
)


# Matches the legacy `HeadPoseEstimator._preprocess` (MobileNetV2 training
# pipeline): tight crop, direct resize to 224x224 (aspect ratio distorted
# to match training), ImageNet mean/std normalization, BGR input.
HEAD_POSE_CONFIG = PreprocessingConfig(
    scale=1.5,
    target_size=(224, 224),
    normalize=Normalize.IMAGENET,
    use_clahe=False,
    input_color=InputColor.BGR,
    resize_mode=ResizeMode.DIRECT,
)
