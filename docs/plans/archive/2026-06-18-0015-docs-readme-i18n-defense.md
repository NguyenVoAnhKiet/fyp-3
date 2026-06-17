# Plan 0015: Documentation — README, i18n Notes, Defense Prep

## Status

**Done** (2026-06-18)

## Context

No root `README.md` exists (noted in `codemap.md:38`). For thesis defense, the README is the first thing the committee sees. This plan creates a minimal README and adds documentation notes.

**Oracle recommendation: Keep README to ~50 lines max.** Committee reads the report, not the README. Link to `codemap.md` for structure details.

## Goals

1. Create a minimal root `README.md` (~50 lines).
2. Document i18n limitation in report Chapter 5.
3. Update `PROJECT_STATUS.md` with audit plan status.

## Non-Goals

- No code changes.
- No i18n implementation.
- No comprehensive documentation overhaul.

## Implementation

### Files to change

| File | Change |
|------|--------|
| `README.md` (new) | ~50 lines: title, 1-paragraph overview, install/run commands, link to codemap, known limitations |
| `docs/project-report/chuong-5.md:34-38` | Add note under 5.2.2 about hardcoded Vietnamese UI strings |
| `PROJECT_STATUS.md:424-441` | Add "Code Quality" subsection noting plans 0013-0015 |

### Task Breakdown

| Task | Description | File | Sub-agent |
|------|-------------|------|-----------|
| 1 | Create minimal README.md | `README.md` | `@fixer` |
| 2 | Add i18n note to report | `docs/project-report/chuong-5.md` | `@fixer` |
| 3 | Update PROJECT_STATUS.md | `PROJECT_STATUS.md` | `@fixer` |

### Phase 1 — Parallel (all independent)

All 3 tasks touch different files.

### Phase 2 — Verify (orchestrator)

```bash
cat README.md  # exists, ~50 lines
grep -c "i18n\|hardcoded" docs/project-report/chuong-5.md  # > 0
grep "0013" PROJECT_STATUS.md  # plan references exist
```

## Testing

No tests. Documentation-only.
