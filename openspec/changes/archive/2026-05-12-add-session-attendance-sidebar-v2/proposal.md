## Why

Currently, during an attendance session, there is no immediate visual feedback showing the history of checked-in individuals on the main session screen. Adding a sidebar solves this by providing real-time visibility into who has successfully checked in, which helps both the users (to confirm their check-in) and the operators (to monitor progress).

## What Changes

- **UI Layout**: Modify the session start screen (`UserModeView`) to include a sidebar below the main camera feed.
- **Attendance List**: Implement a scrollable list component within the sidebar to display checked-in students/staff.
- **Real-time Updates**: Connect the sidebar to the recognition event stream to update the list immediately upon successful identification.
- **Display Details**: Each entry in the list will show the person's name and the time they were checked in.

## Capabilities

### New Capabilities
- `session-attendance-sidebar`: Handles the rendering and state management of the attendance list sidebar.

### Modified Capabilities
<!-- None -->

## Impact

- **Affected Code**: `src/attendance_system/ui/user_mode_view.py`, `src/attendance_system/ui/main_window.py` (if layout changes are global).
- **APIs**: Might need to expose a signal or callback from the AI pipeline/service to the UI for real-time updates.
- **UI/UX**: Change in the visual layout of the session screen.
