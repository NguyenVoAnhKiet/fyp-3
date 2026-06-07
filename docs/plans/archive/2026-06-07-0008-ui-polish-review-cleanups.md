# Plan 0008: Address code-review findings for `feat/ui-polish`

## Status

**Done** — implemented 2026-06-07 on branch `feat/ui-polish` (4 commits: `c36555b` feature, `fd2f5c5` review-fixup, `32d66f4` docs context, `311ad0f` AGENTS.md sync). All 4 critical issues fixed; `@oracle` review returned LGTM; 280 tests pass (250 unit + 30 integration); `ruff check src/ --select F` clean. Branch is merge-ready. Moved to [`archive/2026-06-07-0008-ui-polish-review-cleanups.md`](2026-06-07-0008-ui-polish-review-cleanups.md) on completion.

## Context

`feat/ui-polish` (commit `c36555b`) bundles three independent UX improvements:

1. **Timezone setting in Admin UI** — new `QComboBox` with 13 curated timezones, immediate apply via `pyqtSignal(str)`, `time_utils` exposes `timezone_signals`.
2. **Export Report button fix** — removed `setStyleSheet` override + manual `clicked → menu.exec_()` pattern.
3. **Stale camera frame cleanup** — `user_mode_view._start_session` and `_end_session` now clear the `QLabel` pixmap.

A review by `@oracle` (2026-06-07) returned **Approve with minor changes** with 4 critical issues that should be addressed before the branch is merged to `main`. Without these fixes the code is correct but carries avoidable code smells, duplicated logic, and over-broad exception handling that complicates future maintenance.

The 250 unit + 30 integration tests still pass; the 4 issues are quality issues, not functional bugs.

## Goals

1. Eliminate the dual-name (`_signals` / `timezone_signals`) singleton in `time_utils` so the public API has one obvious name.
2. Extract the duplicated camera-preview-reset logic in `user_mode_view._start_session` and `_end_session` into a single private helper.
3. Move `format_tz_label` from `settings_widget.py` to `time_utils.py` so pure timezone-formatting logic lives next to other timezone utilities (and can reuse the existing `_load_zoneinfo()` lazy loader).
4. Narrow the exception handling in `SettingsResolver._resolve_timezone` from `except (ZoneInfoNotFoundError, Exception)` to `except ZoneInfoNotFoundError` only.

## Non-Goals

- No new features, no new settings, no new tests beyond what's needed to re-verify existing behavior.
- No change to the timezone UX, dropdown list, default value, or signal payload contract.
- No change to the export button or camera-clear behavior — only their implementation structure.
- No rename of the public `timezone_signals` symbol; the existing public name stays.
- No architectural refactor (e.g., splitting `time_utils.py` to remove its PyQt5 dependency). The Oracle suggestion to move the QObject into a dedicated `signals.py` is **deferred** — out of scope for this plan.

## Design Decisions

| # | Question | Final Answer |
|---|----------|--------------|
| 1 | How to resolve the dual name (`_signals` / `timezone_signals`)? | **Drop the `_signals` private name; keep only `timezone_signals` as the module-level singleton.** The `_TimezoneSignals` class name stays (underscore = private to the module). External consumers (`user_mode_view.py`, `attendance_history_widget.py`) update their imports to use the public name directly instead of the `as timezone_signals` alias. |
| 2 | Where should the new `_reset_camera_preview` helper live? | **Private method on `UserModeView` (`self._reset_camera_preview()`).** It uses `self._camera_label`, so a free function or static method would be artificial. Two call sites collapse into one. The placeholder text `[ Đang khởi động camera… ]` becomes a single source of truth. |
| 3 | Should `format_tz_label` be moved verbatim, or refactored on the way? | **Moved verbatim into `time_utils.py`**, replacing the inline `from zoneinfo import ZoneInfo` with a call to the existing `_load_zoneinfo()` helper so the lazy-load pattern is consistent. Tests of `format_tz_label` behavior (via the settings widget round-trip) already cover the move. |
| 4 | How narrow should the exception catch in `_resolve_timezone` be? | **`except ZoneInfoNotFoundError` only.** `ZoneInfo` raises `ZoneInfoNotFoundError` (subclass of `KeyError`) for unknown IANA names on Python 3.9+. `KeyError` is also accepted for compatibility with stdlib implementations that raise plain `KeyError`. The current `except Exception` swallows real bugs (e.g., a `None` argument that bypasses the truthy check). |
| 5 | Should this be one commit or four? | **One commit.** All four fixes are review-driven cleanups on the same `feat/ui-polish` branch. The original commit `c36555b` stays as the "feature commit" and this becomes the "review followup commit" — clean history. |

### Alternative considered but rejected

- **Four separate commits**: rejected because the four issues are interdependent cosmetic fixes from the same review, and splitting them complicates `git bisect` for negligible benefit. One review followup commit is the conventional pattern.

## Implementation

### Files to change

| File | Change |
|------|--------|
| `src/attendance_system/utils/time_utils.py` | (a) Remove the `_signals = _TimezoneSignals()` and `timezone_signals = _signals` lines (currently lines 28-29); replace with a single `timezone_signals = _TimezoneSignals()` declaration. (b) Update the `set_timezone_config` body to emit via `timezone_signals.timezone_changed.emit(...)` (currently line 75 uses `_signals`). (c) Add `format_tz_label(name: str) -> str` helper, reusing `_load_zoneinfo()` instead of an inline `from zoneinfo import ZoneInfo`. |
| `src/attendance_system/ui/settings_widget.py` | (a) Remove the local `format_tz_label` function (currently lines 72-86). (b) Remove the inline `from zoneinfo import ZoneInfo`. (c) Import `format_tz_label` from `attendance_system.utils.time_utils` at the top of the file. |
| `src/attendance_system/ui/user_mode_view.py` | (a) Add a private method `_reset_camera_preview(self) -> None` containing the `self._camera_label.clear()` + `self._camera_label.setText("[ Đang khởi động camera… ]")` pair. (b) Replace the duplicated two-line block in `_start_session` (currently lines 527-528) and `_end_session` (currently lines 571-572) with `self._reset_camera_preview()`. (c) Update the `timezone_signals` import (currently line 62: `_signals as timezone_signals`) to import the public name directly. |
| `src/attendance_system/ui/attendance_history_widget.py` | (a) Update the `timezone_signals` import (currently line 29) to import the public name directly (already does — the change is just dropping the `as timezone_signals` alias style for consistency, no behavior change). |
| `src/attendance_system/core/config.py` | In `_resolve_timezone` (currently lines 408-426), replace `except (ZoneInfoNotFoundError, Exception):` (line 424) with `except ZoneInfoNotFoundError:`. (The redundant `Exception` is redundant because `ZoneInfoNotFoundError` is the documented exception; `KeyError` and `OSError` are not raised by `ZoneInfo(...)` for invalid names on Python 3.9+.) |

### Touch points by line (reference)

- `src/attendance_system/utils/time_utils.py:28-29, 75`
- `src/attendance_system/ui/settings_widget.py:72-86`
- `src/attendance_system/ui/user_mode_view.py:62, 527-528, 571-572`
- `src/attendance_system/ui/attendance_history_widget.py:29` (no behavior change, import style only)
- `src/attendance_system/core/config.py:424`

### Estimated change size

- 5 files touched, ~15-20 net line changes (mostly deletions, since `_signals` and the local `format_tz_label` and the duplicated camera-clear pair are removed).

## Task Breakdown & Sub-agent Assignment

The 4 fixes are split into 5 bounded implementation tasks for `@fixer` sub-agents, then verified and committed by the orchestrator. No research, architectural decision, or UI redesign is needed — the spec is already locked in the **Implementation** table above. All 4 critical issues are pure refactors / cleanups, so `@fixer` is the only specialist used; `@explorer`, `@librarian`, `@designer`, and `@oracle` are not required for this plan.

### Sub-agent rationale

| Sub-agent | Used? | Why |
|-----------|-------|-----|
| `@fixer` | Yes (×5) | Bounded code edits with a clear spec; surgical, no exploration. |
| `@oracle` | No | No architectural decision; the 4 fixes were already decided by the prior review. |
| `@explorer` | No | No unknown files or patterns; all file paths and line numbers are already pinned above. |
| `@librarian` | No | No external library / API research needed; only stdlib `zoneinfo`. |
| `@designer` | No | No UX / styling work; the 4 fixes are code-quality only. |

### Dependency graph

```
Phase 1 (parallel)         Phase 2 (parallel)
─────────────────         ─────────────────
Task 1  ──┐                Task 2  (settings_widget)
time_utils │                Task 3  (user_mode_view)
           ├──>            Task 4  (attendance_history_widget)
Task 5  ──┘                Task 5  already done in Phase 1
config.py

Task 5 is fully independent of Task 1 (different file, no shared symbols), so it joins
Phase 1. Tasks 2-4 each import `format_tz_label` or `timezone_signals` from
`time_utils`, so they must wait for Task 1 to land the public API.
```

### Phase 1 — Foundation + isolated (parallel)

| Task | Description | File | Sub-agent |
|------|-------------|------|-----------|
| **1** | (a) Replace lines 28-29 (`_signals = _TimezoneSignals()` + `timezone_signals = _signals` alias) with a single `timezone_signals = _TimezoneSignals()` declaration. (b) Update `set_timezone_config` (line 75) to emit via `timezone_signals.timezone_changed.emit(...)` instead of `_signals`. (c) Add `format_tz_label(name: str) -> str` helper, using `_load_zoneinfo()` instead of an inline `from zoneinfo import ZoneInfo`. | `src/attendance_system/utils/time_utils.py` | `@fixer` |
| **5** | In `_resolve_timezone` (lines 408-426), replace `except (ZoneInfoNotFoundError, Exception):` (line 424) with `except ZoneInfoNotFoundError:`. | `src/attendance_system/core/config.py` | `@fixer` |

**Orchestrator action:** dispatch both `@fixer` calls in the same turn. Tasks 1 and 5 touch different files, so no conflict.

### Phase 2 — Consumer updates (parallel)

| Task | Description | File | Sub-agent |
|------|-------------|------|-----------|
| **2** | (a) Delete the local `format_tz_label` function (lines 72-86). (b) Delete the inline `from zoneinfo import ZoneInfo`. (c) Add `from attendance_system.utils.time_utils import format_tz_label` to the top imports. | `src/attendance_system/ui/settings_widget.py` | `@fixer` |
| **3** | (a) Add private method `_reset_camera_preview(self) -> None` containing `self._camera_label.clear()` + `self._camera_label.setText("[ Đang khởi động camera… ]")`. (b) Replace the duplicated two-line block in `_start_session` (lines 527-528) and `_end_session` (lines 571-572) with `self._reset_camera_preview()`. (c) Update the `timezone_signals` import (line 62: `_signals as timezone_signals`) to import the public name directly: `from attendance_system.utils.time_utils import timezone_signals`. | `src/attendance_system/ui/user_mode_view.py` | `@fixer` |
| **4** | Update the `timezone_signals` import (line 29) for style consistency — already uses the public name; the change is just to drop the redundant `as timezone_signals` alias if present, and confirm the import is `from attendance_system.utils.time_utils import local_to_utc, timezone_signals, utc_to_local` (no behavior change). | `src/attendance_system/ui/attendance_history_widget.py` | `@fixer` |

**Orchestrator action:** dispatch all three `@fixer` calls in the same turn. Each touches a different file, so no conflict.

### Phase 3 — Verify & commit (orchestrator)

After both phases complete, the orchestrator runs the following serially (read-only commands, no delegation needed):

1. `pytest tests/unit/ -v` — must show 250 passed.
2. `pytest tests/integration/ -v` — must show 30 passed.
3. `ruff check src/ --select F` — must be clean.
4. If any check fails, dispatch a single targeted `@fixer` with the specific error message to fix the localized regression (do **not** retry the whole task; the failure surface is small).
5. If all checks pass, `git add -A` + `git commit` with the message skeleton below.

### Sub-agent / orchestrator load summary

| Role | Calls | Touched files | Wall-clock phases |
|------|-------|---------------|-------------------|
| `@fixer` (Phase 1) | 2 in parallel | `time_utils.py`, `config.py` | 1 round trip |
| `@fixer` (Phase 2) | 3 in parallel | `settings_widget.py`, `user_mode_view.py`, `attendance_history_widget.py` | 1 round trip |
| Orchestrator | verification + commit | — (read-only + git) | after both phases |

**Orchestrator self-implement count: 0.** All 5 implementation tasks are delegated; the orchestrator only coordinates, verifies, and commits.

### Commit message skeleton (single commit, per Design Decision #5)

```text
fix(ui): address 4 review findings on feat/ui-polish

- time_utils: drop dual name (_signals / timezone_signals), single public
  singleton; move format_tz_label here, reusing _load_zoneinfo() lazy loader
- settings_widget: import format_tz_label from time_utils
- user_mode_view: extract _reset_camera_preview helper, drop duplicated 2-line
  block in _start_session / _end_session; update timezone_signals import
- attendance_history_widget: align import style (no behavior change)
- config: narrow _resolve_timezone exception to ZoneInfoNotFoundError only

Refs: plan 0008-ui-polish-review-cleanups; Oracle review 2026-06-07.
Branch: feat/ui-polish (sits on top of c36555b).
```

### Phase 4 — Senior review (`@oracle`)

After Phase 3 commits successfully, the orchestrator dispatches `@oracle` for a read-only second-pass review. This is a "did the 4 critical issues actually get fixed, and did the fixes introduce anything new?" sanity check before the branch is considered merge-ready.

| Aspect | Detail |
|--------|--------|
| **Sub-agent** | `@oracle` (read-only; cannot edit files) |
| **Trigger** | After Phase 3's `git commit` succeeds |
| **Skipped when** | Phase 3 already failed (test or ruff); fix the failure first, then re-run this phase |
| **Concurrency** | Sequential after Phase 3; no parallel work in this phase |

#### What `@oracle` reviews

1. **Issue 1 (dual name)** — `time_utils.py` no longer has `_signals`; `timezone_signals` is the single public singleton; `set_timezone_config` emits through it.
2. **Issue 2 (camera helper)** — `user_mode_view.py` has a single `_reset_camera_preview` method; the duplicated `clear() + setText(...)` block is gone from `_start_session` and `_end_session`.
3. **Issue 3 (label location)** — `format_tz_label` lives in `time_utils.py` and is imported (not redefined) by `settings_widget.py`.
4. **Issue 4 (exception narrowing)** — `_resolve_timezone` catches only `ZoneInfoNotFoundError` (no bare `Exception`).
5. **Regression check** — confirm the move of `format_tz_label` did not change its signature/behavior; confirm `_reset_camera_preview` clears + sets the exact same text as the original; confirm `timezone_signals` consumers still connect and receive the signal.
6. **Architectural fit** — does anything in the commit smell off (newly duplicated logic, broken invariant, or a missed simplification)?

#### `@oracle` prompt template (the orchestrator fills in commit hash + branch)

```text
You are reviewing the post-implementation state of plan 0008
(ui-polish-review-cleanups) on branch `feat/ui-polish` at D:\workspace\tot-nghiep\fyp-3.

Context: 4 critical issues were raised on commit c36555b. A follow-up commit
(latest HEAD on the branch) was just made addressing them. Verify the fixes
are correct and complete.

Read:
- `git log --oneline feat/ui-polish -5`
- `git diff c36555b..HEAD --stat`
- `git diff c36555b..HEAD`  (full diff)
- The current state of the 5 files listed in the plan's Implementation table
- AGENTS.md and CLAUDE.md for project rules

Return:
- Verdict: LGTM / Approve with minor changes / Request changes / Block
- Per-issue confirmation: for each of the 4 critical issues, file:line +
  one-sentence confirmation (or "NOT FIXED" with what is missing)
- New regressions introduced by the fixes (if any)
- Anything that smells off (YAGNI / simplification candidates)

Read-only. Do NOT modify any files. Be direct — no flattery.
```

#### Branch-handling rules after `@oracle` returns

| Verdict | Orchestrator action |
|---------|---------------------|
| **LGTM** or **Approve with minor changes** | Mark plan ready for merge; report to user. Minor nits can be deferred to a follow-up plan or addressed inline. |
| **Request changes** | Dispatch a targeted `@fixer` for each blocking issue (one @fixer per file scope), then re-run Phase 3's verification (pytest + ruff). Phase 4 is **not** re-run unless the fixer's diff is non-trivial. |
| **Block** | Same as Request changes, but the orchestrator surfaces the issue to the user before re-running anything. |

#### Sub-agent / orchestrator load summary (updated)

| Role | Calls | Touched files | Wall-clock phases |
|------|-------|---------------|-------------------|
| `@fixer` (Phase 1) | 2 in parallel | `time_utils.py`, `config.py` | 1 round trip |
| `@fixer` (Phase 2) | 3 in parallel | `settings_widget.py`, `user_mode_view.py`, `attendance_history_widget.py` | 1 round trip |
| Orchestrator | verification + commit | — (read-only + git) | after Phase 2 |
| `@oracle` (Phase 4) | 1 sequential | — (read-only review) | after Phase 3 commit |

**Total sub-agent calls: 6** (5 `@fixer` + 1 `@oracle`). Orchestrator self-implement count: still 0.

## Testing

### No new tests required

The 4 fixes are refactors / cleanups that preserve behavior:

- `format_tz_label` behavior is already covered indirectly by `test_settings_widget.py` (load → save round-trip) and the `test_time_utils.py` test for `set_timezone_config` signal emission (the widget code path is exercised in the integration test `test_settings_and_enrollment_integration.py`).
- The camera-preview reset is exercised by the existing `test_user_mode_freeze.py` test surface for the user mode view.
- The signal singleton rename does not change observable behavior — `timezone_signals.timezone_changed` still emits on the same conditions.

### Verification commands

```bash
cd D:\workspace\tot-nghiep\fyp-3
pytest tests/unit/ -v
pytest tests/integration/ -v
ruff check src/ --select F
```

Expected outcome: same 250 unit + 30 integration tests pass; ruff clean. No new test failures introduced by the move.

### Manual smoke checklist

1. Open Settings UI → switch timezone from `Asia/Ho_Chi_Minh` to `America/Los_Angeles` → Save. Sidebar + history table update immediately.
2. Start an attendance session, then end it. Start another session. No stale frame on the camera preview during the brief transition.
3. Click anywhere on the "Xuất Báo Cáo" button (not just the text) → dropdown opens. No triangle on the right side of the button.

These three smoke checks already pass on `feat/ui-polish` `c36555b`; the 4 fixes here do not change UX behavior so they should continue to pass.

## Related

- Branch under review: `feat/ui-polish` (commit `c36555b`)
- Original commit being cleaned up: `c36555b feat: ui polish - timezone settings, export button fix, camera frame cleanup`
- Oracle review session: `2026-06-07` (4 critical, 3 suggestions, 5 nits)
- Deferred (out of scope, tracked for future plan): splitting `time_utils.py`'s PyQt5 dependency into a dedicated `signals.py` module.
- `AGENTS.md` — wiring and config-priority rules; import-order constraint (not affected by this plan).
- `CLAUDE.md` — "surgical changes" principle: this plan follows it (touch only the lines that need touching).
