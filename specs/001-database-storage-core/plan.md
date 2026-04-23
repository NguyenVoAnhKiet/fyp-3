# Implementation Plan: Database & Storage Core

**Branch**: `001-database-storage-core` | **Date**: 2026-04-24 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-database-storage-core/spec.md`

## Summary

Build the local persistence core for the attendance system in SQLite, covering user accounts, face references, attendance sessions, recognition events, and system settings. The design emphasizes duplicate-prevention, auditable attendance history, privacy-preserving biometric storage, and offline-safe operation.

## Technical Context

**Language/Version**: Python 3.11+  
**Primary Dependencies**: SQLite3, PyQt5 or Tkinter at the application layer, bcrypt for credential hashing, pytest for validation  
**Storage**: Local SQLite database file  
**Testing**: pytest with unit and integration coverage  
**Target Platform**: Windows desktop  
**Project Type**: desktop-app  
**Performance Goals**: Core storage operations should complete within 1 second for normal CRUD paths; session writes must remain responsive enough to avoid blocking the live UI  
**Constraints**: Offline-capable, privacy-preserving biometric storage, immutable committed attendance history, deterministic duplicate prevention  
**Scale/Scope**: Single-machine classroom deployment with many sessions and enrolled users, but no distributed synchronization

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- Attendance Integrity: Duplicate attendance prevention will be enforced with session/user uniqueness rules and transactional writes so a second success cannot be recorded for the same learner in the same session window.
- Privacy by Design: Raw face images are out of scope for persisted storage; only derived embeddings and required metadata will be stored, and admin credentials will be hashed before persistence.
- Offline-First Reliability: All reads, writes, and exports for this module operate on the local SQLite store and do not require network access.
- Deterministic AI Pipeline: Session records will capture the configuration values in effect when attendance decisions are recorded, allowing detect -> liveness -> recognize outcomes to be explained later.
- Measurable Quality Gates: The plan will validate initialization, restart persistence, duplicate-prevention, privacy retention, and CRUD latency with focused automated tests.

## Project Structure

### Documentation (this feature)

```text
specs/001-database-storage-core/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
└── tasks.md
```

### Source Code (repository root)

```text
src/
├── core/
├── models/
├── repositories/
└── services/

tests/
├── integration/
└── unit/
```

**Structure Decision**: Use a single Python desktop application structure with a local `src/` package for storage, model, repository, and service layers, plus `tests/` split into unit and integration coverage. The repository currently contains documentation only, so these directories will be introduced during implementation.

## Complexity Tracking

No constitution violations require justification at this stage.
