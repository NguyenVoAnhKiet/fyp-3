# Implementation Plan: Admin User and Biometric Enrollment

**Branch**: `003-admin-biometric-enrollment` | **Date**: 2026-04-25 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/003-admin-biometric-enrollment/spec.md`

## Summary

Build an administrator-only biometric enrollment flow that creates or selects a user profile, guides capture of valid face samples, stores one derived biometric reference per user, deletes raw image data immediately after extraction or cancellation, and preserves an audit trail for every enrollment attempt.

## Technical Context

**Language/Version**: Python 3.11+  
**Primary Dependencies**: Existing SQLite3 repository/service stack, bcrypt for admin credential hashing, pytest for validation, and the current desktop UI layer (PyQt5 or Tkinter) for any capture-driven screens  
**Storage**: Local SQLite database with the existing `users` and `face_references` tables plus enrollment session/audit tables introduced for this feature  
**Testing**: pytest with unit and integration coverage  
**Target Platform**: Windows desktop  
**Project Type**: desktop-app  
**Performance Goals**: Standard enrollment attempts should complete in under 3 minutes under normal operating conditions; raw image cleanup must occur immediately after session completion, cancellation, or failure  
**Constraints**: Offline-capable, privacy-preserving, single-machine operation, one active enrollment session per target user, deterministic sample acceptance and cleanup behavior  
**Scale/Scope**: Single classroom workstation with a modest enrolled population, not a distributed or multi-site enrollment system

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- Attendance Integrity: Enrollment will create at most one derived biometric reference per user and will block parallel active enrollment sessions for the same target user to avoid ambiguous downstream recognition state.
- Privacy by Design: Raw enrollment images are transient only; the implementation will delete them immediately after feature extraction or session termination and retain only derived biometric data plus required audit metadata.
- Offline-First Reliability: All enrollment, persistence, cancellation, and auditing actions operate locally without network access.
- Deterministic AI Pipeline: Enrollment follows a fixed capture -> quality check -> feature extraction -> aggregate reference -> persist flow with session-scoped acceptance rules.
- Measurable Quality Gates: The feature will be validated by completion-time checks, duplicate-session prevention checks, and raw-image deletion verification across completed, cancelled, and failed sessions.

## Project Structure

### Documentation (this feature)

```text
specs/003-admin-biometric-enrollment/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
└── checklists/
    └── requirements.md
```

### Source Code (repository root)

```text
src/
├── core/
│   └── schema.py
├── models/
│   └── entities.py
├── repositories/
│   ├── face_reference_repository.py
│   ├── user_repository.py
│   └── enrollment_*.py
└── services/
    ├── enrollment_service.py
    └── enrollment_*.py

tests/
├── integration/
└── unit/
```

**Structure Decision**: Keep the feature inside the existing single-project Python desktop layout. Reuse the current `users` and `face_references` foundations, then add enrollment-specific repository and service code plus focused tests rather than introducing a new top-level application boundary.

## Complexity Tracking

No constitution violations require justification at this stage.