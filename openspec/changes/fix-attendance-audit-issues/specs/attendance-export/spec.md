## MODIFIED Requirements

### Requirement: Empty Session Export Produces Valid CSV
The system SHALL ensure that exporting an empty session (with zero attendance records) produces a valid CSV file with proper headers, rather than an invalid file with no headers or data.

#### Scenario: Export active session with records
- **WHEN** a user exports an active session with attendance records
- **THEN** a CSV file is generated with headers (subject, class, date, name, student_id, status) and one row per record

#### Scenario: Export empty session produces valid CSV
- **WHEN** a user exports a closed session with NO attendance records
- **THEN** a CSV file is generated with proper headers (subject, class, date, name, student_id, status) but zero data rows

#### Scenario: CSV headers are consistent
- **WHEN** exporting any session (empty or not)
- **THEN** the CSV headers are always in the same order and include all required columns

#### Scenario: Export handles null user_id gracefully
- **WHEN** exporting a session where a record has a null user_id (deleted user)
- **THEN** the CSV row for that record shows empty string for name and student_id
