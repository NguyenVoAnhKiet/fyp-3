# Quickstart: Report and System Configuration Utilities

## Prerequisites

- Python 3.11+
- Existing project virtual environment
- Local SQLite database initialized by the application

## Validation Focus

This feature should be validated through local tests and a short manual smoke flow:

1. Save a camera preference and threshold values.
2. Restart the application and confirm the saved values persist.
3. Close an attendance session.
4. Export the completed session to CSV.
5. Export the same session to XLSX.
6. Confirm the exported files contain only attendance/session fields and no raw biometric payloads.

## Test Commands

```bash
pytest tests/unit/test_enrollment_and_settings_unit.py -v
pytest tests/integration/test_settings_and_enrollment_integration.py -v
pytest tests/ -v
```

## Manual Checks

- Open the settings UI and verify camera inputs are listed.
- Adjust the liveness and similarity thresholds and save them.
- Start and finish a session, then export the report.
- Attempt to export an active session and confirm the system blocks it.

## Expected Outcome

- Settings persist across restarts.
- Completed sessions export successfully in CSV and XLSX formats.
- Exports remain read-only and exclude biometric data.