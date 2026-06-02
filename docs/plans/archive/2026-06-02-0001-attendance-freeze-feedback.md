# Plan 0001: Attendance Freeze Feedback

## Status

**Done** — implementation complete on branch `feature/attendance-freeze-feedback` (commits `12b030d`, `4110d97`). 12 new unit tests pass (5 `test_camera_thread_pause`, 7 `test_user_mode_freeze`); full suite 144/144; ruff clean. Awaiting merge to `main`.

## Context

During an active attendance session, users currently receive minimal feedback when they are successfully recognized — a green bounding box and their name appear on the camera feed for roughly one second (`_RESULT_HOLD_FRAMES = 30` at ~30 fps), then everything resets to "detecting" gray. This is too subtle: users cannot tell whether they have actually been recorded, so they tend to linger in the camera zone, which delays the next person in line.

**Problem**: No clear "you have been recorded, you can step away" signal. The UI is ambiguous.

**Solution**: When a user is recognized for the **first time in a session**, freeze the camera feed for a few seconds and show a large "điểm danh thành công" overlay. The frozen frame already contains the green bbox + their name, so the visual context is preserved. When the freeze ends, the camera resumes and the next person can be recognized immediately.

## Goals

1. On the first successful recognition of a user in a session, freeze the camera for N seconds (default 4, configurable) and display a prominent success overlay.
2. The freeze must be **per-session**: the same user re-entering the frame later in the same session must not re-trigger the freeze.
3. The freeze must NOT block the next user from being recognized once it ends. AI pipeline should be warm and ready.
4. The freeze must integrate cleanly with the existing per-user cooldown (`_COOLDOWN_SECONDS = 3.0`) and `_recognized_users` set.
5. Behavior must be admin-configurable (duration, optional sound) and disable-able (duration = 0 → off).

## Non-Goals

- **Multi-face freeze**: this plan covers the "first face recognized this frame cycle" case. If two new users are recognized in the same AI batch, only the first triggers a freeze; the second waits until the first freeze ends before triggering their own.
- **Per-user configurable freeze duration**: a single global setting is enough; per-user overrides are out of scope.
- **Freeze for spoof/unrecognized events**: only `success` results trigger a freeze. Spoof and unrecognized keep their existing behavior (bbox color + counter increment, no freeze).
- **Animation or transition effects on the overlay**: the overlay is a static QLabel. No fade-in/out, no animation, no progress bar.
- **Sound/buzzer on success**: included as an *optional* setting (`attendance_freeze_sound_enabled`, default off) but no specific tone choice, no volume control, no multi-tone patterns. When enabled, a single short platform-default beep is played at freeze start.
- **Cross-platform audio backend tuning**: a single approach that "just works" on Windows is sufficient. macOS/Linux audio quality is best-effort.
- **Migrating historical data**: no DB schema changes required for this feature — only a new key in `system_settings`. Existing sessions and records are untouched.

## Design Decisions

The design was worked out by grilling each branch of the decision tree. Each row is one question resolved.

| # | Question | Options considered | Final answer | Why |
|---|----------|--------------------|--------------|-----|
| 1 | "Lần đầu tiên" trigger scope | (a) per-session / (b) lifetime / (c) within-N-seconds | **(a) per-session** | Matches use case ("next person takes their turn"); reuses existing `_recognized_users: set[int]` in `user_mode_view.py:97`; no DB query; predictable per session. |
| 2/3 | "Đóng băng camera" implementation | (a) visual-only freeze / (b) pause camera capture / (c) kill+reopen camera | **(b) pause camera capture** | Cheaper than (c), AI stays warm; `_paused` flag in `CameraThread.run()` loop, `time.sleep(50ms)` while paused, no thread restart. |
| 4 | Freeze duration | (a) fixed 3s / (b) fixed 5s / (c) configurable (default 4s) | **(c) configurable, default 4s** | Matches existing settings pattern (`liveness_threshold`, `similarity_threshold`); admin can tune; 4s is sweet spot. |
| 5 | Visual feedback during freeze | (a) just frozen frame / (b) big centered overlay / (c) overlay + countdown | **(b) big centered overlay** | Frame already has green bbox + name; overlay text clarifies "you're done, you can leave"; no countdown pressure. |
| 6 | Behavior at freeze end | (a) reset immediately / (b) 0.5-1s grace with green / (c) hold green until user exits frame | **(a) reset immediately** | "Freeze = celebration moment, then normal" principle; clean handoff to next user. |
| 7 | AI worker behavior during freeze | (a) don't touch / (b) explicit pause/resume / (c) drain queue at freeze start | **(a) don't touch** | `AIWorker` naturally idles because main loop stops calling `submit_task`; `is_busy()` check at `camera_thread.py:360` already handles in-flight tasks; minimal risk. |
| 8 | Settings key design | (a) 1 key `attendance_freeze_seconds` / (b) range 2-10 / (c) feature flag + key | **(a) 1 key, range 0-10, default 4** | Matches 1-key pattern; 0 disables feature for easy rollback. |
| 9 | Sound on success | (a) none / (b) beep / (c) configurable (default off) | **(c) configurable, default off** | Admin opt-in; respects quiet environments; small added complexity. |
| 10 | Session end mid-freeze | (a) clean cancel / (b) wait for freeze / (c) force-end + log | **(a) clean cancel** | Cancel pending `QTimer.singleShot`, hide overlay, then `camera_thread.stop()` runs normally. |

## Implementation

### Files to change

| File | Change |
|------|--------|
| `src/attendance_system/ui/camera_thread.py` | Add `self._paused: bool = False` to `CameraThread.__init__`. Add `pause()` and `resume()` public methods. Modify `run()` loop (line ~329): check `self._paused` at the top of each iteration; if true, `time.sleep(0.05)` and `continue`. |
| `src/attendance_system/ui/user_mode_view.py` | Add `_freeze_overlay: QLabel` member, absolute-positioned over `_camera_label`. Add `_freeze_timer: QTimer | None` for the cancel-on-end path. In `_on_recognition_result` (line 517), when a new `user_id` enters `_recognized_users`, call `_trigger_freeze()`. `_trigger_freeze()` reads the `attendance_freeze_seconds` setting; if > 0, calls `self._camera_thread.pause()`, shows overlay, starts a `QTimer.singleShot(seconds * 1000, ...)` to `_end_freeze()`. `_end_freeze()` calls `self._camera_thread.resume()`, hides overlay, resets `_bbox_color` is handled by the camera thread's `_result_hold_counter` (already 0 by then). In `_end_session` (line 464), cancel the timer and hide overlay before stopping the camera. |
| `src/attendance_system/ui/settings_widget.py` | Add a new `QGroupBox("Điểm Danh")` to `_build_ui` with: `attendance_freeze_seconds` (`QSpinBox`, range 0-10, default 4) + `attendance_freeze_sound_enabled` (`QCheckBox`, default unchecked). Load + save both in `_load_values` and `_save`. |
| `src/main.py` | Add `_seed_threshold` calls (using the existing helper) for `attendance_freeze_seconds` (env `ATTENDANCE_FREEZE_SECONDS`, default 4) + add a similar seed for `attendance_freeze_sound_enabled` (env `ATTENDANCE_FREEZE_SOUND_ENABLED`, default "false"). Add the env-var read helpers if needed. |
| `.env.example` | Document the two new env vars under a "3. Attendance UX" section, following the style of the `FACE_ANTISPOOF_CONFIDENCE_THRESHOLD` block. |
| `tests/unit/test_user_mode_freeze.py` *(new)* | Test `_trigger_freeze()`: only fires once per session per user; respects `seconds=0` (no-op); overlay hidden when freeze ends; timer cancelled in `_end_session`. |
| `tests/unit/test_camera_thread_pause.py` *(new)* | Test `pause()` / `resume()` set the flag; `run()` skips `cap.read()` while paused. Use mocks to avoid needing a real camera. |

### Touch points by line (reference)

- `camera_thread.py:198-263` — `CameraThread.__init__` and inner `AIWorker` setup. Add `self._paused = False` here.
- `camera_thread.py:329` — `while self._running:` loop in `run()`. Add the pause check at the top.
- `user_mode_view.py:97` — already has `self._recognized_users: set[int]`. Reuse.
- `user_mode_view.py:517-548` — `_on_recognition_result` for "success" branch. Insert `_trigger_freeze()` after `self._recognized_users.add(user_id)`.
- `user_mode_view.py:464-479` — `_end_session`. Add cancel + hide before `self._camera_thread.stop()`.
- `settings_widget.py:75-133` — `_build_ui`. Add a new group box.
- `settings_widget.py:139-164` — `_load_values` and `_save`. Extend.
- `main.py:230-236` — seeding block. Add two more lines for the new settings.

### Settings semantics

| Key | Type | Default | Range | Env var (first-run seed) | Admin UI control |
|-----|------|---------|-------|--------------------------|------------------|
| `attendance_freeze_seconds` | int | 4 | 0-10 | `ATTENDANCE_FREEZE_SECONDS` | `QSpinBox` |
| `attendance_freeze_sound_enabled` | bool | false | true/false | `ATTENDANCE_FREEZE_SOUND_ENABLED` | `QCheckBox` |

A value of 0 for `attendance_freeze_seconds` disables the freeze feature entirely. No freeze, no overlay, no sound. Original behavior is preserved.

## Testing

### Unit tests to add

- `tests/unit/test_user_mode_freeze.py`:
  - `test_freeze_triggers_on_first_recognition_in_session` — first `success` for a user_id calls `_trigger_freeze()`.
  - `test_freeze_does_not_retrigger_for_same_user` — second `success` for the same user_id does NOT call `_trigger_freeze()`.
  - `test_freeze_disabled_when_seconds_is_zero` — when setting is 0, no pause call, no overlay.
  - `test_freeze_overlay_hides_when_timer_fires` — simulate the QTimer callback, assert overlay hidden and `camera_thread.resume()` called.
  - `test_end_session_cancels_pending_freeze` — call `_end_session()` while a freeze is active, assert timer is stopped and overlay is hidden before `camera_thread.stop()`.

- `tests/unit/test_camera_thread_pause.py`:
  - `test_pause_sets_flag` — `pause()` sets `self._paused = True`.
  - `test_resume_clears_flag` — `resume()` sets `self._paused = False`.
  - `test_run_loop_skips_read_while_paused` — patch `time.sleep` and `cap.read`; with `_paused = True`, `cap.read` is not called.

### Manual smoke checklist

1. Start a session. Recognize user A. Verify: camera freezes, overlay "✓ ĐIỂM DANH THÀNH CÔNG" appears, bbox is green, name + score shown.
2. Wait 4s. Verify: camera resumes, overlay hides, bbox returns to gray, AI processes new frames.
3. With user A still in frame, verify: no second freeze (cooldown + `_recognized_users` prevent it).
4. Have user B walk up immediately after A's freeze ends. Verify: user B is recognized within 1-2 frames; their freeze triggers; handoff is smooth.
5. Set `attendance_freeze_seconds = 0` in admin. Repeat step 1. Verify: no freeze, no overlay, original behavior.
6. Set `attendance_freeze_seconds = 6` in admin. Verify: freeze lasts 6s, overlay shown for 6s.
7. Enable `attendance_freeze_sound_enabled`. Verify: a single beep plays at freeze start.
8. Start a freeze, then click "Kết Thúc Phiên" (E). Verify: overlay hides immediately, no QTimer crash, no orphan frame.

### Verification commands

```bash
pytest tests/unit/ -v
ruff check src/
```

## Related

- `_COOLDOWN_SECONDS = 3.0` in `camera_thread.py:23` — per-user re-recognition suppression.
- `_recognized_users: set[int]` in `user_mode_view.py:97` — per-session dedupe of sidebar entries.
- `record_success()` in `attendance_service.py` — DB write that also relies on the UNIQUE(session_id, user_id) constraint.
- AGENTS.md "Gotchas" section — thread-affinity rules for `QThread` subclasses (no creating workers in `run()`).
