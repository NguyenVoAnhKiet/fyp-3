# Session Attendance Sidebar Specification

This specification defines the functional requirements and scenarios for the Real-time Attendance Sidebar, which provides immediate visual feedback during an active attendance session.

## Requirements

### Requirement: Real-time Attendance Sidebar
The system SHALL provide a sidebar on the active attendance screen that displays a real-time list of individuals who have successfully checked in during the current session.

#### Scenario: Pre-populating sidebar on session start
- **WHEN** an attendance session is started
- **THEN** the sidebar SHALL be initialized and populated with any existing successful check-ins for that session (if the session was resumed).

#### Scenario: Real-time update on success
- **WHEN** a person is successfully recognized and their attendance is recorded
- **THEN** their name and check-in time SHALL be immediately added to the top of the sidebar list.

#### Scenario: Visual feedback in sidebar
- **WHEN** an entry is added to the sidebar
- **THEN** it SHALL display the time of check-in (HH:mm:ss) followed by the person's full name.

#### Scenario: Scrollable sidebar
- **WHEN** the number of check-ins exceeds the visible height of the sidebar
- **THEN** the sidebar SHALL provide a vertical scrollbar to allow viewing all entries.

#### Scenario: Clearing sidebar on session end
- **WHEN** the attendance session is ended
- **THEN** the sidebar list SHALL be cleared for the next session.
