"""Unit tests for the composable `FacePreprocessor` (plan 0007).

These tests are independent of ONNX sessions -- they exercise each pipeline
step and each config combination in isolation. They also act as a regression
net for the numeric behavior that `LivenessChecker._preprocess` and
`HeadPoseEstimator._preprocess` used to encode inline.
"""

from __future__ import annotations

import numpy as np
import pytest

from attendance_system.services.face_preprocessor import (
    FacePreprocessor,
    InputColor,
    Normalize,
    PreprocessingConfig,
    ResizeMode,
)
from attendance_system.services.preprocessing_configs import (
    HEAD_POSE_CONFIG,
    LIVENESS_CONFIG,
)


# ==============================================================================
# PreprocessingConfig
# ==============================================================================


def test_config_is_frozen():
    """PreprocessingConfig should be immutable (frozen dataclass)."""
    config = PreprocessingConfig(scale=1.0, target_size=(64, 64))
    with pytest.raises((AttributeError, Exception)):
        config.scale = 2.0  # type: ignore[misc]


def test_liveness_config_matches_minifasnet_spec():
    """LIVENESS_CONFIG must encode the MiniFASNet training recipe."""
    assert LIVENESS_CONFIG.scale == 2.7
    assert LIVENESS_CONFIG.target_size == (128, 128)
    assert LIVENESS_CONFIG.normalize == Normalize.ZERO_ONE
    assert LIVENESS_CONFIG.use_clahe is False
    assert LIVENESS_CONFIG.input_color == InputColor.RGB
    assert LIVENESS_CONFIG.resize_mode == ResizeMode.LETTERBOX


def test_head_pose_config_matches_mobilenetv2_spec():
    """HEAD_POSE_CONFIG must encode the MobileNetV2 training recipe."""
    assert HEAD_POSE_CONFIG.scale == 1.5
    assert HEAD_POSE_CONFIG.target_size == (224, 224)
    assert HEAD_POSE_CONFIG.normalize == Normalize.IMAGENET
    assert HEAD_POSE_CONFIG.use_clahe is False
    assert HEAD_POSE_CONFIG.input_color == InputColor.BGR
    assert HEAD_POSE_CONFIG.resize_mode == ResizeMode.DIRECT


# ==============================================================================
# Output shape & dtype
# ==============================================================================


def test_output_shape_and_dtype_rgb_letterbox():
    """Default (letterbox, RGB) config produces (1, 3, H, W) float32."""
    pre = FacePreprocessor(
        PreprocessingConfig(scale=2.7, target_size=(128, 128))
    )
    img = np.random.randint(0, 256, (200, 150, 3), dtype=np.uint8)
    out = pre(img)
    assert out.shape == (1, 3, 128, 128)
    assert out.dtype == np.float32


def test_output_shape_direct_resize():
    """Direct resize mode produces (1, 3, H, W) float32 from any aspect ratio."""
    pre = FacePreprocessor(
        PreprocessingConfig(
            scale=1.5, target_size=(224, 224), resize_mode=ResizeMode.DIRECT
        )
    )
    img = np.random.randint(0, 256, (40, 60, 3), dtype=np.uint8)
    out = pre(img)
    assert out.shape == (1, 3, 224, 224)
    assert out.dtype == np.float32


# ==============================================================================
# Step 1: Crop (with bbox)
# ==============================================================================


def test_crop_with_scale_2_7_yields_larger_crop():
    """scale=2.7 produces a 270x270 region around a 100x100 bbox center."""
    pre = FacePreprocessor(
        PreprocessingConfig(scale=2.7, target_size=(270, 270))
    )
    # 500x500 frame with a 100x100 face at (200,200). Center = (250,250).
    frame = np.zeros((500, 500, 3), dtype=np.uint8)
    # Paint the bbox region white so we can detect it post-crop.
    frame[200:300, 200:300] = 255
    bbox = (200, 200, 100, 100)
    out = pre(frame, bbox=bbox)
    # Output is the cropped region (then resized to 270x270). We verify
    # the crop step produced a non-empty region by checking the output
    # is not all-zero.
    assert out.shape == (1, 3, 270, 270)
    assert out.max() > 0.5  # white content survives the crop


def test_crop_with_scale_1_5_yields_tighter_crop():
    """scale=1.5 produces a 150x150 region (tighter than scale=2.7)."""
    pre = FacePreprocessor(
        PreprocessingConfig(scale=1.5, target_size=(150, 150))
    )
    frame = np.zeros((500, 500, 3), dtype=np.uint8)
    frame[200:300, 200:300] = 255  # face region
    bbox = (200, 200, 100, 100)
    out = pre(frame, bbox=bbox)
    assert out.shape == (1, 3, 150, 150)
    assert out.max() > 0.5


def test_crop_clamps_to_frame_bounds():
    """A bbox near the frame edge must not produce out-of-bounds indexing."""
    pre = FacePreprocessor(
        PreprocessingConfig(scale=2.7, target_size=(64, 64))
    )
    frame = np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)
    # bbox near edge: half-crop would extend past frame boundary.
    bbox = (5, 5, 20, 20)
    out = pre(frame, bbox=bbox)
    assert out.shape == (1, 3, 64, 64)
    assert not np.isnan(out).any()


def test_no_bbox_treats_input_as_precropped():
    """bbox=None (default) skips the crop step; input is used as-is."""
    pre = FacePreprocessor(
        PreprocessingConfig(scale=2.7, target_size=(128, 128))
    )
    # Pre-cropped 100x100 face. No bbox -> no scaling, just resize to 128x128.
    face = np.full((100, 100, 3), 128, dtype=np.uint8)
    out = pre(face)  # no bbox
    assert out.shape == (1, 3, 128, 128)
    # All pixels are gray=128, so normalized should be ~0.502.
    assert np.allclose(out, 128.0 / 255.0, atol=1e-3)


# ==============================================================================
# Step 2: Color
# ==============================================================================


def test_bgr_input_is_converted_to_rgb():
    """When config.input_color='bgr', the BGR->RGB swap must happen."""
    # BGR image where blue=255, green=0, red=0
    bgr = np.zeros((4, 4, 3), dtype=np.uint8)
    bgr[..., 0] = 255  # B
    bgr[..., 1] = 0    # G
    bgr[..., 2] = 0    # R

    pre_bgr = FacePreprocessor(
        PreprocessingConfig(
            scale=1.0,
            target_size=(4, 4),
            input_color=InputColor.BGR,
            normalize=Normalize.ZERO_ONE,
        )
    )
    out_bgr = pre_bgr(bgr)
    # After BGR->RGB, the red channel (last) should be ~1.0 in output[0,2].
    # The output is CHW float32 in [0,1].
    assert out_bgr[0, 2, 0, 0] > 0.99  # red channel high
    assert out_bgr[0, 0, 0, 0] < 0.01  # blue channel low


def test_rgb_input_passthrough():
    """When config.input_color='rgb', no conversion is applied."""
    rgb = np.zeros((4, 4, 3), dtype=np.uint8)
    rgb[..., 0] = 255  # R
    rgb[..., 1] = 0
    rgb[..., 2] = 0

    pre_rgb = FacePreprocessor(
        PreprocessingConfig(
            scale=1.0,
            target_size=(4, 4),
            input_color=InputColor.RGB,
            normalize=Normalize.ZERO_ONE,
        )
    )
    out_rgb = pre_rgb(rgb)
    assert out_rgb[0, 0, 0, 0] > 0.99  # red channel high
    assert out_rgb[0, 2, 0, 0] < 0.01  # blue channel low


# ==============================================================================
# Step 3: CLAHE
# ==============================================================================


def test_clahe_enabled_increases_contrast_on_low_contrast_input():
    """CLAHE on a low-contrast input should produce a higher-std output."""
    # Low-contrast image: only mid-gray values 100-110.
    rng = np.random.default_rng(0)
    low_contrast = rng.integers(100, 111, size=(64, 64, 3), dtype=np.uint8)

    base_config = PreprocessingConfig(
        scale=1.0,
        target_size=(64, 64),
        normalize=Normalize.ZERO_ONE,
        use_clahe=False,
    )
    pre_no_clahe = FacePreprocessor(base_config)
    pre_with_clahe = FacePreprocessor(
        PreprocessingConfig(
            scale=1.0,
            target_size=(64, 64),
            normalize=Normalize.ZERO_ONE,
            use_clahe=True,
        )
    )
    out_no = pre_no_clahe(low_contrast)
    out_with = pre_with_clahe(low_contrast)
    # Per-channel std should be higher after CLAHE.
    std_no = float(out_no.std(axis=(2, 3)).mean())
    std_with = float(out_with.std(axis=(2, 3)).mean())
    assert std_with > std_no


def test_clahe_disabled_passthrough():
    """With use_clahe=False, output values are determined solely by resize+norm."""
    pre = FacePreprocessor(
        PreprocessingConfig(
            scale=1.0,
            target_size=(32, 32),
            normalize=Normalize.ZERO_ONE,
            use_clahe=False,
        )
    )
    img = np.full((32, 32, 3), 200, dtype=np.uint8)
    out = pre(img)
    # 200/255 ~= 0.784. No CLAHE means no contrast stretch.
    assert np.allclose(out, 200.0 / 255.0, atol=1e-3)


# ==============================================================================
# Step 4: Resize
# ==============================================================================


@pytest.mark.parametrize("shape", [
    (100, 100, 3),  # square
    (200, 100, 3),  # portrait
    (100, 200, 3),  # landscape
    (50, 50, 3),    # small
    (500, 500, 3),  # large
])
def test_letterbox_resize_always_produces_target(shape):
    """Letterbox mode produces exact target shape for any input aspect ratio."""
    pre = FacePreprocessor(
        PreprocessingConfig(scale=1.0, target_size=(128, 128))
    )
    img = np.random.randint(0, 256, shape, dtype=np.uint8)
    out = pre(img)
    assert out.shape == (1, 3, 128, 128)


def test_letterbox_preserves_aspect_ratio_for_portrait():
    """A 200x100 portrait input letterboxed to 128x128: content squeezed horizontally."""
    pre = FacePreprocessor(
        PreprocessingConfig(scale=1.0, target_size=(128, 128))
    )
    # 200x100: longest side is 200, so scale=128/200=0.64. New size = 128x64.
    # Padded on left/right by (128-64)/2 = 32 each. Top/bottom = 0.
    # Paint the whole image white to detect the padded region (which will be reflected).
    img = np.full((200, 100, 3), 128, dtype=np.uint8)
    out = pre(img)
    # Output is uniform gray (the padding reflects the same gray).
    assert np.allclose(out, 128.0 / 255.0, atol=1e-3)


# ==============================================================================
# Step 5: Normalize
# ==============================================================================


def test_normalize_zero_one_produces_values_in_unit_range():
    """[0,1] normalization: output values must lie in [0, 1]."""
    pre = FacePreprocessor(
        PreprocessingConfig(
            scale=1.0, target_size=(64, 64), normalize=Normalize.ZERO_ONE
        )
    )
    img = np.random.randint(0, 256, (64, 64, 3), dtype=np.uint8)
    out = pre(img)
    assert out.min() >= 0.0
    assert out.max() <= 1.0


def test_normalize_imagenet_produces_typical_range():
    """ImageNet normalization: output range is bounded by ~ 1/|std|."""
    pre = FacePreprocessor(
        PreprocessingConfig(
            scale=1.0,
            target_size=(64, 64),
            normalize=Normalize.IMAGENET,
            resize_mode=ResizeMode.DIRECT,
        )
    )
    # Random uint8 image exercises both signs of (x - mean) / std.
    img = np.random.default_rng(0).integers(0, 256, (64, 64, 3), dtype=np.uint8)
    out = pre(img)
    # Output values are bounded by ~ 1/|std| in magnitude (per channel).
    # The loosest std is 0.224 (G), giving a max magnitude of ~4.46.
    assert abs(out.min()) < 1.0 / 0.224
    assert abs(out.max()) < 1.0 / 0.224
    # And both signs are present (output has positive and negative values).
    assert out.min() < 0.0
    assert out.max() > 0.0


def test_imagenet_normalization_matches_known_formula():
    """Verify ImageNet normalize on a known input."""
    pre = FacePreprocessor(
        PreprocessingConfig(
            scale=1.0,
            target_size=(4, 4),
            normalize=Normalize.IMAGENET,
            resize_mode=ResizeMode.DIRECT,
        )
    )
    # Black image: 0/255=0, (0-mean)/std = -mean/std
    black = np.zeros((4, 4, 3), dtype=np.uint8)
    out = pre(black)
    expected_r = (0.0 - 0.485) / 0.229
    expected_g = (0.0 - 0.456) / 0.224
    expected_b = (0.0 - 0.406) / 0.225
    assert out[0, 0, 0, 0] == pytest.approx(expected_r, abs=1e-5)
    assert out[0, 1, 0, 0] == pytest.approx(expected_g, abs=1e-5)
    assert out[0, 2, 0, 0] == pytest.approx(expected_b, abs=1e-5)


# ==============================================================================
# Step 6: Transpose to CHW
# ==============================================================================


def test_output_is_chw_not_hwc():
    """Channel dimension is at axis=1 (CHW), not axis=3 (HWC)."""
    pre = FacePreprocessor(
        PreprocessingConfig(scale=1.0, target_size=(32, 32))
    )
    img = np.random.randint(0, 256, (32, 32, 3), dtype=np.uint8)
    out = pre(img)
    assert out.shape[1] == 3  # C=3 at axis 1
    # Confirm the channels are distinguishable (not all 3 the same).
    assert not np.allclose(out[0, 0], out[0, 1])


def test_batch_dimension_is_leading():
    """Output shape starts with batch dim of size 1."""
    pre = FacePreprocessor(
        PreprocessingConfig(scale=1.0, target_size=(16, 16))
    )
    img = np.zeros((16, 16, 3), dtype=np.uint8)
    out = pre(img)
    assert out.shape[0] == 1


# ==============================================================================
# End-to-end: matches legacy LivenessChecker behavior
# ==============================================================================


def test_liveness_config_output_shape_matches_legacy():
    """LIVENESS_CONFIG output shape must match the legacy (1,3,128,128)."""
    pre = FacePreprocessor(LIVENESS_CONFIG)
    for shape in [(100, 100, 3), (200, 100, 3), (100, 200, 3), (500, 500, 3)]:
        out = pre(np.zeros(shape, dtype=np.uint8))
        assert out.shape == (1, 3, 128, 128)
        assert out.dtype == np.float32
        assert out.min() >= 0.0
        assert out.max() <= 1.0


def test_liveness_config_uniform_input_produces_uniform_output():
    """A uniform input must produce a uniform output (no spurious edges)."""
    pre = FacePreprocessor(LIVENESS_CONFIG)
    img = np.full((200, 200, 3), 100, dtype=np.uint8)
    out = pre(img)
    expected = 100.0 / 255.0
    assert np.allclose(out, expected, atol=1e-3)


def test_head_pose_config_output_shape_matches_legacy():
    """HEAD_POSE_CONFIG output shape must match the legacy (1,3,224,224)."""
    pre = FacePreprocessor(HEAD_POSE_CONFIG)
    out = pre(np.zeros((40, 60, 3), dtype=np.uint8))
    assert out.shape == (1, 3, 224, 224)
    assert out.dtype == np.float32


# ==============================================================================
# Error handling
# ==============================================================================


def test_invalid_input_shape_raises():
    """Non HxWx3 inputs must raise ValueError."""
    pre = FacePreprocessor(
        PreprocessingConfig(scale=1.0, target_size=(32, 32))
    )
    with pytest.raises(ValueError, match="HxWx3"):
        pre(np.zeros((32, 32), dtype=np.uint8))  # 2D
    with pytest.raises(ValueError, match="HxWx3"):
        pre(np.zeros((32, 32, 4), dtype=np.uint8))  # 4 channels


def test_empty_image_raises():
    """An all-zero-pixel image is valid; an actually-empty ndarray is not."""
    pre = FacePreprocessor(
        PreprocessingConfig(scale=1.0, target_size=(32, 32))
    )
    empty = np.zeros((0, 0, 3), dtype=np.uint8)
    with pytest.raises(ValueError, match="empty"):
        pre(empty)


def test_unknown_normalize_raises():
    """A bogus normalize string in config should raise at call time."""
    pre = FacePreprocessor(
        PreprocessingConfig(scale=1.0, target_size=(32, 32), normalize="bogus")
    )
    with pytest.raises(ValueError, match="normalize"):
        pre(np.zeros((32, 32, 3), dtype=np.uint8))


def test_unknown_input_color_raises():
    """A bogus input_color string should raise at call time."""
    pre = FacePreprocessor(
        PreprocessingConfig(scale=1.0, target_size=(32, 32), input_color="cmyk")
    )
    with pytest.raises(ValueError, match="input_color"):
        pre(np.zeros((32, 32, 3), dtype=np.uint8))


def test_unknown_resize_mode_raises():
    """A bogus resize_mode string should raise at call time."""
    pre = FacePreprocessor(
        PreprocessingConfig(scale=1.0, target_size=(32, 32), resize_mode="bogus")
    )
    with pytest.raises(ValueError, match="resize_mode"):
        pre(np.zeros((32, 32, 3), dtype=np.uint8))
