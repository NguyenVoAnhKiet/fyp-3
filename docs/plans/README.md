# Feature Plans

This folder tracks in-flight and archived feature plans — work-in-progress designs that have not yet been implemented (or have just been completed and await archival).

## Conventions

- **Location**: All plans live in `docs/plans/active/` while in flight.
- **Naming**: `<4-digit-id>-<slug>.md` (e.g. `0001-attendance-freeze-feedback.md`). The 4-digit prefix matches the ADR convention in `docs/adr/` and keeps files sortable by creation order. The slug is lowercase, kebab-case, brief but descriptive.
- **Lifecycle**:
  1. **Draft** — Plan created, design being refined.
  2. **In Progress** — Implementation work has started on a feature branch.
  3. **Done** — Code merged to `main`. Move the file to `docs/plans/archive/` with a date prefix: `git mv docs/plans/active/0001-foo.md docs/plans/archive/2026-06-01-0001-foo.md`.
- **Required sections** (Standard plan template):
  - `## Status` — `Draft` / `In Progress` / `Done`
  - `## Context` — Why are we doing this? What problem does it solve?
  - `## Goals` — Concrete success criteria.
  - `## Non-Goals` — Explicit out-of-scope items (anti-scope-creep).
  - `## Design Decisions` — Table of decision points, options considered, and final answers (capture the "why").
  - `## Implementation` — File change list with brief description per change.
  - `## Testing` — Unit tests to add + manual smoke checklist.

## Active Plans

| ID | Title | Status | Branch |
|----|-------|--------|--------|
| 0002 | [Architecture Deepening — Checklist](active/0002-architecture-deepening.md) | In progress (3/5 done) | `refactor/source-code` |
| 0005 | [Centralize Configuration Resolution](active/0005-system-config-resolver.md) | Draft (candidate #3) | `refactor/source-code` |
| 0006 | [Enforce Cache Invalidation](active/0006-caching-face-repository.md) | Draft (candidate #4) | `refactor/source-code` |

## Archive

Browse `docs/plans/archive/` for completed plans. Date prefix sorts chronologically.

| ID | Title | Done on | Branch |
|----|-------|---------|--------|
| 0001 | [Attendance Freeze Feedback](archive/2026-06-02-0001-attendance-freeze-feedback.md) | 2026-06-02 | `feature/attendance-freeze-feedback` |
| 0004 | [Introduce `AIPipeline` Orchestrator](archive/2026-06-03-0004-ai-pipeline-orchestrator.md) — design doc | 2026-06-03 | `refactor/source-code` |
| 0004 | [Introduce `AIPipeline` Orchestrator — implement](archive/2026-06-03-0004-ai-pipeline-orchestrator-implement.md) — impl plan | 2026-06-03 | `refactor/source-code` |
| 0007 | [Extract `FacePreprocessor`](archive/2026-06-03-0007-face-preprocessor.md) | 2026-06-03 | `refactor/source-code` |
| 0003 | [Extract `CameraWorkerBase`](archive/2026-06-04-0003-camera-worker-base.md) | 2026-06-04 | `refactor/source-code` |
