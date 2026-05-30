## ADDED Requirements

### Requirement: Explicit Migration Error Handling
The system SHALL log all migration errors explicitly rather than silently suppressing them. If a database migration fails, the error MUST be logged and the exception MUST be re-raised to prevent the application from proceeding with a potentially corrupted schema.

#### Scenario: Migration succeeds
- **WHEN** the database migration for attendance_records is applied
- **THEN** the migration completes without error and logs success status

#### Scenario: Migration fails with logged error
- **WHEN** the database migration fails (e.g., due to missing columns or transaction failure)
- **THEN** the system logs the error with full exception details and re-raises the exception

#### Scenario: Application halts on migration error
- **WHEN** a migration error is encountered during schema initialization
- **THEN** the application startup is blocked and an error message is displayed to the user

#### Scenario: Log includes debugging context
- **WHEN** a migration fails
- **THEN** the log entry includes the schema version, migration name, and root cause details
