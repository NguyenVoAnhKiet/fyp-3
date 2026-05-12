# Feature Specification: AI Engine & Vision Pipeline

**Feature Branch**: `[002-ai-vision-pipeline]`  
**Created**: 2026-04-24  
**Status**: Draft  
**Input**: User description: "## Module 2: Động cơ AI và Xử lý Luồng hình ảnh (AI Engine & Vision Pipeline)

Đây là trái tim tính toán của hệ thống điểm danh. Module này đóng gói toàn bộ các tác vụ nặng liên quan đến thị giác máy tính và học sâu, được thiết kế để chạy trên một luồng (thread) hoàn toàn tách biệt với giao diện. Nhiệm vụ của nó là tiếp nhận luồng video liên tục từ camera, thực hiện phát hiện khuôn mặt, sau đó chấm điểm độ thực tế (Liveness Score). Nếu vượt qua bài kiểm tra chống giả mạo, hình ảnh tiếp tục được trích xuất vector đặc trưng và đối chiếu với cơ sở dữ liệu. Kết quả cuối cùng sẽ được trả về dưới dạng sự kiện (event) để các module khác tiếp nhận."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Process Live Camera Stream Safely (Priority: P1)

As a lecturer running attendance, I want each camera frame to be processed through anti-spoofing and recognition in the correct order, so the system records only trustworthy identities.

**Why this priority**: This is the core value of the module. If ordered processing fails, attendance reliability and anti-fraud guarantees fail.

**Independent Test**: Feed a controlled mix of real and spoof face samples into the pipeline and verify that only real faces can produce recognized-identity events.

**Acceptance Scenarios**:

1. **Given** a camera stream with a clearly visible real face, **When** the pipeline processes the frame, **Then** it emits a recognition-success event with identity and confidence metadata.
2. **Given** a camera stream with a spoof attempt, **When** the liveness stage evaluates the frame, **Then** it emits a spoof-warning event and does not continue to recognition.

---

### User Story 2 - Keep UI Responsive During AI Workloads (Priority: P2)

As an operator, I want heavy vision processing to run independently from the interface, so live attendance view remains responsive while recognition is running.

**Why this priority**: Classroom operations depend on smooth interaction. A stalled UI during processing causes operational disruption.

**Independent Test**: Run continuous camera processing under expected classroom load and verify that UI interactions and status refresh remain responsive.

**Acceptance Scenarios**:

1. **Given** continuous frame processing, **When** users interact with attendance controls, **Then** the interface remains responsive without blocking for pipeline completion.
2. **Given** temporary processing spikes, **When** frame queue pressure increases, **Then** the module degrades safely without freezing the application.

---

### User Story 3 - Publish Standardized AI Events for Downstream Modules (Priority: P3)

As a downstream attendance module, I want standardized AI result events, so I can update session history and attendance state consistently.

**Why this priority**: Stable event contracts are required for integration, but they depend on the core processing behavior already working.

**Independent Test**: Consume emitted events from a test subscriber and verify event type, required payload fields, and event timing for success, unknown, and spoof outcomes.

**Acceptance Scenarios**:

1. **Given** a recognized real face, **When** the pipeline completes processing, **Then** it emits one success event with required identity, score, and timestamp fields.
2. **Given** an unrecognized but real face, **When** recognition confidence is below threshold, **Then** it emits an unknown-identity event without creating false identity claims.

### Edge Cases

- No face appears in frame for an extended period and the module must continue polling without emitting false events.
- Multiple faces appear in the same frame and the module must apply a deterministic selection policy before emitting any attendance-related event.
- Camera stream drops or device temporarily disconnects and the module must recover automatically when the stream returns.
- Liveness result is borderline around threshold and the module must behave consistently according to configured threshold rules.
- Recognition reference data is unavailable for a subset of users and the module must emit unknown outcomes rather than failing the pipeline.

## Constitution Alignment *(mandatory)*

- **Attendance Integrity**: The module emits attendance-relevant events only after successful liveness and recognition stages, and prevents spoofed inputs from being treated as valid attendance.
- **Privacy by Design**: The module processes transient frame data for inference only and publishes minimum event payload required for downstream attendance decisions.
- **Offline-First Reliability**: The full detect-liveness-recognize flow and event emission operate without internet dependency during active sessions.
- **Deterministic AI Pipeline**: Processing order is fixed as detect -> liveness -> recognize; threshold-based branching is explicit and reproducible for the same inputs.
- **Measurable Quality Gates**: The module defines measurable targets for per-person processing latency, spoof rejection effectiveness, recognition reliability, and event delivery consistency.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system must ingest frames continuously from the configured camera source during active attendance operation.
- **FR-002**: The system must run face detection before any liveness or recognition decision is made.
- **FR-003**: The system must evaluate liveness for each detected face candidate before recognition is attempted.
- **FR-004**: The system must block recognition for any candidate that fails liveness and must emit a spoof-warning event.
- **FR-005**: The system must perform face matching only for candidates that pass liveness checks.
- **FR-006**: The system must emit standardized result events for at least these outcomes: recognized identity, unknown identity, spoof warning, and no-face-detected.
- **FR-007**: Each emitted event must include session context, event type, event timestamp, and confidence metadata required by downstream attendance workflows.
- **FR-008**: The system must execute heavy vision processing independently from UI update loops so interface interactions remain responsive.
- **FR-009**: The system must handle temporary camera interruption by transitioning to a recoverable state and resuming processing when frames are available again.
- **FR-010**: The system must use configurable liveness and similarity thresholds and apply those values consistently within a session.
- **FR-011**: The system must avoid persisting raw camera frames as part of routine pipeline execution unless explicitly required by a separate approved audit workflow.
- **FR-012**: The system must operate fully in offline mode and must not require network calls to produce liveness and recognition events.

### Key Entities *(include if feature involves data)*

- **Frame Processing Task**: A single unit of camera input processing containing frame timestamp, session context, and processing state.
- **Liveness Decision**: The anti-spoofing outcome for a detected face candidate, including score, threshold context, and decision status.
- **Recognition Decision**: The identity matching outcome for a live face candidate, including matched identity (if any), confidence, and threshold context.
- **Vision Event**: The normalized event payload emitted for downstream modules, including event type, session context, timing, and decision metadata.
- **Pipeline Runtime State**: Operational state for the vision worker, including active, degraded, recovering, and stopped states.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: During normal classroom load tests, at least 95% of valid face candidates produce a final event within 2 seconds from first detection.
- **SC-002**: In controlled spoof test scenarios, at least 98% of spoof attempts are emitted as spoof-warning events and do not produce recognition-success events.
- **SC-003**: In controlled known-user scenarios, at least 95% of real-user attempts produce either a correct recognized-identity event or an explicit unknown-identity event without false identity assignment.
- **SC-004**: Under continuous processing for 60 minutes, UI control actions remain responsive with no blocking interaction longer than 300 milliseconds in at least 95% of sampled actions.
- **SC-005**: Event consumers receive required payload fields for 100% of emitted events in contract validation tests.
- **SC-006**: In offline test runs, the module maintains full event generation behavior for the complete session duration in 100% of test cases.

## Assumptions

- The camera device can provide a stable frame stream under normal classroom lighting conditions.
- Enrollment reference data for registered users already exists and is accessible to this module through the local system.
- Threshold defaults are defined by project policy and may be tuned via the configuration module without changing this feature scope.
- This feature covers inference-time processing and event emission only; UI presentation and attendance record persistence are handled by other modules.
