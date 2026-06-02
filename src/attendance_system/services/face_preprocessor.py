"""Face preprocessing pipeline: crop -> resize -> normalize -> to_tensor.

This module extracts the per-model preprocessing logic that was previously
embedded in `LivenessChecker._preprocess` and `HeadPoseEstimator._preprocess`
into a single composable `FacePreprocessor` class. Behavior is controlled by
a frozen `PreprocessingConfig` dataclass, so adding a new model costs a new
config -- not a new preprocessing function.

Pipeline steps (applied in order):

    1. crop     -- optional, only when `bbox` is supplied. Square-padded crop
                   using `config.scale` via `utils.face_utils._crop_face`.
    2. color    -- convert BGR -> RGB if `config.input_color == "rgb"` and
                   the caller passed a BGR image.
    3. clahe    -- optional contrast-limited adaptive histogram equalization
                   on the Y (luminance) channel of YCrCb.
    4. resize   -- letterbox-resize (longest side -> target, reflect-pad
                   shorter side) OR direct resize, per `config.resize_mode`.
    5. normalize -- scale to [0, 1]; optionally apply ImageNet mean/std.
    6. to_tensor -- HWC uint8 -> CHW float32 with a leading batch dim.

The preprocessor is pure numpy/cv2 and depends on no ONNX sessions, so the
steps are unit-testable in isolation.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

import cv2
import numpy as np

# `_crop_face` is the established internal cropping primitive used by four
# callers (camera threads + AI workers). Kept private in `face_utils`; the
# preprocessor is the one place that composes it into a full pipeline.
from attendance_system.utils.face_utils import _crop_face

__all__ = [
    "FacePreprocessor",
    "PreprocessingConfig",
    "Normalize",
    "ResizeMode",
    "InputColor",
]


# --- Normalization strategy -------------------------------------------------

class Normalize:
    """Normalization strategy selector. Pass the string to `PreprocessingConfig`."""

    ZERO_ONE: Final[str] = "zero_one"     # divide by 255; output in [0, 1]
    IMAGENET: Final[str] = "imagenet"     # [0,1] then (x - mean) / std


# --- Resize strategy --------------------------------------------------------

class ResizeMode:
    """Resize strategy selector. Pass the string to `PreprocessingConfig`."""

    LETTERBOX: Final[str] = "letterbox"   # longest side -> target, reflect-pad
    DIRECT: Final[str] = "direct"         # cv2.resize straight to target (may distort)


# --- Input color order ------------------------------------------------------

class InputColor:
    """Input color-order selector. Pass the string to `PreprocessingConfig`."""

    RGB: Final[str] = "rgb"
    BGR: Final[str] = "bgr"


# ImageNet mean/std are public constants of the training pipeline that
# MobileNetV2 (head-pose) expects. Kept module-private; the preprocessor
# applies them when `config.normalize == Normalize.IMAGENET`.
_IMAGENET_MEAN: Final[np.ndarray] = np.array(
    [0.485, 0.456, 0.406], dtype=np.float32
)
_IMAGENET_STD: Final[np.ndarray] = np.array(
    [0.229, 0.224, 0.225], dtype=np.float32
)


@dataclass(frozen=True)
class PreprocessingConfig:
    """Frozen configuration describing one model's preprocessing pipeline.

    Attributes:
        scale: Crop scale factor forwarded to `_crop_face` when `bbox` is
            supplied. 2.7 for liveness (broad context), 1.5 for head-pose
            (tight crop). Ignored when the caller passes a pre-cropped face.
        target_size: Output spatial size as ``(H, W)``. The preprocessor
            produces a tensor of shape ``(1, 3, H, W)``.
        normalize: One of `Normalize.ZERO_ONE` (``"zero_one"``) or
            `Normalize.IMAGENET` (``"imagenet"``).
        use_clahe: When ``True``, apply CLAHE on the Y channel of YCrCb
            before resizing. Default ``False`` -- the MiniFASNet training
            pipeline does not include CLAHE, and Phase-1 testing confirmed
            CLAHE removal improved poor-light performance (see
            `CONTEXT.md` "Phase 3 Testing Results").
        input_color: ``"rgb"`` (default) or ``"bgr"``. BGR inputs are
            converted to RGB before downstream steps.
        resize_mode: ``"letterbox"`` (default, preserves aspect ratio via
            reflect-pad) or ``"direct"`` (straight `cv2.resize`, may
            distort). Liveness uses letterbox; head-pose currently uses
            direct.
    """

    scale: float
    target_size: tuple[int, int]
    normalize: str = Normalize.ZERO_ONE
    use_clahe: bool = False
    input_color: str = InputColor.RGB
    resize_mode: str = ResizeMode.LETTERBOX


class FacePreprocessor:
    """Composable face preprocessing pipeline.

    Instantiated with a `PreprocessingConfig` that fully describes the
    per-model behavior. The class is stateless and safe to share across
    threads -- it holds only a frozen dataclass reference.

    Example:
        >>> config = PreprocessingConfig(scale=2.7, target_size=(128, 128))
        >>> pre = FacePreprocessor(config)
        >>> tensor = pre(face_rgb_uint8)  # (1, 3, 128, 128) float32
    """

    def __init__(self, config: PreprocessingConfig) -> None:
        self._config = config

    @property
    def config(self) -> PreprocessingConfig:
        """The configuration this preprocessor was built with."""
        return self._config

    def __call__(
        self,
        face_crop: np.ndarray,
        bbox: tuple[int, int, int, int] | None = None,
    ) -> np.ndarray:
        """Run the preprocessing pipeline.

        Args:
            face_crop: ``H x W x 3`` uint8 image. Color order matches
                `config.input_color`.
            bbox: Optional ``(x, y, w, h)`` bounding box. When supplied,
                the crop step is applied first using `config.scale`.
                When ``None`` (default), the input is treated as an
                already-cropped face and step 1 is skipped.

        Returns:
            Preprocessed tensor with shape ``(1, 3, H, W)`` and dtype
            ``float32``. ``H`` and ``W`` come from `config.target_size`.

        Raises:
            ValueError: On invalid input shape, empty image, or unknown
                config string fields.
        """
        if face_crop.ndim != 3 or face_crop.shape[2] != 3:
            raise ValueError(
                f"face_crop must be an HxWx3 image, got shape {face_crop.shape!r}"
            )

        # Step 1: crop (optional). Existing callers pre-crop and pass bbox=None,
        # keeping the refactor surgically non-breaking.
        if bbox is not None:
            img = _crop_face(face_crop, bbox, scale=self._config.scale)
        else:
            img = face_crop

        if img.size == 0:
            raise ValueError("face_crop is empty (zero pixels)")

        # Step 2: color order
        if self._config.input_color == InputColor.BGR:
            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        elif self._config.input_color != InputColor.RGB:
            raise ValueError(
                f"Unknown input_color: {self._config.input_color!r}"
            )

        # Step 3: CLAHE (optional)
        if self._config.use_clahe:
            img = self._apply_clahe(img)

        # Step 4: resize
        if self._config.resize_mode == ResizeMode.LETTERBOX:
            img = self._letterbox_resize(img, self._config.target_size)
        elif self._config.resize_mode == ResizeMode.DIRECT:
            img = self._direct_resize(img, self._config.target_size)
        else:
            raise ValueError(
                f"Unknown resize_mode: {self._config.resize_mode!r}"
            )

        # Step 5+6: normalize + HWC uint8 -> CHW float32 with batch dim
        return self._to_tensor(img)

    # ------------------------------------------------------------------
    # Step helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _apply_clahe(rgb: np.ndarray) -> np.ndarray:
        """Apply CLAHE on the Y (luminance) channel of YCrCb.

        Operates on uint8 images; returns uint8. Chroma channels are
        untouched to avoid color shifts.
        """
        ycrcb = cv2.cvtColor(rgb, cv2.COLOR_RGB2YCrCb)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        ycrcb[..., 0] = clahe.apply(ycrcb[..., 0])
        return cv2.cvtColor(ycrcb, cv2.COLOR_YCrCb2RGB)

    @staticmethod
    def _letterbox_resize(
        rgb: np.ndarray, target_size: tuple[int, int]
    ) -> np.ndarray:
        """Resize longest side to ``target_h``, reflect-pad shorter side.

        Matches the legacy `LivenessChecker._preprocess` algorithm:
        uses `int()` truncation (not `round()`) and selects the
        interpolation mode by upscale vs. downscale direction.
        """
        target_h, target_w = target_size
        old_h, old_w = rgb.shape[:2]
        ratio = float(target_h) / max(old_h, old_w)
        new_h = int(old_h * ratio)
        new_w = int(old_w * ratio)
        interp = cv2.INTER_LANCZOS4 if ratio > 1.0 else cv2.INTER_AREA
        resized = cv2.resize(
            rgb, (new_w, new_h), interpolation=interp
        )
        delta_h = target_h - new_h
        delta_w = target_w - new_w
        top, bottom = delta_h // 2, delta_h - (delta_h // 2)
        left, right = delta_w // 2, delta_w - (delta_w // 2)
        # BORDER_REFLECT_101 avoids hard edge artifacts at the pad boundary.
        return cv2.copyMakeBorder(
            resized, top, bottom, left, right, cv2.BORDER_REFLECT_101
        )

    @staticmethod
    def _direct_resize(
        rgb: np.ndarray, target_size: tuple[int, int]
    ) -> np.ndarray:
        """Resize straight to ``(target_h, target_w)`` (may distort AR)."""
        return cv2.resize(rgb, (target_size[1], target_size[0]),
                          interpolation=cv2.INTER_LINEAR)

    def _to_tensor(self, rgb: np.ndarray) -> np.ndarray:
        """Normalize to float32, transpose HWC -> CHW, add batch dim.

        Casts to float32 BEFORE dividing by 255 to match the legacy
        pipeline's numeric behavior. ImageNet normalization happens on
        the HWC array; transpose is applied last (mathematically
        equivalent to either order).
        """
        normalized = rgb.astype(np.float32) / 255.0
        if self._config.normalize == Normalize.IMAGENET:
            normalized = (normalized - _IMAGENET_MEAN) / _IMAGENET_STD
        elif self._config.normalize != Normalize.ZERO_ONE:
            raise ValueError(
                f"Unknown normalize: {self._config.normalize!r}"
            )
        return normalized.transpose(2, 0, 1)[np.newaxis]
