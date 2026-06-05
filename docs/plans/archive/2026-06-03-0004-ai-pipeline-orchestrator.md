# Plan 0004: Introduce `AIPipeline` Orchestrator

**Parent plan:** [0002 — Architecture Deepening Checklist](2026-06-06-0002-architecture-deepening.md) (candidate #2).

## Status

**Done** ✅ — implemented on `refactor/source-code`, commit `a1590c1`. Implement plan: [2026-06-03-0004-ai-pipeline-orchestrator-implement.md](2026-06-03-0004-ai-pipeline-orchestrator-implement.md).

**Dependency:** Plan 0007 (FacePreprocessor) was implemented first; pipeline consumes `PreprocessingConfig` directly.

## Context

The per-frame AI pipeline is distributed across 6 files in 4 layers:

| File | Role (pre-0004) | Role (post-0004) |
|------|------|------|
| `services/ai_pipeline.py` | `LivenessChecker`, `FaceRecognizer` (ONNX inference + decision logic) | `LivenessChecker`, `FaceRecognizer`, **`AIPipeline`** orchestrator |
| `services/head_pose.py` | `HeadPoseEstimator` (separate ONNX inference) | Same — consumed by `AIPipeline` |
| `services/liveness_tracker.py` | _(was in `core/`)_ | **`LivenessTracker`** (relocated from `core/`) — composed into `AIPipeline` |
| `services/pipeline_result.py` *(new)* | — | **`PipelineResult`** dataclass — structured output of `AIPipeline.run()` |
| `ui/camera_thread.py` | `AIWorker.run()` manually sequences 5 steps | `AIWorker.run()` calls `self._pipeline.run(frame)` (~5 lines) |
| `ui/enrollment_ai_worker.py` | `EnrollmentAIWorker.run()` manually sequences 4 steps | `EnrollmentAIWorker.run()` calls `self._pipeline.run_enrollment(frame)` (~5 lines) |
| `utils/face_utils.py` | `_crop_face` (shared, scale parameter) | Same — called inside `AIPipeline` |

Understanding "how does a single frame get processed" now requires reading **1 file**: `services/ai_pipeline.py`. `LivenessTracker` moved to `services/` where it belongs (seam-placement: only `AIPipeline` uses it).

## Goals

1. ✅ Single `AIPipeline.run(frame) -> PipelineResult` encapsulates the per-frame sequence.
2. ✅ `PipelineResult` is a dataclass with optional fields: `liveness`, `recognition`, `head_pose`, `cropped_face`. Callers don't peek at internals.
3. ✅ `AIWorker.run()` and `EnrollmentAIWorker.run()` shrink to: `frame = camera.read(); result = self._pipeline.run(frame); self._emit(result)`.
4. ✅ `LivenessTracker` moved from `core/` to `services/liveness_tracker.py` (re-export shim in `core/` for backward compat).
5. ⬜ Frame-skip counter stays in UI layer (design decision: not pipeline responsibility).
6. ✅ Crop-scale selection via `PreprocessingConfig` from Plan 0007 — no hardcoded values.
7. ✅ Pipeline is testable through its interface — 16 unit tests in `test_ai_pipeline_orchestrator.py`.

## Non-Goals

- No changes to ONNX model files or their loading sequence.
- No changes to the per-model decision logic (logit diff → threshold, similarity threshold, Euler angle bounds) — those stay in their respective classes.
- No changes to the temporal-smoothing algorithm (`LivenessTracker` math stays the same, just relocated).
- No new AI model integration.
- No removal of the existing `LivenessChecker` / `FaceRecognizer` / `HeadPoseEstimator` classes — they become adapters consumed by the pipeline.

## Design Decisions

_Resolved by implementation plan (0004-impl). See `docs/plans/archive/2026-06-03-0004-ai-pipeline-orchestrator-implement.md` for full rationale._

| # | Question | Answer | Rationale |
|---|----------|--------|-----------|
| 1 | One `AIPipeline` for both attendance and enrollment, or two specialized pipelines? | **One class, two methods** — `run_attendance()` and `run_enrollment()` | Shared core (liveness + recognition) but distinct sequences. Avoids duplication; clear separation via method names. |
| 2 | What is the `PipelineResult` shape? | `@dataclass(slots=True)` with `result_type` discriminator + optional `liveness`, `recognition`, `head_pose`, `cropped_face` fields | Follows existing patterns. Discriminator enables callers to switch on outcome without probing optional fields. |
| 3 | Does `AIPipeline` own the frame-skip counter? | **No** — stays in UI/camera thread | Performance optimization policy, not pipeline responsibility. Caller decides when to invoke pipeline. |
| 4 | Where does `LivenessTracker` belong? | **`services/liveness_tracker.py`** (relocated from `core/`) | AI service, not system core. Only `AIPipeline` uses it — seam-placement rule: live where you have leverage. |
| 5 | Is crop-scale selection per-call or part of pipeline configuration? | **`PreprocessingConfig`** (from Plan 0007) | Leverages completed Plan 0007. Eliminates hardcoded scale values; configurable per model. |

## Implementation

### Files changed (commit `a1590c1`)

| File | Change |
|------|--------|
| `src/attendance_system/services/pipeline_result.py` *(new)* | `@dataclass(slots=True) PipelineResult` with `result_type` discriminator + optional fields. |
| `src/attendance_system/services/liveness_tracker.py` *(new)* | `LivenessTracker` relocated from `core/`. Same logic, new location. |
| `src/attendance_system/services/ai_pipeline.py` | Added `AIPipeline` class. Composes `LivenessChecker` + `LivenessTracker` + `FaceRecognizer`. Methods: `run_attendance()`, `run_enrollment()`. |
| `src/attendance_system/core/liveness_tracker.py` | Re-export shim for backward compatibility. |
| `src/attendance_system/ui/camera_thread.py` | `AIWorker` takes `AIPipeline`; `run()` reduced from ~80 to ~30 lines. |
| `src/attendance_system/ui/enrollment_ai_worker.py` | `EnrollmentAIWorker` takes `AIPipeline`; `run()` reduced from ~87 to ~5 lines. |
| `src/attendance_system/ui/enrollment_camera_thread.py` | Creates `AIPipeline` for enrollment path. |
| `tests/unit/test_pipeline_result.py` *(new)* | 13 tests: field defaults, equality, immutability. |
| `tests/unit/test_ai_pipeline_orchestrator.py` *(new)* | 16 tests: both pipeline modes, edge cases, field population. |
| `tests/unit/test_camera_thread.py` | Updated `AIWorker` constructor to accept `AIPipeline`. |
| `tests/unit/test_enrollment_ai_worker.py` | Updated `EnrollmentAIWorker` constructor to accept `AIPipeline`. |
| `tests/unit/test_liveness_tracker.py` | Updated import to `services/liveness_tracker`. |
| `CONTEXT.md` | Added **PipelineResult**, **AIPipeline** terms. |
| `AGENTS.md` | Updated AI Pipeline Orchestration section, file locations, liveness terms. |

### Touch points (reference)

- `ui/camera_thread.py` — `AIWorker.run()` reduced from ~80 to ~30 lines (delegates to `AIPipeline`).
- `ui/enrollment_ai_worker.py` — `EnrollmentAIWorker.run()` reduced from ~87 to ~5 lines (delegates to `AIPipeline`).
- `services/ai_pipeline.py` — `AIPipeline` class added; `LivenessChecker` and `FaceRecognizer` now composed as dependencies.
- `services/liveness_tracker.py` — relocated from `core/`, same logic.
- `services/pipeline_result.py` — new `PipelineResult` dataclass.

## Testing

### Unit tests added

- `tests/unit/test_pipeline_result.py` — 13 tests: field defaults, equality, immutability, `result_type` discriminator.
- `tests/unit/test_ai_pipeline_orchestrator.py` — 16 tests: `run_attendance()`, `run_enrollment()`, field population, edge cases.

### Unit tests updated (not deleted)

- `tests/unit/test_camera_thread.py` — constructor updated to pass `AIPipeline`.
- `tests/unit/test_enrollment_ai_worker.py` — constructor updated to pass `AIPipeline`.
- `tests/unit/test_liveness_tracker.py` — import path updated to `services/liveness_tracker`.

### Manual smoke checklist

1. ✅ Attendance session: recognition + liveness work as before, `LivenessTracker` EMA/hysteresis smooths flicker.
2. ✅ Spoof event: red bbox, "spoof" decision, liveness_tracker state correct.
3. ✅ Enrollment: 3 head poses captured, pose angles reported, embedding stored.
4. ✅ Circuit-breaker: `LivenessChecker` model path pointing at non-existent file → triggers after 30 attempts.
5. ✅ Face partially out of frame: liveness tracker IoU re-tracks correctly across the gap.

### Verification commands

```bash
pytest tests/unit/test_pipeline_result.py -v
pytest tests/unit/test_ai_pipeline_orchestrator.py -v
pytest tests/unit/test_camera_thread.py -v
pytest tests/unit/test_enrollment_ai_worker.py -v
ruff check src/attendance_system/services/
```

## Related

- Parent plan: [0002 — Architecture Deepening Checklist](2026-06-06-0002-architecture-deepening.md)
- Implement plan: [0004-impl](../archive/2026-06-03-0004-ai-pipeline-orchestrator-implement.md) — **Done** ✅
- Predecessor (completed): [0007 — FacePreprocessor](../archive/2026-06-03-0007-face-preprocessor.md) — pipeline consumes `PreprocessingConfig` directly.
- Sibling: [0003 — CameraWorkerBase](0003-camera-worker-base.md) — independent; can be done before or after.
- `AGENTS.md` "Gotchas" — `_COOLDOWN_SECONDS = 3.0`, `_AI_FRAME_SKIP = 3`, `_crop_face` scale (2.7 liveness, 1.5 head-pose), `LivenessTracker` (EMA α=0.4, hysteresis T_HIGH=0.65/T_LOW=0.45, IoU).
- `CONTEXT.md` — **PipelineResult**, **AIPipeline** terms added.
- Branch: `refactor/source-code`.
