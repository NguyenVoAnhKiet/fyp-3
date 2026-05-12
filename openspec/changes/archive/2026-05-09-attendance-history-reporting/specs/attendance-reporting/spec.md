## ADDED Requirements

### Requirement: Export to Excel
The system SHALL allow administrators to export the attendance records of a selected session to an Excel (.xlsx) file.

#### Scenario: Successful Excel export
- **WHEN** admin clicks the "Export to Excel" button for a session
- **THEN** the system prompts for a save location and generates a valid Excel file containing the session details (date, class, subject) and student attendance records (student name, ID, status, timestamp).

### Requirement: Export to CSV
The system SHALL allow administrators to export the attendance records of a selected session to a CSV file.

#### Scenario: Successful CSV export
- **WHEN** admin clicks the "Export to CSV" button for a session
- **THEN** the system prompts for a save location and generates a valid CSV file containing the session details (date, class, subject) and student attendance records (student name, ID, status, timestamp).
