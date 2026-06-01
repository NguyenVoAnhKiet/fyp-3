## Why

The attendance feature (face detection → liveness → recognition → DB recording) is the core business logic of this application, but it has never undergone a systematic end-to-end review. A recent health audit found 3 confirmed bugs (closed-session writes, empty CSV export, duplicate-path inefficiency) plus 2 design flaws (silent migration failures, missing callback tests), indicating the codebase has accumulated risk. A structured review is needed to find remaining issues before they cause data corruption, security bypasses, or production outages.

## What Changes

- Create a comprehensive **review plan** (proposal + design + test specs + tasks) covering the full attendance pipeline
- Review each component systematically: YuNet detection → MiniFASNet liveness → LivenessTracker smoothing → SFace recognition → AttendanceService recording → UI integration → export
- For each component: verify correctness, edge-case handling, thread safety, and performance
- Write targeted **test specs** to cover identified gaps (embedding extraction, cache invalidation, full pipeline integration, camera recovery, concurrent access)
- Define implementation tasks to fix any bugs found during review

## Capabilities

### New Capabilities
- `attendance-pipeline-review`:
  - Systematic review of the 7-layer attendance pipeline
  - Test specs covering untested paths (embedding extraction, cache invalidation, camera recovery, concurrent writes)
  - Implementation tasks for any bugs found

### Modified Capabilities
- *(None — this is a new review activity, not changing existing requirements)*

## Impact

- **Code reviewed**: `camera_thread.py`, `ai_pipeline.py`, `attendance_service.py`, `liveness_tracker.py`, `face_utils.py`, `user_mode_view.py`, `schema.py`, `exceptions.py`
- **Tests created/updated**: New test specs → new test files under `tests/unit/` and `tests/integration/`
- **No API changes**: This review does not change existing interfaces
- **No dependency changes**
