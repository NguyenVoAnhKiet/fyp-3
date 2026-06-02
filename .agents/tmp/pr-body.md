## Summary

On the **first successful recognition of a user in a session**, freeze the camera for N seconds and show a centered Vietnamese success overlay, then resume so the next user can be recognized. Admin-configurable (duration 0–10s, optional sound). Default: 4s freeze, sound off, overlay-only UX.

## Why

Previously the green bbox + name appeared for ~1s (`_RESULT_HOLD_FRAMES = 30` @ 30 fps) then reset to gray — too subtle. Users lingered in the camera zone, delaying the next person. A clear "điểm danh thành công" signal + brief freeze gives unambiguous feedback and clean handoff.

## Changes

**Feature (3 commits)**
- `12b030d` — feat(ui): freeze camera + overlay on first recognition per session
- `4110d97` — docs: AGENTS.md notes
- `b99eebd` — docs(plans): archive 0001 plan (Status → Done)

**Code**
- `src/attendance_system/ui/camera_thread.py` — `pause()` / `resume()` public API + `_paused` flag polled at 50ms in `run()` (AIWorker untouched, idles naturally)
- `src/attendance_system/ui/user_mode_view.py` — `_build_freeze_overlay()` (parented to `_camera_label`, `STATUS_SUCCESS` design token), `_trigger_freeze()` re-syncs geometry each trigger, `resizeEvent` keeps overlay aligned, cancel timer + hide overlay in `_end_session`
- `src/attendance_system/ui/settings_widget.py` — new "Điểm Danh" admin group (seconds `QSpinBox` 0–10, sound `QCheckBox`)
- `src/main.py` — `_seed_setting()` helper + env seeds `ATTENDANCE_FREEZE_SECONDS` (int, default 4) and `ATTENDANCE_FREEZE_SOUND_ENABLED` (bool, default false)

**Config / docs**
- `.env.example` — new "Attendance UX" section
- `AGENTS.md` — docs + test notes
- `docs/README.md` — small link update
- `docs/plans/README.md` — move 0001 from Active → Archive table
- `docs/plans/active/0001-attendance-freeze-feedback.md` → `docs/plans/archive/2026-06-02-0001-attendance-freeze-feedback.md` (Status: Done)

**Tests** (12 new, all unit)
- `tests/unit/test_camera_thread_pause.py` — 5 tests: `pause()` / `resume()` flag, `run()` skips `cap.read()` while paused
- `tests/unit/test_user_mode_freeze.py` — 7 tests: first-success triggers, no re-trigger for same user, `seconds=0` is a no-op, overlay hides on timer fire, `_end_session` cancels pending freeze + resumes camera

## Testing

- `pytest tests/unit/ -v` — 144/144 pass (12 new)
- `ruff check src/` — clean

## Design

Decision rationale captured in the [archived plan](docs/plans/archive/2026-06-02-0001-attendance-freeze-feedback.md) (10 grilled decision points).

## Notes

- Per-user recognition cooldown (`_COOLDOWN_SECONDS = 3.0`) is **unaffected**.
- Freeze is per-session (reuses existing `_recognized_users: set[int]`); re-recognition of the same user later in the same session does not re-trigger.
- `attendance_freeze_seconds = 0` cleanly disables the feature (no freeze, no overlay, no sound → original behavior).
- No DB schema changes.
