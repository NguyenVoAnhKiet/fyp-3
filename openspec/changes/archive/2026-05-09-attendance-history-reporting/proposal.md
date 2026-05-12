## Why

The system currently lacks a centralized interface for administrators to review historical attendance data. This change provides the necessary UI and backend logic to browse past attendance sessions, view detailed records, and export this data for administrative reporting and external analysis.

## What Changes

- **New `AttendanceHistoryWidget`**: A UI component featuring a split-view layout. The left side displays a list of past attendance sessions, and the right side shows detailed attendance records for the selected session.
- **Filtering Capabilities**: Implementation of date range, class, and subject filters for the session list to enable efficient data retrieval.
- **Enhanced `AttendanceService`**: New methods to fetch sessions and their associated attendance logs from the database.
- **Data Export**: Functionality to export attendance records to Excel (.xlsx) and CSV formats, integrated into the UI via an "Export" button in the session details view.
- **Main UI Integration**: Adding the `AttendanceHistoryWidget` to the administrator dashboard.

## Capabilities

### New Capabilities
- `attendance-history`: Provides the ability to search, filter, and view historical attendance sessions and individual student records within those sessions.
- `attendance-reporting`: Provides the ability to export selected attendance data into standardized formats (Excel, CSV) for external use.

### Modified Capabilities
- None: This change introduces new features without altering existing core requirements of other modules.

## Impact

- **UI**: New `AttendanceHistoryWidget` in `src/attendance_system/ui/`.
- **Services**: Updates to `AttendanceService` in `src/attendance_system/services/attendance_service.py`.
- **Repositories**: New or updated queries in `AttendanceRepository` and `SessionRepository` in `src/attendance_system/repositories/`.
- **Dependencies**: Addition of `pandas` and `openpyxl` for Excel export (if not already present).
- **Architecture**: Minor expansion of the service layer to handle reporting logic.
