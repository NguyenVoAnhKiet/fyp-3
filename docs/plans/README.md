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

_No active plans — see [Archive](#archive) for completed work._

## Archive

Browse `docs/plans/archive/` for completed plans. Date prefix sorts chronologically.

| ID | Title | Done on | Branch |
|----|-------|---------|--------|
| 0001 | [Attendance Freeze Feedback](archive/2026-06-02-0001-attendance-freeze-feedback.md) | 2026-06-02 | `feature/attendance-freeze-feedback` |
