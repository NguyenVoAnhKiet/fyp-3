# Plan 0004: Introduce `AIPipeline` Orchestrator

**Parent plan:** [0002 — Architecture Deepening Checklist](0002-architecture-deepening.md) (candidate #2).

## Status

**Draft** — design pending grilling. Surfaced by `improve-codebase-architecture` skill; see friction recap in parent plan.

**Dependency:** recommended to be implemented after [0007 — FacePreprocessor](0007-face-preprocessor.md) so the pipeline consumes a deep preprocessor.

**Implementation:** ✅ Complete (Plan 0004-impl). See `docs/plans/active/0004-ai-pipeline-orchestrator-implement.md`.

## Context

The per-frame AI pipeline is distributed across 6 files in 4 layers:

| File | Role |
|------|------|
| `services/ai_pipeline.py` | `LivenessChecker`, `FaceRecognizer` (ONNX inference + decision logic) |
| `services/head_pose.py` | `HeadPoseEstimator` (separate ONNX inference) |
| `core/liveness_tracker.py` | `LivenessTracker` (EMA + hysteresis + IoU — lives in `core/` but only `AIWorker` uses it) |
| `ui/camera_thread.py` | `AIWorker.run()` manually sequences: `_crop_face` → `LivenessChecker.check` → `LivenessTracker.update` → `compute_iou` → `FaceRecognizer.identify` |
| `ui/enrollment_ai_worker.py` | `EnrollmentAIWorker.run()` manually sequences: `_crop_face` → `HeadPoseEstimator.estimate` → `LivenessChecker.check` → embedding extraction |
| `utils/face_utils.py` | `_crop_face` (shared, scale parameter) |

Understanding "how does a single frame get processed" requires reading 6 files. There's no `AIPipeline.run(frame) -> PipelineResult`. `LivenessTracker` is in the wrong layer (per seam-placement rule: code should live where it has leverage, and only one caller uses it).

## Goals

1. Single `AIPipeline.run(frame) -> PipelineResult` encapsulates the per-frame sequence.
2. `PipelineResult` is a dataclass with optional fields: `liveness`, `recognition`, `head_pose`, `cropped_face`. Callers don't peek at internals.
3. `AIWorker.run()` and `EnrollmentAIWorker.run()` shrink to: `frame = camera.read(); result = self._pipeline.run(frame); self._emit(result)`.
4. `LivenessTracker` moves from `core/` to `services/ai_pipeline.py` (or stays in `core/` if justified — Design Q4).
5. Frame-skip counter (`_AI_FRAME_SKIP = 3`) lives in the pipeline, not the camera thread. The pipeline is self-paced.
6. Crop-scale selection (2.7 for liveness, 1.5 for head-pose) is part of pipeline configuration, not a per-call parameter.
7. The pipeline is testable through its interface (inject mock `LivenessChecker` + `FaceRecognizer`), without needing QThread or real ONNX models.

## Non-Goals

- No changes to ONNX model files or their loading sequence.
- No changes to the per-model decision logic (logit diff → threshold, similarity threshold, Euler angle bounds) — those stay in their respective classes.
- No changes to the temporal-smoothing algorithm (`LivenessTracker` math stays the same, just relocated).
- No new AI model integration.
- No removal of the existing `LivenessChecker` / `FaceRecognizer` / `HeadPoseEstimator` classes — they become adapters consumed by the pipeline.

## Design Decisions

_To be filled by grilling session. Five design questions in scope:_

| # | Question | Constraints |
|---|----------|-------------|
| 1 | One `AIPipeline` for both attendance and enrollment, or two specialized pipelines? | Attendance: liveness + recognition. Enrollment: head-pose + liveness + embedding extraction. Different crops (2.7 vs 1.5), different result fields. Is the overlap worth one class with configuration? |
| 2 | What is the `PipelineResult` shape? | Dataclass with `liveness`, `recognition`, `head_pose`, `cropped_face` fields (each optional, set to `None` if the corresponding step was skipped)? |
| 3 | Does `AIPipeline` own the frame-skip counter (`_AI_FRAME_SKIP = 3`)? | Currently `CameraThread.run()` owns it. Moving it to the pipeline makes the pipeline self-paced; eliminates the need for the caller to know about frame pacing. |
| 4 | Where does `LivenessTracker` belong? | Move from `core/` to `services/ai_pipeline.py`, or keep in `core/` as a shared utility? Per the seam-placement rule, if only one caller uses it, that's where it should live. |
| 5 | Is the crop-scale selection (2.7 vs 1.5) per-call or part of pipeline configuration? | A `LivenessPreprocessing(scale=2.7)` config embedded in the pipeline is cleaner than passing scale as a parameter to each call. |

## Implementation

### Files to change

| File | Change |
|------|--------|
| `src/attendance_system/services/ai_pipeline.py` | Add `AIPipeline` class. Compose `LivenessChecker` + `LivenessTracker` + `FaceRecognizer` + `HeadPoseEstimator` as injected dependencies. Owns the frame-skip counter. `run(frame) -> PipelineResult` returns a dataclass with optional fields. |
| `src/attendance_system/services/pipeline_result.py` *(new)* | Define `@dataclass(slots=True) PipelineResult` with fields: `liveness: LivenessResult \| None`, `recognition: RecognitionResult \| None`, `head_pose: HeadPoseResult \| None`, `cropped_face: np.ndarray \| None`. |
| `src/attendance_system/core/liveness_tracker.py` | Either: (a) move to `services/ai_pipeline.py` (if Design Q4 decides so), or (b) keep here but pass to `AIPipeline` as an injected dependency. |
| `src/attendance_system/services/head_pose.py` | No internal changes. Becomes a dependency of `AIPipeline` (or a separate `EnrollmentPipeline` if Design Q1 decides on two pipelines). |
| `src/attendance_system/ui/camera_thread.py` | `AIWorker.run()` reduces to: `frame = self._pipeline.read_frame()`; `result = self._pipeline.run(frame)`; `self._emit(result)`. Delete manual sequencing and inline calls. |
| `src/attendance_system/ui/enrollment_ai_worker.py` | `EnrollmentAIWorker.run()` same reduction. |
| `tests/unit/test_ai_pipeline.py` | New tests for `AIPipeline.run()` with mock `LivenessChecker` + `FaceRecognizer`. Frame-skip counter behavior. PipelineResult population. |
| `tests/unit/test_pipeline_result.py` *(new)* | PipelineResult field defaults, equality, immutability. |
| `CONTEXT.md` | Add new term: **PipelineResult** — the structured output of a single frame through the AI pipeline. |

### Touch points by line (reference)

- `camera_thread.py:106-171` — `AIWorker.run()` body (will shrink dramatically)
- `enrollment_ai_worker.py:69-155` — `EnrollmentAIWorker.run()` body
- `core/liveness_tracker.py:116-208` — main tracker logic (relocation target)
- `services/ai_pipeline.py:38-306` — current `LivenessChecker` and `FaceRecognizer` definitions
- `services/head_pose.py:30-91` — `HeadPoseEstimator` (no changes, just becomes a dependency)

## Testing

### Unit tests to add (in `test_ai_pipeline.py`)

- `test_pipeline_returns_result_with_liveness` — mock `LivenessChecker.check` returns real → result.liveness is real.
- `test_pipeline_returns_result_with_recognition` — mock `FaceRecognizer.identify` returns user_id → result.recognition.user_id set.
- `test_pipeline_skips_frame_at_skip_counter` — pipeline.run(frame) called 3 times → `_process_frame` called once.
- `test_pipeline_resets_skip_counter_on_pipeline_run` — counter accumulates across `run()` calls correctly.
- `test_pipeline_returns_none_fields_when_step_disabled` — `liveness_checker=None` → result.liveness is None.
- `test_pipeline_propagates_liveness_tracker_state` — two consecutive frames for same face → tracker.ema carries over.
- `test_pipeline_emits_circuit_breaker_signal_on_persistent_failure` — `LivenessChecker.check` raises 30 times → `camera_error` signal.
- `test_pipeline_result_dataclass_fields` — defaults, equality, slots, hash.

### Unit tests to delete or move

- `test_camera_thread.py` — tests that mock `LivenessChecker` or `FaceRecognizer` at the worker level become waste (test moved to pipeline).
- `test_enrollment_ai_worker.py` — same.

### Manual smoke checklist

1. Start an attendance session. Verify: recognition + liveness work as before, `LivenessTracker` EMA/hysteresis still smooths flicker.
2. Trigger a spoof event. Verify: red bbox, "spoof" decision, liveness_tracker state correct.
3. Start enrollment. Capture 3 head poses. Verify: pose angles reported correctly, embedding stored.
4. With `LivenessChecker` model path pointing at a non-existent file, verify: circuit-breaker triggers after 30 attempts (same as today).
5. With face partially out of frame, verify: liveness tracker IoU re-tracks correctly across the gap.

### Verification commands

```bash
pytest tests/unit/test_ai_pipeline.py -v
pytest tests/unit/test_pipeline_result.py -v
pytest tests/unit/test_camera_thread.py -v
pytest tests/unit/test_enrollment_ai_worker.py -v
ruff check src/attendance_system/services/
```

## Related

- Parent plan: [0002 — Architecture Deepening Checklist](0002-architecture-deepening.md)
- Predecessor (recommended): [0007 — FacePreprocessor](0007-face-preprocessor.md) — pipeline consumes a deep preprocessor.
- Sibling: [0003 — CameraWorkerBase](0003-camera-worker-base.md) — independent; can be done before or after.
- `AGENTS.md` "Gotchas" — `_COOLDOWN_SECONDS = 3.0`, `_AI_FRAME_SKIP = 3`, `_crop_face` scale (2.7 liveness, 1.5 head-pose), `LivenessTracker` (EMA α=0.4, hysteresis T_HIGH=0.65/T_LOW=0.45, IoU).
- `CONTEXT.md` — will gain **PipelineResult** term.
- Branch: `refactor/source-code`.
