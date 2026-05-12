# Implementation Plan: Report and System Configuration Utilities

**Branch**: `006-module-6-module` | **Date**: 2026-04-26 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/006-module-6-module/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

Add local configuration controls for camera selection and threshold tuning, plus read-only export of completed attendance sessions to CSV and XLSX using the existing SQLite-backed attendance data.

## Technical Context

<!--
  ACTION REQUIRED: Replace the content in this section with the technical details
  for the project. The structure here is presented in advisory capacity to guide
  the iteration process.
-->

**Language/Version**: Python 3.11+
**Primary Dependencies**: SQLite3, existing service/repository stack, PyQt5 UI, pytest, csv stdlib, openpyxl for XLSX export
**Storage**: Local SQLite3 database with existing `system_settings`, `sessions`, `attendance_records`, `recognition_events`, and `users` tables
**Testing**: pytest
**Target Platform**: Desktop app on the existing Windows-first classroom environment
**Project Type**: desktop-app
**Performance Goals**: Settings changes should persist immediately; report export should complete within 30 seconds for completed sessions up to 500 rows; the UI should remain responsive while using local data only
**Constraints**: Offline-capable, no raw biometric data in exports, read-only reporting, thresholds must remain within existing pipeline bounds
**Scale/Scope**: Single-user local installation with classroom-sized session reports and per-device camera configuration

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- Attendance Integrity: The design keeps report generation read-only, uses completed-session snapshots, and never creates or edits attendance records.
- Privacy by Design: Exported reports exclude raw face images and embeddings; settings persistence only stores non-biometric configuration values.
- Offline-First Reliability: Camera selection, threshold updates, and report export all operate against local SQLite data without internet dependence.
- Deterministic AI Pipeline: Saved thresholds are read from system settings and applied through the existing liveness/similarity gate before recognition begins.
- Measurable Quality Gates: Validate settings persistence, CSV/XLSX contents, completed-session export gating, and no biometric fields in output files.

## Project Structure

### Documentation (this feature)

```text
specs/006-module-6-module/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)
<!--
  ACTION REQUIRED: Replace the placeholder tree below with the concrete layout
  for this feature. Delete unused options and expand the chosen structure with
  real paths (e.g., apps/admin, packages/something). The delivered plan must
  not include Option labels.
-->

```text
src/
├── models/
├── services/
├── repositories/
├── ui/
└── core/

tests/
├── contract/
├── integration/
└── unit/
```

**Structure Decision**: Single Python desktop project. The feature stays inside the existing `src/` service, repository, model, and UI layers, with validation in `tests/`.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| None | N/A | N/A |
