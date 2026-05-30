## Context

The attendance face-recognition pipeline consists of 7 layers: YuNet face detection → MiniFASNet liveness (anti-spoofing) → LivenessTracker (temporal smoothing) → SFace recognition → CameraThread/AIWorker (pipeline orchestration) → AttendanceService (DB recording) → UserModeView (UI integration). A health audit has already found 3 bugs (closed-session writes, empty CSV export, duplicate-path inefficiency) and 2 design flaws (silent migration failures, missing callback tests). These were fixed, but a systematic review of the remaining code is needed to catch additional issues.

The system runs entirely offline (Python 3.12, PyQt5, ONNX Runtime, SQLite/WAL). All AI models run locally on CPU. The codebase has 142 passing tests and zero FIXME/TODO comments.

## Goals / Non-Goals

**Goals:**
- Systematically review each layer of the attendance pipeline for correctness, edge cases, thread safety, and performance
- For each layer, produce a checklist of verified items and any bugs found
- Create test specs to cover identified gaps (embedding extraction, cache invalidation, camera recovery, concurrent writes, special characters in export)
- Define implementation tasks for any bugs discovered during review
- End with a verified, documented baseline for the attendance feature

**Non-Goals:**
- No new features or capabilities
- No API changes or interface modifications
- No performance optimization beyond what is uncovered during review
- No model re-training or hyperparameter tuning

## Decisions

| Decision | Choice | Rationale | Alternatives Considered |
|----------|--------|-----------|------------------------|
| Review order | Risk-priority order (highest risk first) | AttendanceService has data integrity implications — review it first | Alphabetical or layer order |
| Review method per component | Code review + unit test + manual test (varies by component) | Different risks need different detection methods | One-size-fits-all approach |
| Test specs focused on gaps | Only write tests for uncovered scenarios | Existing tests (142 passing) already cover happy paths | Full regression test rewrite |
| No integration test harness for full pipeline | Too expensive — requires real camera + ONNX models | Unit tests with mock models provide sufficient coverage at lower cost | Build a full integration test rig |
| Manual camera test deferred | Relies on hardware setup | Code review + unit tests catch logic bugs; manual tests catch accuracy issues | N/A — manual test is separate activity |

## Risks / Trade-offs

| Risk | Mitigation |
|------|-----------|
| Code review misses runtime-only bugs (e.g., race conditions) | Unit tests specifically target threading scenarios; cooldown and circuit-breaker already tested |
| Review scope is large (7 layers) | Prioritized by risk; stop at P0/P1 first |
| No real camera in CI → some bugs only found during manual test | Document manual test scenarios clearly so they can be run on-device |
| Liveness model accuracy cannot be tested in unit tests (no real ONNX model in CI) | Use mock ONNX sessions; test preprocessing and edge-case handling only |
