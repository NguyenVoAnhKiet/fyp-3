# Feature Specification: Database & Storage Core

**Feature Branch**: `[001-database-storage-core]`  
**Created**: 2026-04-24  
**Status**: Draft  
**Input**: User description: "## Module 1: Cốt lõi Dữ liệu và Lưu trữ (Database & Storage Core)

Module này chịu trách nhiệm xây dựng nền tảng lưu trữ toàn bộ thông tin cục bộ của hệ thống bằng SQLite3. Trọng tâm của module là việc khởi tạo, quản lý và kết nối năm bảng dữ liệu chính bao gồm: thông tin người dùng, mảng vector đặc trưng khuôn mặt (embeddings), thông tin các phiên điểm danh, lịch sử nhận diện chi tiết và bảng cài đặt cấu hình hệ thống. Yêu cầu đầu ra của phân hệ này là một tập hợp các lớp (classes) xử lý cơ sở dữ liệu hoàn chỉnh, cung cấp các hàm tương tác (CRUD) hoạt động độc lập và an toàn để không làm nghẽn các luồng xử lý chính của ứng dụng."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Initialize Core Storage (Priority: P1)

As a system operator, I want the local storage to be ready with all required record types from the start, so the attendance system can begin working immediately and retain data across restarts.

**Why this priority**: If core storage is unavailable, the system cannot support attendance, enrollment, or configuration workflows.

**Independent Test**: Start from a fresh installation, initialize the feature, and confirm that all required record types are available and persist after a restart.

**Acceptance Scenarios**:

1. **Given** a fresh installation, **When** the system starts for the first time, **Then** the local storage is initialized and ready for use.
2. **Given** existing stored records, **When** the system restarts, **Then** those records remain available without manual recovery.

---

### User Story 2 - Record Attendance History Reliably (Priority: P2)

As a lecturer, I want each attendance session and recognition result to be recorded consistently, so attendance history remains accurate and auditable.

**Why this priority**: Accurate attendance history is the core business outcome of the module and must remain trustworthy during live use.

**Independent Test**: Create a session, record attendance events, attempt a duplicate entry, and verify that only one attendance result is kept for the same learner within the defined window.

**Acceptance Scenarios**:

1. **Given** an active session, **When** a learner is recognized successfully, **Then** the attendance record is saved with the correct status and timestamp.
2. **Given** an active session with a learner already marked present, **When** the same learner is recognized again within the duplicate-prevention window, **Then** the second attempt is blocked from creating a second attendance entry.

---

### User Story 3 - Manage Settings and Protected Enrollment Data (Priority: P3)

As an administrator, I want to store configuration values and biometric references safely, so the system can be tuned without exposing private data.

**Why this priority**: Configuration and privacy controls support operational correctness, but they are secondary to core storage and attendance integrity.

**Independent Test**: Update a setting, verify that the new value is available after restart, and confirm that enrollment data is stored only in derived form without retaining raw images.

**Acceptance Scenarios**:

1. **Given** a saved configuration value, **When** an administrator updates it, **Then** the new value is persisted for future sessions.
2. **Given** a completed enrollment workflow, **When** storage is reviewed afterward, **Then** no raw enrollment images remain stored.

### Edge Cases

- A record type is missing from an older installation and the system must restore the missing structure without losing existing data.
- Two write operations target the same record at nearly the same time and the final state must remain consistent.
- A duplicate attendance attempt arrives after a learner has already been marked present for the session.
- A session is interrupted before a write completes and the system must not leave partially saved attendance data in an unclear state.
- A stored configuration value is absent or invalid and the system must fall back to a safe default.

## Constitution Alignment *(mandatory)*

- **Attendance Integrity**: The storage layer keeps attendance records unique per learner per session window, preserves the recorded status, and prevents silent duplication.
- **Privacy by Design**: Only derived biometric references and required administrative data are stored; raw enrollment images are not retained after processing, and sensitive values are protected from plain-text exposure.
- **Offline-First Reliability**: All storage and retrieval operations work locally without internet access, so attendance and admin workflows remain usable in disconnected environments.
- **Deterministic AI Pipeline**: The storage layer preserves the session context, status, and effective thresholds needed to explain how each recognition outcome was recorded.
- **Measurable Quality Gates**: Core records must be initialized successfully on first run, remain available after restart, and support routine read/write operations without blocking the live attendance workflow.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system must initialize all required local record types before the feature is used.
- **FR-002**: The system must preserve existing records across restarts without manual reconstruction.
- **FR-003**: The system must support create, read, update, and delete operations for user records and configuration records.
- **FR-004**: The system must record each attendance session with a unique identity, session context, status, and timestamps.
- **FR-005**: The system must record attendance outcomes and detailed recognition history for each session.
- **FR-006**: The system must prevent duplicate attendance entries for the same learner within the same session window.
- **FR-007**: The system must keep committed attendance history immutable except for controlled, auditable corrections.
- **FR-008**: The system must store only derived biometric references and must not retain raw enrollment images after enrollment completes.
- **FR-009**: The system must protect administrative credentials and sensitive settings from plain-text exposure in stored data.
- **FR-010**: The system must continue operating when internet access is unavailable.
- **FR-011**: The system must store the active configuration values needed to explain and reproduce attendance decisions for a given session.

### Key Entities *(include if feature involves data)*

- **User Account**: A person enrolled in the system. Key attributes include identity details, active status, and audit timestamps.
- **Face Reference**: A derived biometric representation linked to a user account for recognition purposes.
- **Attendance Session**: A teaching session with course and class context, lifecycle status, and start and end timestamps.
- **Recognition Event**: A recorded recognition attempt within a session, including the result, time, and link to the relevant user or fallback status.
- **System Setting**: A configurable operational value that affects storage or attendance behavior.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A fresh installation can be initialized and used without manual storage setup in 100% of validation runs.
- **SC-002**: Existing records remain available after a restart in 100% of recovery tests.
- **SC-003**: Routine create and read operations for core records complete within 1 second in at least 95% of normal-load test runs.
- **SC-004**: Duplicate attendance attempts for the same learner within a session are blocked in 100% of duplicate-prevention test cases.
- **SC-005**: Attendance and recognition records remain auditable and unchanged after they are committed in 100% of integrity checks.
- **SC-006**: No raw enrollment images remain in storage after enrollment workflows in 100% of privacy verification checks.
- **SC-007**: Administrators can update a stored setting and see the updated value apply to the next relevant session in 100% of acceptance tests.

## Assumptions

- Primary users are system administrators and lecturers who manage attendance data and configuration.
- This feature covers local persistence and retrieval only; synchronization with external services is out of scope.
- Attendance history is retained according to project policy unless a later specification defines a narrower retention rule.
- The system may use safe default values when a stored configuration item is missing or invalid.