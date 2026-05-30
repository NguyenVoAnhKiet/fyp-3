## MODIFIED Requirements

### Requirement: Attendance Record Creation with Status Validation
The system SHALL validate that the session is in "active" status before creating an attendance record. If the session is closed, the system MUST raise `SessionClosedError` and prevent the record from being created.

#### Scenario: Create record in active session succeeds
- **WHEN** a user is recognized in an active session
- **THEN** an attendance record with status="success" is created in the database

#### Scenario: Create record in closed session fails
- **WHEN** a user is recognized in a closed session
- **THEN** the system raises `SessionClosedError` and NO attendance record is created

#### Scenario: Duplicate detection works in active sessions only
- **WHEN** the same user is recognized twice in an active session
- **THEN** the first record is created; the second triggers a duplicate detection (not an error)

#### Scenario: Duplicate detection blocked in closed sessions
- **WHEN** the same user is recognized in a closed session
- **THEN** the system raises `SessionClosedError` before duplicate detection occurs
