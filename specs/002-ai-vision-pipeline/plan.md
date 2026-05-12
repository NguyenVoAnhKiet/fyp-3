# Implementation Plan: AI Engine & Vision Pipeline

**Branch**: `002-ai-vision-pipeline` | **Date**: 2026-04-24 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/002-ai-vision-pipeline/spec.md`

## Summary

Build a threaded vision pipeline that reads camera frames, applies face detection, liveness screening, and recognition in the fixed order detect -> liveness -> recognize, then emits normalized events for attendance handling. The design keeps heavy inference off the UI thread, preserves offline operation, and reuses the existing attendance service and SQLite event model.

## Technical Context

**Language/Version**: Python 3.11+  
**Primary Dependencies**: OpenCV for frame capture/preprocessing, local anti-spoof and embedding inference components compatible with MiniFASNet/DeepFace, `threading` and `queue` from the standard library, pytest for validation  
**Storage**: Local SQLite3 with WAL mode and the existing `recognition_events` / `attendance_records` tables  
**Testing**: pytest with unit and integration coverage  
**Target Platform**: Python desktop application on Windows-class classroom machines  
**Project Type**: Desktop app with a background worker and local persistence  
**Performance Goals**: 95% of valid candidates produce a final event within 2 seconds; 95% of sampled UI interactions remain responsive within 300 ms  
**Constraints**: Offline-first processing, deterministic pipeline order, no raw frame persistence in the normal path, one active camera stream per session  
**Scale/Scope**: Single classroom camera, per-session recognition against a local enrollment set, tens of concurrent events per session rather than high-volume throughput

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- Attendance Integrity: The pipeline emits recognition outcomes only after liveness succeeds, and downstream attendance writes still rely on the existing `(session_id, user_id)` uniqueness rule and audited event records.
- Privacy by Design: The pipeline uses transient frame data for inference only; raw face images are not retained by the normal processing path, and the design continues to depend on hashed admin credentials and derived embeddings already in the repo.
- Offline-First Reliability: Frame capture, liveness, recognition, and event emission are all local operations; no network call is required for attendance processing.
- Deterministic AI Pipeline: The processing order is fixed as detect -> liveness -> recognize, and session threshold snapshots are read from the existing session model so the same session uses one threshold set.
- Measurable Quality Gates: The plan carries latency, UI responsiveness, spoof rejection, and event contract checks into the test matrix.

## Project Structure

### Documentation (this feature)

```text
specs/002-ai-vision-pipeline/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── vision-event-contract.md
└── tasks.md
```

### Source Code (repository root)

```text
src/
├── core/
├── models/
├── repositories/
├── services/
└── utils/

tests/
├── integration/
└── unit/
```

**Structure Decision**: Keep the feature inside the existing single-project layout. The implementation will add vision-pipeline service code under `src/services/`, runtime/event dataclasses in `src/models/`, and unit/integration coverage under `tests/unit/` and `tests/integration/` without introducing a new top-level application boundary.

## Complexity Tracking

No constitution violations identified. This plan stays within the existing single-project desktop architecture, so no complexity justification is required.

