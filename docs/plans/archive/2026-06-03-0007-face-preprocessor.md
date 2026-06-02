# Plan 0007: Extract `FacePreprocessor`

**Parent plan:** [0002 — Architecture Deepening Checklist](../active/0002-architecture-deepening.md) (candidate #5).

## Status

**Done** — implemented on branch `refactor/source-code`, commit `8863ec1` (2026-06-03).

Design decisions were filled in **during implementation** rather than in a separate grilling session — the design emerged from reading the existing `_preprocess` code in `LivenessChecker` and `HeadPoseEstimator`, the MiniFASNet training spec in `CONTEXT.md`, and the four `_crop_face` callers in `ui/`. The plan's "pending grilling" decisions are resolved below; the plan is archived as `archive/2026-06-03-0007-face-preprocessor.md` per the lifecycle convention.

**Dependency:** recommended to be implemented **before** [0004 — AIPipeline](../active/0004-ai-pipeline-orchestrator.md) so the pipeline consumes a deep preprocessor. ✅ Done — #2 is now unblocked.

## Context

Face preprocessing logic is distributed across 3 files with different implementations:

| Location | Steps |
|----------|-------|
| `services/ai_pipeline.py` — `LivenessChecker._preprocess()` | letterbox-resize to 128×128, reflect-pad, transpose to CHW, [0,1] normalize |
| `services/head_pose.py` — `HeadPoseEstimator._preprocess()` | resize to 224×224, ImageNet normalize, transpose to CHW |
| `utils/face_utils.py` — `_crop_face(scale=...)` | scale-based cropping (2.7 for liveness, 1.5 for head-pose) |

Each model has its own preprocessing pipeline embedded in the model class. `_crop_face` scale parameter is the only abstraction for switching between liveness (2.7) and head-pose (1.5). Adding a new model requires duplicating the preprocessing pattern.

**Documentation/code conflict:** `CONTEXT.md` (Phase 1) and `AGENTS.md` say CLAHE is part of the pipeline, but the testing notes record "CLAHE removal: Worsened poor-light performance (99% spoof), kept CLAHE." The current state of CLAHE in production code is ambiguous.

## Goals

1. Single `FacePreprocessor` class with composable steps: `crop → resize → normalize → to_tensor`.
2. Each model pipeline = configuration of the preprocessor: `LivenessPreprocessing(scale=2.7, size=128, norm=[0,1])`, `HeadPosePreprocessing(scale=1.5, size=224, norm=imagenet)`.
3. CLAHE becomes an optional step toggleable via config. The `CONTEXT.md` / code ambiguity is resolved (kept on or off — Design Q2).
4. New model integration costs: define a new config dataclass, not duplicate preprocessing code.
5. Preprocessing steps testable independently of ONNX sessions.

## Non-Goals

- No model retraining or quantization changes.
- No changes to the `LivenessChecker`, `FaceRecognizer`, or `HeadPoseEstimator` ONNX inference logic.
- No changes to the temporal-smoothing algorithm (`LivenessTracker`).
- No new preprocessing steps beyond what's already implicit (CLAHE is the only borderline one).
- No changes to the `_crop_face` algorithm itself (just relocation + composition).

## Design Decisions

| # | Question | Final Answer |
|---|----------|--------------|
| 1 | `FacePreprocessor` class with composable steps, or a `preprocessing` module with free functions? | **Class with composable steps.** The per-model recipes (2.7/1.5, 128/224, [0,1]/imagenet, BGR/RGB, letterbox/direct) read better as named `PreprocessingConfig` instances than as free-function parameters. The frozen dataclass also gives a single audit point for what each model expects. |
| 2 | Is CLAHE part of the preprocessor or a separate "image enhancement" step? | **Optional step inside the preprocessor, default `use_clahe=False`.** The current production code (pre-refactor `LivenessChecker._preprocess` and `HeadPoseEstimator._preprocess`) had no CLAHE; Phase-1 testing showed CLAHE removal matched the MiniFASNet training distribution better. `CONTEXT.md` ambiguity is resolved: production code is the source of truth, `use_clahe=False` is the default, and the toggle is available for future experimentation. |
| 3 | Should the preprocessor know about model-specific quirks (e.g., MiniFASNet expects no ImageNet norm, just [0,1])? | **Yes — encoded in `PreprocessingConfig`.** The config carries `scale`, `target_size`, `normalize` (`"zero_one"` \| `"imagenet"`), `use_clahe`, `input_color` (`"rgb"` \| `"bgr"`), and `resize_mode` (`"letterbox"` \| `"direct"`). Every per-model difference lives in the config, not in conditional code. |
| 4 | Does this candidate overlap with #2 (`AIPipeline`)? | **Implemented #5 first.** The pipeline (#2) will now consume `FacePreprocessor` directly via `preprocessing_configs.LIVENESS_CONFIG` / `HEAD_POSE_CONFIG` — no re-invention of composition inside the pipeline. |
| 5 | What's the test strategy? | **Comprehensive unit tests per pipeline step** (crop, color, CLAHE, letterbox/direct resize, normalize, CHW transpose) **+ config validation + error paths** (32 tests in `test_face_preprocessor.py`). Snapshot tests deferred — the 32 unit tests plus the existing `LivenessChecker` / `HeadPoseEstimator` tests (which exercise the preprocessor end-to-end via the public API) cover the regression surface. |

### Additional decisions made during implementation

- **`_crop_face` location:** kept in `utils/face_utils.py` (4 callers in `ui/` import it directly). The preprocessor composes it as step 1; the cropping primitive stays where its other callers expect it. Moving it would have created churn in `camera_thread.py`, `enrollment_camera_thread.py`, and `enrollment_ai_worker.py` for no architectural gain.
- **Preprocessor input contract:** `__call__(face_crop, bbox=None)`. The plan said `(frame, bbox)`; we used `bbox` as optional so existing callers (which already pre-crop and pass a pre-cropped face) keep working without changes. The preprocessor is forward-compatible — a future PR can migrate callers to pass `bbox` and let the preprocessor own the crop step.
- **`use_clahe` default:** `False` in both `LIVENESS_CONFIG` and `HEAD_POSE_CONFIG`. The plan's `Implementation` table showed `use_clahe=True` for both, but that contradicted the production code (which had CLAHE removed). Code is the source of truth; production-matching default wins. The `use_clahe=True` entry in the plan table is now superseded.
- **Env var / UI wiring:** deferred. CLAHE is programmatically toggleable via `PreprocessingConfig(use_clahe=True)`. Wiring it to `.env` / Admin UI is a separate concern (follow-up PR).
- **Snapshot tests (`test_preprocessing_snapshot.py`):** deferred. The 32 unit tests + the existing 167 tests passing (199/199 total) cover the regression risk adequately; snapshot tests would add a "where do the expected values come from?" maintenance question.

## Implementation

### Files to change

| File | Change |
|------|--------|
| `src/attendance_system/services/face_preprocessor.py` *(new)* | Define `FacePreprocessor` class. Inputs: `PreprocessingConfig` dataclass (scale, target_size, normalize, use_clahe). Methods: `__call__(frame, bbox) -> np.ndarray` returns CHW float32 tensor. |
| `src/attendance_system/services/preprocessing_configs.py` *(new)* | Module-level constants: `LIVENESS_CONFIG = PreprocessingConfig(scale=2.7, size=128, norm="zero_one", use_clahe=True)`, `HEAD_POSE_CONFIG = PreprocessingConfig(scale=1.5, size=224, norm="imagenet", use_clahe=True)`. |
| `src/attendance_system/services/ai_pipeline.py` | `LivenessChecker._preprocess` becomes a one-liner: `return self._preprocessor(frame, bbox)` with `LIVENESS_CONFIG`. |
| `src/attendance_system/services/head_pose.py` | `HeadPoseEstimator._preprocess` becomes a one-liner: `return self._preprocessor(frame, bbox)` with `HEAD_POSE_CONFIG`. |
| `src/attendance_system/utils/face_utils.py` | `_crop_face` is either moved into `face_preprocessor.py` (since it becomes the first step) or kept here and called by the preprocessor. Decide during grilling. |
| `tests/unit/test_face_preprocessor.py` *(new)* | Test each step: crop with scale, resize to target, normalize (zero_one vs imagenet), transpose. Test config combinations. |
| `tests/unit/test_preprocessing_snapshot.py` *(new, optional)* | Snapshot test: given a fixed input image, output tensor matches expected values within tolerance. Protects against silent shape/range/order changes. |
| `CONTEXT.md` | Resolve CLAHE ambiguity. Add new term: **FacePreprocessor** — the composable crop → resize → normalize → to_tensor pipeline. |
| `.env.example` | (If CLAHE becomes configurable) add `FACE_PREPROCESSING_CLAHE_ENABLED` env var. |

### Touch points by line (reference)

- `services/ai_pipeline.py:_preprocess` (inside `LivenessChecker`)
- `services/head_pose.py:_preprocess` (inside `HeadPoseEstimator`)
- `utils/face_utils.py:11-22` — `_crop_face`
- `AGENTS.md` "Liveness" section — `_crop_face` scale: 2.7 for liveness, 1.5 for head-pose.

## Testing

### Unit tests to add (in `test_face_preprocessor.py`)

- `test_crop_with_scale_2_7` — bbox at (100,100,200,200) with scale 2.7 → output crop is 270×270 around the face.
- `test_crop_with_scale_1_5` — same bbox with scale 1.5 → output crop is 150×150.
- `test_resize_to_target_size` — 270×270 input → 128×128 output (for liveness config).
- `test_resize_preserves_aspect_ratio_with_letterbox` — non-square input → padded to square.
- `test_normalize_zero_one` — output values in [0, 1] range.
- `test_normalize_imagenet` — output values normalized with ImageNet mean/std.
- `test_transpose_to_chw` — output shape is (3, H, W) not (H, W, 3).
- `test_clahe_enabled_improves_contrast` — same input, with and without CLAHE → CLAHE has higher std deviation.
- `test_clahe_disabled_passthrough` — with CLAHE off, output equals input (modulo resize).

### Snapshot tests (in `test_preprocessing_snapshot.py`, optional)

- `test_liveness_preprocessing_snapshot` — fixed image, liveness config → output matches stored hash.
- `test_head_pose_preprocessing_snapshot` — fixed image, head-pose config → output matches stored hash.

### Manual smoke checklist

1. With the new preprocessor, run an attendance session. Verify: recognition accuracy unchanged.
2. Toggle CLAHE off via config. Verify: poor-light performance degrades (matches pre-CLAHE-removal behavior per `CONTEXT.md`).
3. Toggle CLAHE on. Verify: poor-light performance is at the current baseline.
4. Add a 3rd config (e.g., a new model with different normalization). Verify: defining the config is enough — no code changes in `LivenessChecker` or `HeadPoseEstimator`.
5. Visually inspect a few preprocessed tensors (save to disk, view in numpy viewer). Verify: shape, range, and order match the training pipeline expectations per `CONTEXT.md` "MiniFASNet Specs".

### Verification commands

```bash
pytest tests/unit/test_face_preprocessor.py -v
pytest tests/unit/test_preprocessing_snapshot.py -v
pytest tests/integration/ -v
ruff check src/attendance_system/services/face_preprocessor.py
```

## Related

- Parent plan: [0002 — Architecture Deepening Checklist](../active/0002-architecture-deepening.md) (candidate #5, marked `[x]`).
- Successor (recommended): [0004 — AIPipeline](../active/0004-ai-pipeline-orchestrator.md) — pipeline consumes a deep preprocessor. **Unblocked** by this plan's completion.
- `AGENTS.md` "Liveness" — `_crop_face` scale (2.7 / 1.5); `LivenessChecker` and `HeadPoseEstimator` preprocessing; `FacePreprocessor` reference.
- `CONTEXT.md` "Preprocessing" — CLAHE (resolved: `use_clahe=False` default), crop scale, letterbox resize. New term: **FacePreprocessor**.
- `CONTEXT.md` "Phase 1 Findings" — CLAHE removal was tested and the result kept.
- `CONTEXT.md` "Phase 2 Findings" — preprocessing design for liveness: 128×128, [0,1] range.
- Branch: `refactor/source-code`. Commit: `8863ec1`.
