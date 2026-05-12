## 1. Backend & Data Layer

- [x] 1.1 Add `get_sessions` method to `AttendanceRepository` with support for date range, class, and subject filters.
- [x] 1.2 Add `get_records_for_session` method to `AttendanceRepository` to fetch detailed student logs for a specific session ID.
- [x] 1.3 Update `AttendanceService` to expose the new repository methods for sessions and records.
- [x] 1.4 Implement `export_session_to_csv` in `AttendanceService` using `pandas`.
- [x] 1.5 Implement `export_session_to_excel` in `AttendanceService` using `pandas`.
- [x] 1.6 Add unit tests for the new `AttendanceService` methods, specifically for filtering logic and data structure of exports.

## 2. UI Development

- [x] 2.1 Create `AttendanceHistoryWidget` in `src/attendance_system/ui/attendance_history_widget.py`.
- [x] 2.2 Implement the UI layout using `QSplitter` to create the left (session list) and right (session details) panes.
- [x] 2.3 Build the session list filters: `QDateEdit` for date ranges and `QComboBox` for class/subject selections.
- [x] 2.4 Implement the session records table in the right pane using `QTableWidget` or `QTableView`.
- [x] 2.5 Add "Export to Excel" and "Export to CSV" buttons with appropriate icons to the session detail view.
- [x] 2.6 Implement logic to populate the session list based on filters and the detail table based on selection.
- [x] 2.7 Connect export buttons to `AttendanceService` export methods, including a `QFileDialog` for selecting the save path.

## 3. Integration & Verification

- [x] 3.1 Register and add the `AttendanceHistoryWidget` to the `AdminDashboardView` or `MainWindow`.
- [x] 3.2 Implement basic error handling and user feedback (e.g., success/failure message boxes) for the export process.
- [x] 3.3 Perform manual verification of exported file contents against database records.
- [x] 3.4 Ensure all new UI components follow existing styling and layout conventions.
