## Context

The current attendance system successfully captures real-time attendance data but lacks a mechanism for administrators to review past data or generate reports. This design addresses the need for a dedicated "Attendance History" module that integrates with the existing service and repository layers.

## Goals / Non-Goals

**Goals:**
- Implement a user-friendly split-view UI for browsing sessions and viewing detailed student records.
- Enable filtering of sessions by date range, class, and subject to simplify data discovery.
- Provide robust data export capabilities for Excel (.xlsx) and CSV formats.
- Ensure data consistency by reading directly from the existing attendance and session tables.

**Non-Goals:**
- Modification of historical attendance records (CRUD for history is out of scope).
- Advanced analytics (e.g., trend charts, absence alerts) beyond simple list views and exports.
- Integration with external LMS/SIS at this stage.

## Decisions

### 1. UI Layout: Split-View with `QSplitter`
- **Rationale**: A split-view allows admins to quickly scan sessions on the left and see details on the right without switching pages. `QSplitter` provides a resizable interface that adapts to different screen sizes.
- **Alternative**: A single table view where selecting a row opens a dialog. This was rejected because it requires more clicks and hides context.

### 2. Service Layer Expansion
- **Action**: Add `get_sessions(filters)` and `get_session_records(session_id)` to `AttendanceService`.
- **Rationale**: Keeps business logic out of the UI and maintains the existing service-repository pattern.

### 3. Data Export via `pandas`
- **Rationale**: `pandas` provides high-level `to_excel()` and `to_csv()` methods that handle data types and formatting more reliably than manual CSV writing or low-level `openpyxl` calls alone. It also simplifies future expansions (e.g., adding more export formats).
- **Dependency**: Requires `pandas` and `openpyxl`.
- **Alternative**: Python's built-in `csv` module. Rejected for Excel export as it doesn't support .xlsx natively.

### 4. Query Optimization
- **Action**: Use JOINs in `SessionRepository` to fetch session info along with student counts and class names in a single query where possible.
- **Rationale**: Reduces the number of database roundtrips and improves UI responsiveness.

## Risks / Trade-offs

- **[Risk] UI Lag with Many Sessions** → **Mitigation**: Implement pagination or a "Load More" button in the session list if the count exceeds 1000. For the initial implementation, date range filters will be the primary tool to keep results manageable.
- **[Risk] Dependency Bloat** → **Mitigation**: `pandas` is a large library. If storage space is critical, we could switch to a lighter CSV-only approach, but the benefit of native Excel support for administrative staff outweighs the footprint.
- **[Risk] Exporting Huge Sessions** → **Mitigation**: Perform export operations in a separate thread to prevent UI freezing during file generation.
