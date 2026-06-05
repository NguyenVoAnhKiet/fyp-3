# Plan 0003: Extract Camera Worker Base Classes

**Parent plan:** [0002 — Architecture Deepening Checklist](2026-06-06-0002-architecture-deepening.md) (candidate #1).

## Status

**Done** — implemented 2026-06-04, commit `7e0e747` on `refactor/source-code`.

## Context

Camera infrastructure is duplicated across 3 files:

- `ui/camera_thread.py` (attendance: `CameraThread` + inner `AIWorker`)
- `ui/enrollment_camera_thread.py` (enrollment: `EnrollmentCameraThread`)
- `ui/enrollment_ai_worker.py` (enrollment: `EnrollmentAIWorker`)

7 patterns copy-pasted: `_retry_read()`, circuit-breaker counter, sentinel shutdown queue, `submit_task()` numpy-copy, stop/drain, `_READ_RETRY_DELAYS`, `_PAUSE_POLL_INTERVAL_SECONDS`. Changing the circuit-breaker threshold (ADR-0001: 30) requires touching 3 files. Adding a new camera feature costs ~120 LOC instead of ~40.

Two distinct duplication clusters exist:
1. **Camera capture threads** (`CameraThread` + `EnrollmentCameraThread`): share camera init, `_retry_read()`, frame loop, pause/resume, stop/drain, bbox drawing, display emission.
2. **AI processing workers** (`AIWorker` + `EnrollmentAIWorker`): share queue(maxsize=1), sentinel shutdown, `submit_task()` numpy-copy, `is_busy()`, circuit-breaker, stop/drain.

## Goals

1. Two base classes: `CameraThreadBase(QThread)` for camera capture, `AIWorkerBase(QThread)` for AI processing.
2. Both `CameraThread` and `EnrollmentCameraThread` inherit from `CameraThreadBase`; their `run()` overrides only differ in the per-frame AI step.
3. Both `AIWorker` and `EnrollmentAIWorker` inherit from `AIWorkerBase`; their `_process_frame()` overrides only differ in signal emission.
4. Circuit-breaker threshold becomes one constant in `AIWorkerBase`, not three.
5. Adding a new camera-threaded feature costs ~40 LOC instead of ~120.
6. ADR-0001 semantics preserved: shared counter, one broken model kills both.

## Non-Goals

- No changes to AI inference logic (detection, recognition, liveness, head-pose).
- No changes to camera index selection or backend (`cv2.VideoCapture`).
- No changes to PyQt signal types emitted to UI.
- No removal of `EnrollmentCameraThread` — it is actively used by `enrollment_widget.py`.
- No new threading model. Both bases inherit from `QThread` exactly as today.

## Design Decisions

_Answers derived from codebase analysis (2026-06-03)._

| # | Question | Recommendation | Rationale |
|---|----------|---------------|-----------|
| 1 | Base class vs mixin vs composition? | **Two base classes** — `CameraThreadBase(QThread)` for camera capture threads, `AIWorkerBase(QThread)` for AI processing workers. Inheritance. | Two distinct shared concepts, not one. `CameraThread` and `EnrollmentCameraThread` share camera init + `_retry_read()` + frame loop + stop/drain. `AIWorker` and `EnrollmentAIWorker` share queue + sentinel + `submit_task()` + `is_busy()` + circuit-breaker + stop/drain. Composition would require injecting two separate concerns; inheritance matches the existing QThread pattern. A single base class doesn't work because the `run()` loops are fundamentally different (camera capture vs queue consumer). |
| 2 | Per-model or shared circuit-breaker counter? | **Shared counter** — preserve ADR-0001 intent. One broken model kills both. | ADR-0001 says: "The counter is shared between liveness and head-pose — one broken model kills both." In `EnrollmentAIWorker`, the counter IS shared (single `_consecutive_failures` incremented on either `PoseInferenceError` or `LivenessInferenceError`). The "independent counters by variable reuse" concern from the original plan was based on `camera_thread.py`'s `AIWorker`, which only catches `LivenessInferenceError` — but that's attendance (no head-pose), so there's no conflict. The enrollment worker already implements the ADR correctly. **No ADR update needed.** |
| 3 | Is `EnrollmentCameraThread` legacy path dead code? | **No — it is actively used.** | `enrollment_widget.py` imports and instantiates `EnrollmentCameraThread` (line 32, 289). It delegates AI to `EnrollmentAIWorker` internally. 13 references in tests. It is NOT dead code. Both `CameraThread` and `EnrollmentCameraThread` must be refactored. |
| 4 | Where does the base live? | **`ui/camera_worker_base.py`** for both bases. | Camera threads and AI workers are UI-layer threading components. They emit Qt signals to the UI. A `core/` or `infrastructure/` package would be misleading — these are not domain-agnostic infrastructure. Keeping them in `ui/` maintains locality with their consumers. |
| 5 | What goes behind the seam vs in the interface? | See tables below. | The seam is the `run()` method: concrete in base (camera read + queue drain), calls abstract `_process_frame()` for per-thread logic. |

### CameraThreadBase — public interface

| Method | Concrete in base? | Notes |
|--------|-------------------|-------|
| `__init__(camera_index, detector_model_path, ...)` | Yes | Camera init, detector setup |
| `run()` | Yes (concrete) | Open camera → loop: check paused → read → retry on failure → detect faces → call `_process_frame()` → draw bboxes → emit frame |
| `_retry_read(cap)` | Yes | Exponential backoff reconnection (verbatim from both threads) |
| `stop()` | Yes | Disconnect signals, stop child worker, `wait()` |
| `pause()` / `resume()` | Yes | `_paused` flag + poll interval (currently only in `CameraThread`, promoted to base) |
| `_process_frame(frame, faces)` | **Abstract** | Per-thread: attendance annotates + submits to AIWorker; enrollment does legacy OR pose-based capture |
| `_emit_display_frame(frame_rgb)` | Yes | QImage conversion + `.copy()` + `frame_ready.emit()` |
| `_draw_bboxes(frame_rgb)` | Yes | Colored rectangles + landmarks |
| `_annotate_frame(qimg)` | Yes | QPainter text labels (success/spoof/unrecognized) |

### AIWorkerBase — public interface

| Method | Concrete in base? | Notes |
|--------|-------------------|-------|
| `__init__(pipeline, parent)` | Yes | Queue(maxsize=1), `_running`, `_consecutive_failures` |
| `run()` | Yes (concrete) | Queue consumer loop: get task → call `_process_frame()` → emit results → circuit-breaker on failure |
| `submit_task(...)` | Yes | `put_nowait()` with numpy `.copy()` |
| `is_busy()` | Yes | `qsize >= maxsize` |
| `stop()` | Yes | Drain queue + push sentinel + `wait(3000)` |
| `_process_frame(task)` | **Abstract** | Per-worker: attendance emits `recognition_result`; enrollment emits `pose_estimated` + `capture_complete` |
| `_on_success(result)` | **Abstract** | Per-worker signal emission |
| `_on_failure(error)` | Yes | Circuit-breaker logic, `camera_error` / `inference_warning` signals |

## Implementation

### Files to change

| File | Change |
|------|--------|
| `src/attendance_system/ui/camera_worker_base.py` *(new)* | Define `CameraThreadBase(QThread)` with: camera init, `_retry_read()`, pause/resume, `_draw_bboxes()`, `_annotate_frame()`, `_emit_display_frame()`, `stop()`. `run()` is concrete (open camera → loop → detect → `_process_frame()` → draw → emit). `_process_frame()` is abstract. Define `AIWorkerBase(QThread)` with: queue + sentinel, `submit_task()`, `is_busy()`, `stop()`, circuit-breaker. `run()` is concrete (queue consumer → `_process_frame()` → success/failure). `_process_frame()` is abstract. |
| `src/attendance_system/ui/camera_thread.py` | `CameraThread` inherits `CameraThreadBase`. Remove: `_retry_read()`, `_draw_bboxes()`, `_annotate_frame()`, `_emit_display_frame()`, `_paused`/`pause()`/`resume()`, duplicated constants. Keep: `__init__()` (creates `AIWorker`), `run()` override (calls base loop + submits to AI worker), `_on_recognition_result()`, `_on_ai_worker_camera_error()`. `AIWorker` inherits `AIWorkerBase`. Remove: queue, sentinel, `_consecutive_failures`, `submit_task()`, `is_busy()`, `stop()`. Keep: `__init__()`, `_process_frame()` override (calls `pipeline.run_attendance()`), `_on_success()` override (emits `recognition_result`). |
| `src/attendance_system/ui/enrollment_camera_thread.py` | `EnrollmentCameraThread` inherits `CameraThreadBase`. Remove: `_retry_read()`, duplicated constants. Keep: `__init__()` (creates `EnrollmentAIWorker`), `run()` override (calls base loop + handles enrollment state machine), enrollment-specific methods (`_handle_legacy_frame`, `_handle_pose_frame`, `_on_pose_estimated`, `_on_capture_complete`, `_draw_status`). |
| `src/attendance_system/ui/enrollment_ai_worker.py` | `EnrollmentAIWorker` inherits `AIWorkerBase`. Remove: queue, sentinel, `_consecutive_failures`, `submit_task()`, `is_busy()`, `stop()`. Keep: `__init__()`, `_process_frame()` override (calls `pipeline.run_enrollment()`), `_on_success()` override (emits `pose_estimated` + `capture_complete`). |
| `tests/unit/test_camera_worker_base.py` *(new)* | Test shared infrastructure: queue mechanics, sentinel shutdown, circuit-breaker count, retry-with-backoff, `pause()` polling, `stop()` signal disconnect. |
| `tests/unit/test_camera_thread.py` | Update existing tests to use the new base — most queue/sentinel tests are now covered by the base test suite and should be deleted from this file. |
| `tests/unit/test_enrollment_ai_worker.py` | Same: update to consume base; keep only enrollment-specific inference tests. |
| `docs/adr/0001-onnx-circuit-breaker.md` | **No update needed** — shared counter semantics are already correct per codebase analysis. |

### Touch points by line (reference)

- `camera_thread.py:21-35` — duplicated constants (`_AI_FRAME_SKIP`, `_COOLDOWN_SECONDS`, `_PAUSE_POLL_INTERVAL_SECONDS`, `_COLOR_*`, `_RESULT_HOLD_FRAMES`, `_MAX_CONSECUTIVE_FAILURES`, `_READ_RETRY_DELAYS`, `_MAX_READ_RETRIES`)
- `camera_thread.py:42-167` — `AIWorker` class (queue, sentinel, submit_task, run, stop — all move to `AIWorkerBase`)
- `camera_thread.py:169-262` — `CameraThread.__init__` + `pause()`/`resume()`/`stop()` (pause/resume move to base)
- `camera_thread.py:263-285` — `_retry_read()` (verbatim copy → base)
- `camera_thread.py:291-351` — `CameraThread.run()` (camera loop → base)
- `camera_thread.py:357-441` — `_detect_faces()`, `_draw_bboxes()`, `_emit_display_frame()`, `_annotate_frame()` (all move to base)
- `enrollment_camera_thread.py:32-34` — duplicated constants
- `enrollment_camera_thread.py:128-151` — `_retry_read()` (verbatim copy → base)
- `enrollment_ai_worker.py:17-18, 40-42` — `_SENTINEL`, `_MAX_CONSECUTIVE_FAILURES`, queue setup (all move to `AIWorkerBase`)
- `enrollment_ai_worker.py:44-59` — `submit_task()` (move to base)
- `enrollment_ai_worker.py:61-114` — `run()` (queue consumer → base; `_process_frame` override stays)
- `enrollment_ai_worker.py:116-138` — `stop()` (move to base)

## Testing

### Unit tests to add (in `test_camera_worker_base.py`)

- `test_base_processes_submitted_frame` — `submit_task(frame)` → `_process_frame` called exactly once with the frame.
- `test_base_drains_queue_on_stop` — `stop()` waits for in-flight task to complete before thread exits.
- `test_circuit_breaker_kills_thread_after_threshold_failures` — `_process_frame` raises 30 times → `camera_error` signal emitted + thread exits.
- `test_circuit_breaker_resets_on_success` — 29 failures + 1 success → counter resets to 0.
- `test_pause_skips_processing` — `pause()` during a frame → `_process_frame` not called; `resume()` re-enables.
- `test_retry_read_handles_transient_failures` — first 2 `cap.read()` return `False`, third succeeds → no error signal, no failure counter increment.
- `test_retry_read_gives_up_after_max_retries` — all retries fail → `camera_error` signal + counter increments.
- `test_sentinel_terminates_idle_worker` — `stop()` with empty queue → thread exits within 100ms.

### Unit tests to delete (move to base test)

- `test_camera_thread.py:52-268` queue/sentinel/circuit-breaker tests — replaced by base test.
- `test_enrollment_ai_worker.py` queue/sentinel tests — replaced by base test.

### Manual smoke checklist

1. Start an attendance session. Recognize 3 users in sequence. Verify: no crashes, AI works as before, circuit-breaker logic equivalent.
2. Start enrollment. Capture 3 different head poses. Verify: enrollment pipeline unchanged, no regression in pose detection.
3. With camera unplugged mid-session, verify: 30 failures → `camera_error` modal appears (same as before refactor).
4. Click "Kết thúc phiên" mid-recognition. Verify: clean thread stop, no orphan frames, no QTimer crash.
5. With the camera returning intermittent errors (use a fake video that returns `False` for 5 frames, then `True`), verify: no spurious circuit-breaker trigger.

### Verification commands

```bash
pytest tests/unit/test_camera_worker_base.py -v
pytest tests/unit/test_camera_thread.py -v
pytest tests/unit/test_enrollment_ai_worker.py -v
pytest tests/integration/test_head_pose_enrollment.py -v
ruff check src/attendance_system/ui/camera_worker_base.py
```

## Sub-Agent Task Breakdown

### Phase 1: Create Base Classes (Parallel — no dependencies)

| Task | Agent | File | Description |
|------|-------|------|-------------|
| 1.1 | @fixer | `ui/camera_worker_base.py` | Create `CameraThreadBase(QThread)`: camera init, `_retry_read()`, `pause()`/`resume()`, `_draw_bboxes()`, `_annotate_frame()`, `_emit_display_frame()`, `stop()`. `run()` concrete loop calling abstract `_process_frame()`. |
| 1.2 | @fixer | `ui/camera_worker_base.py` | Create `AIWorkerBase(QThread)` in same file: queue(maxsize=1) + sentinel, `submit_task()`, `is_busy()`, `stop()` (drain + sentinel + wait), circuit-breaker in `run()`. `run()` concrete loop calling abstract `_process_frame()`. |
| 1.3 | @fixer | `tests/unit/test_camera_worker_base.py` | Write base class tests: queue mechanics, sentinel shutdown, circuit-breaker (30 failures → error, 29+1 success → reset), pause/resume, retry-read transient failures, retry-read max retries. |

### Phase 2: Refactor CameraThread + AIWorker (Sequential — depends on Phase 1)

| Task | Agent | File | Description |
|------|-------|------|-------------|
| 2.1 | @fixer | `ui/camera_thread.py` | Refactor `CameraThread` to inherit `CameraThreadBase`. Remove duplicated methods/constants. Override `_process_frame()`. |
| 2.2 | @fixer | `ui/camera_thread.py` | Refactor `AIWorker` to inherit `AIWorkerBase`. Remove queue/sentinel/stop. Override `_process_frame()` and `_on_success()`. |
| 2.3 | @fixer | `tests/unit/test_camera_thread.py` | Update tests: delete queue/sentinel/circuit-breaker tests (now in base test), keep attendance-specific tests. |

### Phase 3: Refactor EnrollmentCameraThread + EnrollmentAIWorker (Sequential — depends on Phase 1)

| Task | Agent | File | Description |
|------|-------|------|-------------|
| 3.1 | @fixer | `ui/enrollment_camera_thread.py` | Refactor `EnrollmentCameraThread` to inherit `CameraThreadBase`. Remove `_retry_read()`, duplicated constants. Override `_process_frame()`. Keep enrollment-specific state machine. |
| 3.2 | @fixer | `ui/enrollment_ai_worker.py` | Refactor `EnrollmentAIWorker` to inherit `AIWorkerBase`. Remove queue/sentinel/stop. Override `_process_frame()` and `_on_success()`. |
| 3.3 | @fixer | `tests/unit/test_enrollment_ai_worker.py` | Update tests: delete queue/sentinel tests (now in base test), keep enrollment-specific inference tests. |

### Phase 4: Integration Verification (Sequential — depends on Phases 2+3)

| Task | Agent | File | Description |
|------|-------|------|-------------|
| 4.1 | @fixer | — | Run full test suite: `pytest tests/ -v`. Fix any regressions. |
| 4.2 | @fixer | — | Run lint: `ruff check src/attendance_system/ui/`. Fix any violations. |
| 4.3 | @oracle | — | Architecture review: verify LSP compliance, seam placement, no behavior changes. |

### Dependency Graph

```
Phase 1 (Parallel):
  1.1 CameraThreadBase ──┐
  1.2 AIWorkerBase ──────┼──▶ Phase 2 ──┐
  1.3 Base tests ────────┘              │
                                        ├──▶ Phase 4
                         Phase 3 ────────┘
  (Parallel after Phase 1):
  3.1 EnrollmentCameraThread ──┐
  3.2 EnrollmentAIWorker ──────┼──▶ Phase 4
  3.3 Enrollment tests ────────┘
```

### Parallel Execution Opportunities

| Group | Tasks | Parallel? | Blocked By |
|-------|-------|-----------|------------|
| G1 | 1.1, 1.2, 1.3 | ✅ Yes | None |
| G2 | 2.1, 2.2, 2.3 | ⚠️ Sequential (same files) | G1 |
| G3 | 3.1, 3.2, 3.3 | ⚠️ Sequential (same files) | G1 |
| G4 | 4.1, 4.2, 4.3 | ⚠️ Sequential | G2 + G3 |

### Sub-Agent Summary

```
┌─────────────────────────────────────────────────────────────┐
│                    TASK DISTRIBUTION                         │
│                                                             │
│  @fixer (9 tasks):                                         │
│  ├─ 1.1 Create CameraThreadBase                           │
│  ├─ 1.2 Create AIWorkerBase                               │
│  ├─ 1.3 Base class tests                                  │
│  ├─ 2.1 Refactor CameraThread                             │
│  ├─ 2.2 Refactor AIWorker                                 │
│  ├─ 2.3 Update camera_thread tests                        │
│  ├─ 3.1 Refactor EnrollmentCameraThread                   │
│  ├─ 3.2 Refactor EnrollmentAIWorker                       │
│  └─ 3.3 Update enrollment tests                           │
│                                                             │
│  @oracle (1 task):                                         │
│  └─ 4.3 Final architecture review                         │
│                                                             │
│  Orchestrator (2 tasks):                                   │
│  ├─ 4.1 Run full test suite                               │
│  └─ 4.2 Run linting                                       │
│                                                             │
│  Total: 12 tasks                                           │
│  @fixer: 75% | @oracle: 8% | Orchestrator: 17%            │
└─────────────────────────────────────────────────────────────┘
```

## Related

- Parent plan: [0002 — Architecture Deepening Checklist](2026-06-06-0002-architecture-deepening.md)
- ADR-0001: `docs/adr/0001-onnx-circuit-breaker.md` (no update needed — shared counter already correct)
- `AGENTS.md` "Gotchas" — `QThread` thread-affinity rules, `EnrollmentCameraThread` flips frames (mirror), attendance `CameraThread` does not, `_COOLDOWN_SECONDS = 3.0`, `_AI_FRAME_SKIP = 3`, `_PAUSE_POLL_INTERVAL_SECONDS = 0.05`.
- Branch: `refactor/source-code`.
