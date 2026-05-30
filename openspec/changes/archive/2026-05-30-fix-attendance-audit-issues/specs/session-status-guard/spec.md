## ADDED Requirements

### Requirement: Session Status Validation
The system SHALL validate that a session is in "active" status before accepting attendance records. If a session is closed or in any non-active status, the system MUST reject the record with a `SessionClosedError` exception.

#### Scenario: Record success on active session
- **WHEN** a user is recognized during an active session
- **THEN** the attendance record is created successfully

#### Scenario: Record success on closed session
- **WHEN** a user is recognized during a closed session
- **THEN** the system raises `SessionClosedError` and does NOT create an attendance record

#### Scenario: Record duplicate on closed session
- **WHEN** a user is already recorded in a closed session and is recognized again
- **THEN** the system raises `SessionClosedError` and does NOT log a duplicate event

#### Scenario: Spoof warning on closed session
- **WHEN** a liveness check fails (spoof detected) during a closed session
- **THEN** the system raises `SessionClosedError` and does NOT log a spoof warning event
