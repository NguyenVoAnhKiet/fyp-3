## Context

The `UserModeView` is the primary interface for attendance sessions. Currently, it shows a large camera feed and a status label below it. There is no historical view of check-ins during the active session, which can lead to uncertainty for users and operators.

## Goals / Non-Goals

**Goals:**
- Provide immediate visual confirmation of recent successful check-ins.
- Maintain a readable list of all check-ins for the current session.
- Integrate the sidebar seamlessly into the existing `UserModeView` layout.

**Non-Goals:**
- Allowing manual editing of attendance from this sidebar.
- Displaying full student profiles or detailed biometric data.
- Search/filter functionality within the sidebar (this belongs in History).

## Decisions

### 1. UI Layout Strategy
We will insert the sidebar into the existing `QVBoxLayout` of the `ACTIVE` panel, below the camera feed.
- **Top**: Existing camera feed (with `stretch=1` to take remaining space).
- **Middle**: New Sidebar component.
- **Bottom**: Existing status labels and controls.
- **Rationale**: Vertical layout keeps the camera as the primary visual element and avoids horizontal space contention. A `QHBoxLayout` was originally planned but discarded because it would reduce camera width on widescreen displays.

### 2. Sidebar Component
The sidebar will be a `QFrame` containing:
- A header label ("Danh sách điểm danh").
- A `QListWidget` for the actual names.
- **Rationale**: `QListWidget` provides built-in scrolling and easy item management compared to manual layout of labels.

### 3. Data Flow
`UserModeView._on_recognition_result` already receives `full_name` upon success.
- Upon successful `record_success`, a new item will be prepended (or appended) to the `QListWidget`.
- We will prepend new entries so the latest check-in is always at the top.

### 4. Visual Styling
- Sidebar height: Fixed at 200px (scrollable if content overflows).
- Sidebar stretches horizontally to fill the parent width.
- List items: Simple text "HH:mm:ss - Name".
- Colors: Subtle background for the sidebar to distinguish it from the camera area.

## Risks / Trade-offs

- **[Risk] Vertical Space** → The sidebar takes up vertical space below the camera.
  - **Mitigation**: Use a fixed height (200px) with the camera using `stretch=1` so the camera always gets the majority of the window.
- **[Risk] List Overflow** → Many check-ins may exceed the 200px sidebar height.
  - **Mitigation**: The `QListWidget` provides a built-in vertical scrollbar for overflow.
- **[Risk] State Persistence** → If the view is switched or refreshed, the sidebar might lose its temporary list.
  - **Mitigation**: When entering the `ACTIVE` state (session start), we can optionally query the database for existing records for that `session_id` to populate the list (important if the app restarts during a session).
