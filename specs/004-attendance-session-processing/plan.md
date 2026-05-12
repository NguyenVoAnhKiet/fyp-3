# Implementation Plan: Attendance Session Processing

**Branch**: `004-attendance-session-processing` | **Date**: 2026-04-26 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/004-attendance-session-processing/spec.md`

## Summary

Implement lecturer-driven attendance session lifecycle handling and real-time AI event processing so the system can start ACTIVE sessions, persist successful attendance once per student per session, and log spoof outcomes as warnings without internet dependency.

## Technical Context

**Language/Version**: Python 3.11+  
**Primary Dependencies**: Existing service and repository stack under `src/services` and `src/repositories`, SQLite3 persistence layer, threaded vision pipeline event flow, pytest for validation  
**Storage**: Local SQLite3 with WAL mode using existing `attendance_records`, `recognition_events`, and `sessions` persistence boundaries  
**Testing**: pytest (unit + integration + contract)  
**Target Platform**: Windows desktop (offline classroom workstation)
**Project Type**: desktop-app module stack  
**Performance Goals**: Event-to-history persistence within 2 seconds for normal classroom load; zero duplicate successful attendance entries per student per session  
**Constraints**: Offline-capable, deterministic consume-order behavior, no raw biometric image persistence, session-gated event intake only while ACTIVE  
**Scale/Scope**: Single workstation operation for one active class session at a time, typically tens to hundreds of students per session

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- Attendance Integrity: Design uses session-scoped duplicate checks keyed by `(session_id, user_id, success)` so only the first successful attendance is persisted and every outcome remains auditable.
- Privacy by Design: Module consumes derived AI outcomes only and persists status/identity/timestamp metadata; no raw face images are introduced by this feature.
- Offline-First Reliability: Session creation, event intake, duplicate prevention, and history persistence use only local SQLite operations and remain available without network access.
- Deterministic AI Pipeline: Attendance processing accepts only finalized pipeline outputs after detect -> liveness -> recognize; event contract defines allowed outcome mapping.
- Measurable Quality Gates: Validation combines unit and integration checks for duplicate blocking, spoof-warning persistence, malformed-event rejection, and event-to-persistence latency targets.

## Project Structure

### Documentation (this feature)

```text
specs/004-attendance-session-processing/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── attendance-session-event-contract.md
└── tasks.md
```

### Source Code (repository root)

```text
src/
├── core/
├── models/
│   └── entities.py
├── repositories/
│   ├── attendance_repository.py
│   ├── recognition_event_repository.py
│   └── session_repository.py
└── services/
  ├── attendance_service.py
  ├── vision_event_adapter.py
  └── vision_pipeline_service.py

tests/
├── contract/
│   └── test_vision_event_contract.py
├── integration/
│   ├── test_attendance_audit.py
│   ├── test_attendance_history.py
│   ├── test_offline_behavior.py
│   └── test_vision_pipeline_flow.py
└── unit/
  ├── test_attendance_service.py
  ├── test_vision_event_adapter.py
  └── test_vision_pipeline_order.py
```

**Structure Decision**: Keep the existing single-project Python desktop module layout and implement this feature by extending attendance/session services plus repository behavior and targeted tests.

## Post-Design Constitution Check

- Attendance Integrity: PASS. Data model and contract preserve single-success attendance semantics per student/session and audit all outcomes.
- Privacy by Design: PASS. No raw image persistence introduced; only event metadata and attendance outcomes are specified.
- Offline-First Reliability: PASS. Quickstart validation and requirements assume local-only operation for session and history workflows.
- Deterministic AI Pipeline: PASS. Contract requires finalized outcome payloads with deterministic mapping and validation rules.
- Measurable Quality Gates: PASS. Research and quickstart define measurable timing, duplicate-prevention, and spoof-traceability checks.

## Complexity Tracking

No constitution violations require justification at this stage.
