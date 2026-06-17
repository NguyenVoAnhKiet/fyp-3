# Plan 0013: Quick Wins — Test Fix, Imports, Types

## Status

**Draft** (revised after Oracle review 2026-06-17)

## Context

Codebase audit for thesis defense found 10 issues. This plan fixes the only functional bug (failing test) plus low-risk polish items. All changes are surgical and independently verifiable.

## Goals

1. Fix failing test so full suite passes (324/324).
2. Fix import ordering in `camera_worker_base.py`.
3. Add missing return type hints to `attendance_service.py`.
4. Extract one magic number in `enrollment_widget.py`.

## Non-Goals

- No error handling changes (Plan 0014).
- No thread safety changes (Plan 0014).
- No new features or behavioral changes.
- No README (Plan 0015).

## Design Decisions

| # | Question | Final Answer |
|---|----------|--------------|
| 1 | How to fix the failing test? | **Update assertion to `VideoCapture(0, cv2.CAP_DSHOW)`.** Implementation is correct (DirectShow avoids Windows camera blocking); test expectation is outdated. |
| 2 | Where to put magic number constants? | **Module-level in each file**, following existing pattern. But reuse existing `DEFAULT_ATTENDANCE_FREEZE_SECONDS` from `defaults.py` instead of duplicating. |
| 3 | Type hints scope? | **Return types only.** Don't restructure signatures. |

## Implementation

### Files to change

| File | Change |
|------|--------|
| `tests/unit/test_camera_thread.py:285` | `assert_called_with(camera_thread._camera_index)` → `assert_called_with(camera_thread._camera_index, cv2.CAP_DSHOW)` |
| `src/attendance_system/ui/camera_worker_base.py:19` | Move `from pathlib import Path` above `import logging` (line 9) |
| `src/attendance_system/services/attendance_service.py:147-166` | Add return types: `get_sessions() -> list[dict]`, `get_session_details() -> dict | None`, `get_session_records() -> list[dict]`, `get_unique_classes() -> list[str]`, `get_unique_subjects() -> list[str]` |
| `src/attendance_system/ui/user_mode_view.py:440` | Replace `int(seconds_str) if seconds_str is not None else 4` with `import` of `DEFAULT_ATTENDANCE_FREEZE_SECONDS` from `attendance_system.core.defaults` and use it as fallback |
| `src/attendance_system/ui/enrollment_widget.py:498` | Extract `1500` → `_SUCCESS_EFFECT_DELAY_MS = 1500` at module top; use in `QTimer.singleShot(_SUCCESS_EFFECT_DELAY_MS, ...)` |

### Task Breakdown

| Task | Description | File | Sub-agent |
|------|-------------|------|-----------|
| 1 | Fix failing test assertion | `tests/unit/test_camera_thread.py` | `@fixer` |
| 2 | Fix import ordering | `src/attendance_system/ui/camera_worker_base.py` | `@fixer` |
| 3 | Add return type hints | `src/attendance_system/services/attendance_service.py` | `@fixer` |
| 4 | Import existing constant + extract one magic number | `user_mode_view.py`, `enrollment_widget.py` | `@fixer` |

### Phase 1 — Parallel fixes (all independent)

Tasks 1-4 touch different files. All 4 can run in parallel.

### Phase 2 — Verify (orchestrator)

```bash
python -m pytest tests/unit/test_camera_thread.py::test_camera_thread_retry_read_releases_old_cap -v
python -m pytest tests/ -v
```

## Testing

No new tests required. 324/324 tests must pass after changes.
