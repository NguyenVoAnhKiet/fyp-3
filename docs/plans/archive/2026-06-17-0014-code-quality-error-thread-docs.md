# Plan 0014: Code Quality — Error Handling, Dynamic Attributes, Docstrings

## Status

**Done** (2026-06-17)

## Context

Codebase audit found silent exception swallowing, a dynamic attribute hack, and inconsistent docstrings. This plan fixes HIGH-priority items 2 and 4, plus MEDIUM-priority item 8.

**Oracle decision: DROP `threading.Event` refactor.** The `_running` bool flag is atomic under CPython GIL, standard Qt pattern, and YAGNI for this project. Instead, add a comment documenting the thread-safety rationale.

## Goals

1. Replace 5 silent `except Exception` blocks with proper logging.
2. Replace dynamic `_value_label` attribute on QFrame with proper QLabel references.
3. Add/enhance docstrings on 4 key public classes.
4. Add thread-safety comment to `_running` flag (no code change).

## Non-Goals

- No `threading.Event` refactor (YAGNI — bool is fine under GIL).
- No behavioral changes.
- No UI/UX changes.
- No new tests.

## Design Decisions

| # | Question | Final Answer |
|---|----------|--------------|
| 1 | How to handle silent `except Exception` blocks? | **Add `logger.warning(...)` or `logger.debug(...)` in each block.** Don't change exception scope — just make errors visible. |
| 2 | How to replace dynamic `_value_label`? | **Refactor `_make_stat_card` to return `(QFrame, QLabel)` tuple.** Store label refs directly as `self._stat_success_label` etc. Eliminates `type: ignore`. |
| 3 | Which classes need enhanced docstrings? | `AttendanceService`, `CameraThreadBase`, `AIWorkerBase`, `SettingsWidget` — the classes a defense committee would examine. |
| 4 | How to document thread safety? | Add comment: `# Written from main thread via stop(), read from worker thread. Atomic under CPython GIL.` No code change. |

## Implementation

### Files to change

| File | Change |
|------|--------|
| `src/attendance_system/ui/user_mode_view.py:524,624,665,717` | Add `logger.warning(...)` in each `except Exception` block |
| `src/attendance_system/services/authentication_service.py:38` | Add `logger.warning("bcrypt check failed: %s", e)` before `return False` |
| `src/attendance_system/ui/user_mode_view.py:296-304,354,386-389` | Refactor `_make_stat_card` → return `(QFrame, QLabel)`. Store refs as `self._stat_success_label` etc. Update `_refresh_stats_display`. |
| `src/attendance_system/ui/camera_worker_base.py:83` | Add comment documenting GIL-based thread safety for `_running` bool |
| `src/attendance_system/services/attendance_service.py` | Add class docstring explaining service layer role, session lifecycle, error semantics |
| `src/attendance_system/ui/camera_worker_base.py` | Add class docstrings for `CameraThreadBase` and `AIWorkerBase` |
| `src/attendance_system/ui/settings_widget.py` | Add class docstring for `SettingsWidget` |

### Task Breakdown

| Task | Description | Files | Sub-agent |
|------|-------------|-------|-----------|
| 1 | Add logging to 5 silent except blocks | `user_mode_view.py`, `authentication_service.py` | `@fixer` |
| 2 | Refactor `_make_stat_card` to eliminate dynamic attribute | `user_mode_view.py` | `@fixer` |
| 3 | Add/enhance docstrings on 4 key classes | `attendance_service.py`, `camera_worker_base.py`, `settings_widget.py` | `@fixer` |
| 4 | Add thread-safety comment to `_running` flag | `camera_worker_base.py` | `@fixer` |

### Phase 1 — Parallel (all independent)

Tasks 1-4 touch different line ranges in different files. All can run in parallel.

### Phase 2 — Verify (orchestrator)

```bash
python -m pytest tests/ -v
grep -n "type: ignore" src/attendance_system/ui/user_mode_view.py  # should be empty
```

## Testing

No new tests. 324/324 tests must pass. No `type: ignore` comments remaining.
