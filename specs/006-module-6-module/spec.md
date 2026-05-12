# Feature Specification: Report and System Configuration Utilities

**Feature Branch**: `006-module-6-module`  
**Created**: 2026-04-26  
**Status**: Draft  
**Input**: User description: "## Module 6: Tiện ích Báo cáo và Cấu hình Hệ thống

Module cuối cùng tập trung vào việc khai thác dữ liệu đã thu thập và tinh chỉnh hệ thống cho phù hợp với môi trường thực tế. Tính năng cấu hình cung cấp một giao diện cho phép quản trị viên hoặc người dùng lựa chọn thiết bị camera đầu vào và cân chỉnh linh hoạt các thông số như ngưỡng Liveness hay ngưỡng Similarity thông qua thanh trượt. Tính năng báo cáo đảm nhiệm việc truy vấn toàn bộ dữ liệu của một phiên học đã kết thúc, định dạng lại và trích xuất thành tệp Excel (.xlsx) hoặc CSV, cung cấp công cụ đắc lực cho việc đánh giá điểm chuyên cần."

## User Scenarios & Testing *(mandatory)*

<!--
  IMPORTANT: User stories should be PRIORITIZED as user journeys ordered by importance.
  Each user story/journey must be INDEPENDENTLY TESTABLE - meaning if you implement just ONE of them,
  you should still have a viable MVP (Minimum Viable Product) that delivers value.
  
  Assign priorities (P1, P2, P3, etc.) to each story, where P1 is the most critical.
  Think of each story as a standalone slice of functionality that can be:
  - Developed independently
  - Tested independently
  - Deployed independently
  - Demonstrated to users independently
-->

### User Story 1 - Configure Camera and Thresholds (Priority: P1)

As an administrator or authorized user, I want to choose the camera input and adjust liveness and similarity thresholds so the attendance system fits the local classroom environment.

**Why this priority**: Configuration is the prerequisite for dependable capture and recognition quality, so it delivers the earliest operational value.

**Independent Test**: Can be fully tested by opening settings, selecting a camera, changing both thresholds, saving the values, and verifying the saved configuration is shown again later.

**Acceptance Scenarios**:

1. **Given** the settings screen is open, **When** the user selects an available camera and saves the choice, **Then** the selected camera becomes the active input for upcoming use.
2. **Given** the settings screen is open, **When** the user adjusts the liveness and similarity thresholds within the allowed range and saves, **Then** the new values are stored and displayed as the current settings.

---

### User Story 2 - Export Completed Session Reports (Priority: P2)

As an administrator or lecturer, I want to export a completed attendance session into a spreadsheet file so I can review attendance and calculate attendance results outside the application.

**Why this priority**: Reporting is the primary way to turn captured attendance data into usable course records and decisions.

**Independent Test**: Can be fully tested by closing a session, exporting it to CSV or XLSX, and confirming the resulting file contains the expected attendance rows and headings.

**Acceptance Scenarios**:

1. **Given** a session has already ended, **When** the user exports the session report as CSV, **Then** the system creates a CSV file containing the session attendance data.
2. **Given** a session has already ended, **When** the user exports the session report as XLSX, **Then** the system creates an XLSX file containing the same report content.

---

### User Story 3 - Guard Report and Settings Boundaries (Priority: P3)

As an administrator or authorized user, I want invalid settings and invalid export attempts to be blocked so the system stays reliable and easy to trust.

**Why this priority**: Boundary handling protects the feature from producing misleading reports or unstable configuration values.

**Independent Test**: Can be fully tested by attempting out-of-range threshold changes, exporting an active session, and checking that the system rejects each invalid action with clear feedback.

**Acceptance Scenarios**:

1. **Given** a user enters a threshold outside the supported range, **When** they try to save it, **Then** the system rejects the value and keeps the previous valid setting.
2. **Given** a session is still active, **When** the user attempts to export a report, **Then** the system blocks the export and explains that only completed sessions can be exported.

---

### Edge Cases

<!--
  ACTION REQUIRED: The content in this section represents placeholders.
  Fill them out with the right edge cases.
-->

- No camera devices are available when the settings screen opens.
- A previously selected camera is no longer present when the user returns to settings.
- The user moves a threshold slider to its minimum or maximum value.
- A session contains no attendance rows when the user requests a report.
- The user tries to export a report while the session is still active.
- The destination file cannot be written because of a permission or storage error.

## Constitution Alignment *(mandatory)*

- **Attendance Integrity**: The feature does not change attendance outcomes; reports are read-only snapshots of completed sessions and must not create, delete, or alter attendance records.
- **Privacy by Design**: Exported reports include only attendance and session fields needed for review, and they must not contain raw face images, face embeddings, or other biometric payloads.
- **Offline-First Reliability**: Camera selection, threshold updates, and report export all operate on local application data and must remain usable without internet access.
- **Deterministic AI Pipeline**: Saved threshold values must feed the existing liveness and similarity gates for future sessions in a predictable way, and reporting must summarize outcomes without changing recognition decisions.
- **Measurable Quality Gates**: Settings changes must persist across restarts, report exports must complete reliably for completed sessions, and exported contents must match the stored attendance history exactly.

## Requirements *(mandatory)*

<!--
  ACTION REQUIRED: The content in this section represents placeholders.
  Fill them out with the right functional requirements.
-->

### Functional Requirements

- **FR-001**: The system MUST allow authorized users to view available camera input devices and select one as the active input source for upcoming use.
- **FR-002**: The system MUST allow authorized users to adjust liveness and similarity thresholds through bounded controls.
- **FR-003**: The system MUST persist the selected camera input and threshold values locally so the last saved configuration is available after restart.
- **FR-004**: The system MUST apply saved threshold values to new attendance sessions or new capture workflows that start after the settings are saved.
- **FR-005**: The system MUST generate a report for a completed attendance session that includes student identity, session identity, timestamps, and attendance outcome data.
- **FR-006**: The system MUST export completed-session reports in CSV and XLSX formats.
- **FR-007**: The system MUST prevent report export for sessions that are not completed and provide a clear explanation to the user.
- **FR-008**: The system MUST exclude raw images, face embeddings, and other biometric payloads from exported reports.
- **FR-009**: The system MUST keep report generation read-only and MUST NOT modify attendance history or session outcomes.
- **FR-010**: The system MUST continue to support settings updates and report exports when internet access is unavailable.

### Key Entities *(include if feature involves data)*

- **System Setting**: Represents a persisted configuration value such as the selected camera input, liveness threshold, or similarity threshold.
- **Camera Input Selection**: Represents the currently chosen capture device and its availability state.
- **Session Report**: Represents a read-only summary of a completed attendance session, including attendance rows and session metadata.
- **Report Export**: Represents the generated CSV or XLSX file produced from a completed session report.

## Success Criteria *(mandatory)*

<!--
  ACTION REQUIRED: Define measurable success criteria.
  These must be technology-agnostic and measurable.
-->

### Measurable Outcomes

- **SC-001**: In usability tests, at least 95% of users can select a camera and save valid threshold values in under 60 seconds.
- **SC-002**: In persistence tests, 100% of saved camera and threshold settings remain available after the application is restarted.
- **SC-003**: In acceptance tests, 100% of completed sessions with attendance data can be exported successfully to either CSV or XLSX.
- **SC-004**: For completed sessions containing up to 500 attendance rows, at least 95% of exports finish in under 30 seconds.
- **SC-005**: In export validation tests, 100% of generated reports contain the required session and attendance columns and no raw biometric data.
- **SC-006**: In negative tests, 0 exports are produced for sessions that are still active or otherwise incomplete.

## Assumptions

<!--
  ACTION REQUIRED: The content in this section represents placeholders.
  Fill them out with the right assumptions based on reasonable defaults
  chosen when the feature description did not specify certain details.
-->

- Authorized users already have access to the application settings and report features through the existing UI flow.
- The host environment can enumerate at least one camera device when camera selection is expected to succeed.
- Report exports are limited to completed sessions and use data already stored locally in the application.
- Threshold bounds match the safe operating range expected by the existing recognition pipeline.
