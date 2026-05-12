# Data Model: Report and System Configuration Utilities

## System Setting

- **Purpose**: Stores a persisted configuration value used by the application.
- **Key fields**: `setting_key`, `setting_value`, `value_type`, `updated_at`
- **Rules**:
  - Keys are unique.
  - Values are stored locally and must survive application restarts.
  - Camera selection and threshold values must remain within the supported runtime bounds.

## Camera Input Selection

- **Purpose**: Represents the camera input preference chosen by the user.
- **Key fields**: `camera_index` or equivalent identifier, `display_label`, `is_available`
- **Relationships**: Used by settings UI and capture startup logic.
- **Rules**:
  - The selected device may be unavailable later and must be handled as a runtime condition.
  - The stored preference should not block the user from changing to a different device.

## Session Report

- **Purpose**: Represents a completed attendance session prepared for export.
- **Key fields**: `session_id`, `subject_name`, `class_name`, `status`, `start_time`, `end_time`, threshold snapshots, row count
- **Relationships**: Aggregates attendance outcomes from the session, joined with student metadata.
- **Rules**:
  - Only completed sessions may be exported.
  - The report must be derived from stored attendance history, not from live UI state.

## Session Report Row

- **Purpose**: Represents one exported attendance line item.
- **Key fields**: `student_id`, `full_name`, `session_time`, `attendance_status`, optional confidence or outcome notes
- **Relationships**: Belongs to one session report and maps to one recorded attendance outcome.
- **Rules**:
  - Rows must not contain raw face images or embeddings.
  - Columns must be stable across CSV and XLSX export formats.

## Report Export

- **Purpose**: Represents the generated output artifact.
- **Key fields**: `format`, `destination_path`, `generated_at`, `session_id`
- **Relationships**: Created from one completed session report.
- **Rules**:
  - Export is read-only.
  - Export must fail safely if the session is not completed or the destination cannot be written.

## State Notes

- Settings state transitions are simple: user edits values, system validates, system persists, future sessions read the saved values.
- Report state transitions are also simple: active session -> closed session -> exportable report -> file output.