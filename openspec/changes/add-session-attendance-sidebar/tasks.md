## 1. UI Refactoring

- [ ] 1.1 Insert sidebar widget below the camera label in the existing `QVBoxLayout` within `UserModeView._build_active_panel`.
- [ ] 1.2 Implement sidebar UI structure (Header + `QListWidget`) within `UserModeView`.
- [ ] 1.3 Add a helper method `_add_to_sidebar(name, time)` to `UserModeView` to prepend items to the list.

## 2. Logic Integration

- [ ] 2.1 Update `UserModeView._on_recognition_result` to call `_add_to_sidebar` on successful identification.
- [ ] 2.2 Update `UserModeView._start_session` to clear the sidebar list and optionally populate it with existing records if resuming.
- [ ] 2.3 Update `UserModeView._end_session` to clear the sidebar list.

## 3. Styling & Polishing

- [ ] 3.1 Apply styling to the sidebar (fixed width, background color, fonts).
- [ ] 3.2 Ensure the camera feed still scales properly with `stretch=1` when the sidebar is placed below it.

## 4. Verification

- [ ] 4.1 Start a session and verify the sidebar is visible but empty.
- [ ] 4.2 Perform a successful check-in and verify it appears at the top of the sidebar.
- [ ] 4.3 Verify that multiple check-ins are ordered by newest first.
- [ ] 4.4 End the session and verify the sidebar is cleared.
