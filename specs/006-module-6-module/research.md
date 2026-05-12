# Research: Report and System Configuration Utilities

## Decision 1: Reuse the existing settings persistence path for camera and threshold values

- Decision: Store selected camera input and threshold values through the existing `SettingsService` and `SystemSettingRepository` flow backed by `system_settings`.
- Rationale: The repository already supports keyed local settings with timestamps, which fits the module's configuration needs without introducing a new persistence boundary.
- Alternatives considered: A separate configuration table was considered but would duplicate the existing local settings mechanism.

## Decision 2: Build exports from completed session data in SQLite

- Decision: Generate reports from the existing session, attendance, recognition, and user tables, but only for sessions that are already closed.
- Rationale: The feature is explicitly read-only and should reflect the exact stored attendance history without mutating records.
- Alternatives considered: Exporting from in-memory UI state was rejected because it would not be auditable or durable.

## Decision 3: Use the standard library for CSV and a dedicated spreadsheet library for XLSX

- Decision: Use Python's `csv` module for CSV output and add `openpyxl` for XLSX generation.
- Rationale: CSV is already available in the standard library, and XLSX requires a dedicated writer. `openpyxl` is a minimal, widely used choice for workbook generation.
- Alternatives considered: `xlsxwriter` was considered but is not present in the current workspace environment; using pandas would add unnecessary surface area for a simple export path.

## Decision 4: Keep the feature offline and local-only

- Decision: Implement settings changes and report exports entirely against the local SQLite database and local filesystem.
- Rationale: The constitution requires offline-first behavior, and the current architecture already stores all operational attendance data locally.
- Alternatives considered: Any network-backed export or settings sync was rejected because it would add failure modes unrelated to the module's purpose.

## Decision 5: Treat report generation as read-only business logic

- Decision: Report generation will query data and format it for export only; it will not update attendance status, session status, or biometric records.
- Rationale: This preserves attendance integrity and keeps export logic safe to rerun.
- Alternatives considered: Auto-closing sessions or marking records during export was rejected because it mixes reporting with state mutation.

## Decision 6: Camera selection remains a UI/runtime concern, not a stored hardware contract

- Decision: Persist the selected camera identifier or index, but treat device availability as a runtime check when the settings screen opens or when capture starts.
- Rationale: Camera hardware can change between runs, so the system needs to remember the preferred device while still handling missing devices gracefully.
- Alternatives considered: Hard-binding a camera device permanently was rejected because it would fail whenever the host hardware changes.