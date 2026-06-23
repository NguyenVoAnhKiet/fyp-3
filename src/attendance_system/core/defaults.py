"""Default values for all system tunables.

Single source of truth — referenced by ``SystemConfig`` field defaults and
``SettingsResolver`` when no CLI / env / DB value is set.  Centralizing
defaults here makes the previous 0.5→0.3 style migrations a one-file change
instead of touching 4+ call sites.

``.env.example`` is documentation only; this module is the executable source
of truth.  Update both in lockstep when adding a new tunable.
"""

from __future__ import annotations

from pathlib import Path

# ---------------------------------------------------------------------------
# AI thresholds (per-face decision cutoffs)
# ---------------------------------------------------------------------------

#: Cosine-similarity threshold for face recognition match (0–1).
#: SFace embeddings are L2-normalised; 0.6 is a permissive default.
DEFAULT_SIMILARITY_THRESHOLD: float = 0.6

# ---------------------------------------------------------------------------
# Hybrid liveness decider
# ---------------------------------------------------------------------------

#: Liveness confidence threshold (0–1) in probability space.
#: Updated from 0.3 (logit space) to 0.5 (probability space) for plan 0009.
DEFAULT_LIVENESS_THRESHOLD: float = 0.5

#: Number of frames in the voting window for HybridLivenessDecider.
DEFAULT_HYBRID_VOTING_WINDOW: int = 5

#: Additive boost to liveness probability when recognition matches.
DEFAULT_HYBRID_BOOST_AMOUNT: float = 0.10

#: Whether the new hybrid liveness decider is enabled (feature flag).
#: When False, uses the legacy liveness path.
DEFAULT_HYBRID_LIVENESS_ENABLED: bool = True

#: Number of AI-frames between recognition runs in hybrid mode.
#: At _AI_FRAME_SKIP=3 and interval=5, recognition runs ~every 15 camera
#: frames ≈ 2 Hz at 30 fps.
DEFAULT_RECOGNITION_INTERVAL: int = 5

# ---------------------------------------------------------------------------
# Camera
# ---------------------------------------------------------------------------

#: OpenCV camera device index.  ``CAMERA_INDEX=`` (empty string) in ``.env``
#: is treated as missing and falls back to this default — see
#: ``_resolve_camera_index`` in the resolver.
DEFAULT_CAMERA_INDEX: int = 0

# ---------------------------------------------------------------------------
# Attendance UX (post-recognition freeze)
# ---------------------------------------------------------------------------

#: Duration of the success-overlay freeze in seconds.  ``0`` disables the
#: feature entirely (no overlay, no sound, no camera pause).
DEFAULT_ATTENDANCE_FREEZE_SECONDS: int = 4

#: Whether the platform-default beep plays when the freeze starts.
DEFAULT_ATTENDANCE_FREEZE_SOUND_ENABLED: bool = False

# ---------------------------------------------------------------------------
# AI model file paths (relative to project root)
# ---------------------------------------------------------------------------

DEFAULT_DATABASE_PATH: Path = Path("attendance.db")

DEFAULT_RECOGNITION_MODEL_PATH: Path = Path(
    "models/face_recognition/face_recognition_sface_2021dec.onnx"
)
DEFAULT_DETECTOR_MODEL_PATH: Path = Path(
    "models/face_detection/face_detection_yunet_2023mar.onnx"
)
DEFAULT_LIVENESS_MODEL_PATH: Path = Path("models/anti_spoof/best_model_quantized.onnx")
DEFAULT_HEADPOSE_MODEL_PATH: Path = Path("models/head_pose/mobilenetv2.onnx")

# ---------------------------------------------------------------------------
# Feature flags
# ---------------------------------------------------------------------------

#: Whether the MiniFASNet liveness model is loaded at all.  When ``False``,
#: every face is treated as real (bypass mode for performance or when the
#: model is not deployed).
DEFAULT_ANTISPOOF_ENABLED: bool = True

#: Whether the MobileNetV2 head-pose estimator is loaded for enrollment.
DEFAULT_HEADPOSE_ENABLED: bool = True

# ---------------------------------------------------------------------------
# Timezone
# ---------------------------------------------------------------------------

#: IANA timezone name used when no env/DB value is set.
DEFAULT_TIMEZONE: str = "Asia/Ho_Chi_Minh"
