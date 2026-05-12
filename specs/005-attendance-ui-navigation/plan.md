# Implementation Plan: Attendance UI Navigation Architecture

**Branch**: `005-attendance-ui-navigation` | **Date**: 2026-04-26 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/005-attendance-ui-navigation/spec.md`

## Summary

Deliver a desktop UI shell for attendance operations that manages deterministic state transitions (IDLE <-> LIVE), renders smooth camera preview at 24+ FPS, and supports keyboard-driven controls (`S`, `E`, `Q`) with consistent color-coded visual outcomes.

## Technical Context

**Language/Version**: Python 3.11+  
**Primary Dependencies**: PyQt5 for desktop UI shell and event loop, OpenCV frame source integration from existing vision pipeline, existing `src/services` attendance and vision adapters, `threading` and `queue` for non-blocking frame and event handoff  
**Storage**: Local SQLite3 (WAL) reused through existing repositories; no new persistent store for this UI feature  
**Testing**: pytest (unit + integration + contract), manual UX smoke validation checklist for frame-rate and hotkey behavior  
**Target Platform**: Windows desktop classroom workstation (offline-capable)
**Project Type**: single-project Python desktop application module  
**Performance Goals**: Maintain displayed live preview >=24 FPS for at least 95% of sampled intervals in a 10-minute session; hotkey response <=200ms for 99% of valid commands  
**Constraints**: Must remain responsive during continuous video rendering, must not alter detect -> liveness -> recognize decision semantics, must operate without internet, must avoid storing raw biometric imagery in UI layer  
**Scale/Scope**: One active attendance session per workstation, one live camera stream, tens to hundreds of attendees per session

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- Attendance Integrity: UI state machine constrains start/end actions to valid contexts and surfaces outcome state clearly, reducing operator-driven duplicate or invalid attendance operations.
- Privacy by Design: UI consumes derived outcomes and frame previews transiently; no raw frame persistence, no credential handling changes, and no broader role scope changes are introduced.
- Offline-First Reliability: UI controls and live feedback depend on local modules only and remain available without network connectivity.
- Deterministic AI Pipeline: UI is consumer-only for finalized pipeline outputs and does not mutate liveness/similarity decisions or threshold ordering.
- Measurable Quality Gates: Plan includes quantifiable checks for FPS stability, command latency, state transition correctness, and consistent visual mapping.

## Project Structure

### Documentation (this feature)

```text
specs/005-attendance-ui-navigation/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── ui-attendance-interaction-contract.md
└── tasks.md
```

### Source Code (repository root)

```text
src/
├── core/
├── models/
├── repositories/
└── services/
  ├── attendance_service.py
  ├── vision_event_adapter.py
  └── vision_pipeline_service.py

tests/
├── contract/
├── integration/
└── unit/
```

**Structure Decision**: Keep the current single-project Python desktop structure and add UI architecture behavior without introducing a separate frontend repository.

## Post-Design Constitution Check

- Attendance Integrity: PASS. Data model and contract define deterministic state transitions and command validity to prevent operator confusion that could compromise attendance integrity.
- Privacy by Design: PASS. Artifacts explicitly require transient frame rendering and no raw image persistence in UI workflows.
- Offline-First Reliability: PASS. Quickstart validations execute fully with local camera/input and local services only.
- Deterministic AI Pipeline: PASS. Contracts define UI as read-only consumer of pipeline outcomes, preserving detect -> liveness -> recognize ordering.
- Measurable Quality Gates: PASS. Research and quickstart include measurable thresholds for FPS, response latency, state consistency, and feedback mapping.

## Complexity Tracking

No constitution violations require justification at this stage.
