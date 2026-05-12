# Feature Specification: Attendance Session Processing

**Feature Branch**: `004-attendance-session-processing`  
**Created**: 2026-04-26  
**Status**: Draft  
**Input**: User description: "Module 4: Phan he Diem danh va Xu ly Phien hoc. Module nay phuc vu truc tiep cho nguoi dung cuoi (Giang vien) voi muc tieu van hanh buoi hoc mot cach tron tru nhat. Khoi dau bang viec tao lap mot phien diem danh moi gan lien voi ten mon hoc va lop hoc cu the, he thong se chuyen sang trang thai hoat dong (ACTIVE). Trong suot qua trinh nay, module se lien tuc lang nghe ket qua tra ve tu Dong co AI, doi chieu du lieu de ngan chan viec ghi nhan trung lap cho mot sinh vien, dong thoi cap nhat trang thai (Thanh cong hoac Canh bao gia mao) vao co so du lieu lich su theo thoi gian thuc."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Start Attendance Session (Priority: P1)

As a lecturer, I create a new attendance session with course and class identifiers so the class can move into an active attendance state immediately.

**Why this priority**: A session must exist before any attendance event can be processed, so this is the entry point for all other value.

**Independent Test**: Can be fully tested by creating a session with valid class metadata and confirming the session transitions to ACTIVE and is visible for event intake.

**Acceptance Scenarios**:

1. **Given** a lecturer is authenticated and no session is active, **When** the lecturer submits course name and class code, **Then** the system creates a new attendance session and marks it as ACTIVE.
2. **Given** a lecturer omits required session metadata, **When** the lecturer attempts to start a session, **Then** the system rejects session creation with a clear validation message and remains in IDLE.

---

### User Story 2 - Process Live Attendance Events (Priority: P2)

As a lecturer, I need AI recognition results to be processed in real time so each student is marked accurately while duplicate check-ins are prevented.

**Why this priority**: Real-time, duplicate-safe recording is the core function of classroom attendance operations.

**Independent Test**: Can be fully tested by feeding a stream of recognized student events into an ACTIVE session and verifying first valid event is recorded while repeated events for the same student in the same session are blocked.

**Acceptance Scenarios**:

1. **Given** an ACTIVE session and a valid recognition result for a student not yet recorded in that session, **When** the event is received, **Then** the system stores a successful attendance record with a timestamp.
2. **Given** an ACTIVE session and a repeated recognition result for the same student already recorded successfully, **When** the event is received again, **Then** the system does not create a duplicate attendance record.

---

### User Story 3 - Handle Spoof Warnings in Session History (Priority: P3)

As a lecturer, I need spoof-detected events to be logged as warnings so I can review suspicious activity without contaminating successful attendance results.

**Why this priority**: Spoof transparency protects attendance integrity and gives instructors actionable audit data.

**Independent Test**: Can be fully tested by submitting spoof-flagged events during an ACTIVE session and confirming warning history entries are stored without marking the student as present.

**Acceptance Scenarios**:

1. **Given** an ACTIVE session and a spoof-flagged recognition event, **When** the event is processed, **Then** the system records a warning outcome in session history and does not create a successful attendance record.
2. **Given** a student has both spoof warnings and one valid recognition in the same session, **When** history is reviewed, **Then** all outcomes are preserved chronologically with outcome type clearly distinguishable.

---

### Edge Cases

- A recognition event arrives when no session is ACTIVE.
- AI emits an event with missing student identity or missing outcome classification.
- Multiple identical events for the same student arrive within a short time window.
- Spoof warning and successful recognition for the same student are produced close together.
- Session is manually ended while events are still arriving from the vision pipeline.

## Constitution Alignment *(mandatory)*

- **Attendance Integrity**: Only one successful attendance entry per student per session is allowed; repeated recognitions are treated as duplicates and not counted as new attendance.
- **Privacy by Design**: This feature stores attendance outcomes and identifiers needed for auditability, and does not require raw face image persistence.
- **Offline-First Reliability**: Session start and event recording operate against local storage and remain functional without internet connectivity.
- **Deterministic AI Pipeline**: The module consumes finalized AI outcomes from the detect -> liveness -> recognize sequence and maps each event to a deterministic attendance or warning result.
- **Measurable Quality Gates**: Validation includes duplicate-prevention checks, spoof-warning traceability, event-order consistency, and timely history updates during active sessions.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST allow a lecturer to create an attendance session using course name and class identifier.
- **FR-002**: The system MUST transition a newly created attendance session to ACTIVE status immediately after successful creation.
- **FR-003**: The system MUST reject session activation when required session metadata is incomplete.
- **FR-004**: The system MUST accept recognition outcomes only while a session is ACTIVE.
- **FR-005**: The system MUST persist each first-time successful recognition for a student as one attendance record within the active session.
- **FR-006**: The system MUST prevent creation of duplicate successful attendance records for the same student within the same session.
- **FR-007**: The system MUST persist spoof-detected outcomes as warning history entries tied to the active session.
- **FR-008**: The system MUST keep successful attendance outcomes and spoof warnings distinguishable in session history.
- **FR-009**: The system MUST timestamp every stored outcome using a consistent session timeline.
- **FR-010**: The system MUST ignore or reject malformed AI outcomes that lack required identity or outcome fields and log them for audit review.
- **FR-011**: The system MUST continue processing valid events when internet connectivity is unavailable.
- **FR-012**: The system MUST stop accepting new attendance outcomes after the session leaves ACTIVE state.

### Key Entities *(include if feature involves data)*

- **Attendance Session**: Represents one class attendance window, including course metadata, class metadata, lifecycle status, and start/end timestamps.
- **Recognition Outcome Event**: Represents one processed AI result consumed by this module, including student identity, outcome type (success or spoof warning), confidence metadata, and event timestamp.
- **Attendance Record**: Represents a successful, non-duplicate presence confirmation for one student in one attendance session.
- **Session History Entry**: Represents an immutable audit item for each processed outcome, including warnings, validation rejects, and successful records.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Lecturers can start a new attendance session in under 30 seconds from entering class metadata.
- **SC-002**: At least 99% of valid recognition outcomes appear in session history within 2 seconds during normal operation.
- **SC-003**: Duplicate successful attendance rate for the same student in the same session is 0% in acceptance and regression tests.
- **SC-004**: 100% of spoof-detected outcomes are recorded as warnings and never counted as successful attendance.
- **SC-005**: At least 95% of pilot-session runs complete without manual correction of attendance history.
- **SC-006**: 100% of stored records in this feature contain no raw face image payloads.

## Assumptions

- Lecturers initiating sessions are already authenticated by existing administration and access-control flows.
- AI engine outputs already include a normalized student identifier and outcome type before reaching this module.
- Attendance is tracked per session; cross-session duplicate detection is out of scope.
- Session-close controls and user interface triggers are provided by adjacent modules and invoke this module through existing service boundaries.
