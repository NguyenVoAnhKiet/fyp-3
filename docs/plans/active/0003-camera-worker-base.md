# Plan 0003: Extract `CameraWorkerBase`

**Parent plan:** [0002 — Architecture Deepening Checklist](0002-architecture-deepening.md) (candidate #1).

## Status

**Draft** — design pending grilling. Surfaced by `improve-codebase-architecture` skill; see friction recap in parent plan.

## Context

Camera infrastructure is duplicated verbatim across 3 files:

- `ui/camera_thread.py` (attendance path: `CameraThread` + inner `AIWorker`)
- `ui/enrollment_camera_thread.py` (enrollment legacy path)
- `ui/enrollment_ai_worker.py` (enrollment AI worker)

7 patterns copy-pasted: `_retry_read()`, circuit-breaker counter, sentinel shutdown queue, `submit_task()` numpy-copy, stop/drain, `_READ_RETRY_DELAYS`, `_PAUSE_POLL_INTERVAL_SECONDS`. Changing the circuit-breaker threshold (ADR-0001: 30) requires touching 3 files. Adding a new camera feature costs ~120 LOC instead of ~40.

**ADR-0001 conflict worth reopening:** the ADR says "the counter is shared between liveness and head-pose in the enrollment thread." In `EnrollmentAIWorker`, head-pose and liveness have **independent** consecutive-failure counters — they share `self._consecutive_failures` only by variable reuse, not by design. If head-pose fails 29 times then succeeds, the counter resets even if liveness has been silently failing. The new base class is a natural place to encode the correct semantics (either per-model counters with the original "kill on any persistent failure" intent, or a single shared counter with documented reset semantics).

## Goals

1. Single `CameraWorkerBase(QThread)` (or mixin) owns: camera read with retry, circuit-breaker, sentinel-driven queue, signal disconnect on stop, `_PAUSE_POLL_INTERVAL_SECONDS` polling.
2. Both `AIWorker` (attendance) and `EnrollmentAIWorker` (enrollment) consume the base; their `run()` overrides only differ in the per-frame inference step.
3. ADR-0001 semantics made explicit: circuit-breaker counter either per-model with documented intent, or single shared counter with reset rule stated.
4. Threshold for circuit-breaker becomes one constant in the base, not three.
5. Adding a new camera-threaded feature (e.g., resolution switching, recording mode) costs ~40 LOC instead of ~120.

## Non-Goals

- No changes to AI inference logic (detection, recognition, liveness, head-pose).
- No changes to camera index selection or backend (`cv2.VideoCapture`).
- No changes to PyQt signal types emitted to UI.
- No removal of the legacy `EnrollmentCameraThread` if it has any remaining users — that's a separate question answered in the grilling session (Design Question 3).
- No new threading model. The base inherits from `QThread` exactly as today.

## Design Decisions

_To be filled by grilling session. Five design questions in scope:_

| # | Question | Constraints |
|---|----------|-------------|
| 1 | Base class vs mixin vs composition? | Inheritance tightens coupling; composition is more flexible. Both camera threads use the same camera; both AI workers use the same queue/sentinel — is there a shared concept or two? |
| 2 | Per-model or shared circuit-breaker counter? | ADR-0001 said "shared between liveness and head-pose." Either preserve intent in the new base, or reopen the ADR. |
| 3 | Is `EnrollmentCameraThread` legacy path dead code? | If `EnrollmentAIWorker` has fully replaced it, only 2 consumers need refactoring. |
| 4 | Where does the base live? `ui/camera_thread_base.py`, `core/camera_worker.py`, or new `infrastructure/` package? | Camera threads are UI-threaded; base should match their location unless the new package is justified. |
| 5 | What goes behind the seam vs in the interface? | `run()` is abstract; `submit_task()` concrete shared; `pause()`/`resume()` per-thread (currently in `CameraThread` only). Establish the contract. |

## Implementation

### Files to change

| File | Change |
|------|--------|
| `src/attendance_system/ui/camera_worker_base.py` *(new)* | Define `CameraWorkerBase(QThread)` with: `_retry_read()`, circuit-breaker counter, `queue.Queue(maxsize=1)` + `_SENTINEL`, `submit_task()` numpy-copy helper, `_PAUSE_POLL_INTERVAL_SECONDS` polling, `stop()` signal-disconnect. `run()` is concrete (does the read + submit + drain) and calls abstract `_process_frame(frame)` for the per-thread inference step. |
| `src/attendance_system/ui/camera_thread.py` | Reduce `AIWorker` to override `_process_frame` only. Delete duplicated constants. `pause()`/`resume()` moves to base. |
| `src/attendance_system/ui/enrollment_ai_worker.py` | Same reduction: `EnrollmentAIWorker` overrides `_process_frame` only. Encode the per-model vs shared circuit-breaker decision here (or in the base, depending on Design Q2). |
| `src/attendance_system/ui/enrollment_camera_thread.py` | Either: (a) refactor to inherit from base and implement the legacy capture loop, or (b) delete if confirmed dead code by Design Q3. |
| `tests/unit/test_camera_worker_base.py` *(new)* | Test the shared infrastructure: queue mechanics, sentinel shutdown, circuit-breaker count, retry-with-backoff, `pause()` polling, `stop()` signal disconnect. |
| `tests/unit/test_camera_thread.py` | Update existing tests to use the new base — most queue/sentinel tests are now covered by the base test suite and should be deleted from this file. |
| `tests/unit/test_enrollment_ai_worker.py` | Same: update to consume base; keep only enrollment-specific inference tests. |
| `docs/adr/0001-onnx-circuit-breaker.md` | Update if Design Q2 changes the counter semantics. |

### Touch points by line (reference)

- `camera_thread.py:35-40` — duplicated constants
- `camera_thread.py:65-87` — `submit_task()` + queue setup
- `camera_thread.py:106-171` — `AIWorker.run()` body (will shrink to `_process_frame`)
- `camera_thread.py:173-196` — stop/drain boilerplate
- `camera_thread.py:290-312` — `_retry_read()` (verbatim copy)
- `enrollment_camera_thread.py:125-148` — `_retry_read()` (verbatim copy)
- `enrollment_ai_worker.py:19-20, 48-67, 93-106, 126-141, 157-179` — duplicated patterns

## Testing

### Unit tests to add (in `test_camera_worker_base.py`)

- `test_base_processes_submitted_frame` — `submit_task(frame)` → `_process_frame` called exactly once with the frame.
- `test_base_drains_queue_on_stop` — `stop()` waits for in-flight task to complete before thread exits (existing `test_camera_thread.py:52-268` covers this for one thread; the base test should cover it once for both).
- `test_circuit_breaker_kills_thread_after_threshold_failures` — `_process_frame` raises 30 times → `camera_error` signal emitted + thread exits.
- `test_circuit_breaker_resets_on_success` — 29 failures + 1 success → counter resets to 0.
- `test_circuit_breaker_per_model_vs_shared` — depends on Design Q2 decision.
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
ruff check src/attendance_system/ui/camera_worker_base.py
```

## Related

- Parent plan: [0002 — Architecture Deepening Checklist](0002-architecture-deepening.md)
- ADR-0001: `docs/adr/0001-onnx-circuit-breaker.md` (may be updated)
- `AGENTS.md` "Gotchas" — `QThread` thread-affinity rules, `EnrollmentCameraThread` flips frames (mirror), attendance `CameraThread` does not, `_COOLDOWN_SECONDS = 3.0`, `_AI_FRAME_SKIP = 3`, `_PAUSE_POLL_INTERVAL_SECONDS = 0.05`.
- Branch: `refactor/source-code`.
