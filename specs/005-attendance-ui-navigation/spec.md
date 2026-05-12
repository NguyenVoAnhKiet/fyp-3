# Feature Specification: Attendance UI Navigation Architecture

**Feature Branch**: `005-attendance-ui-navigation`  
**Created**: 2026-04-26  
**Status**: Draft  
**Input**: User description: "## Module 5: Kiến trúc Giao diện và Điều hướng (UI/UX Architecture) Sử dụng PyQt5 hoặc Tkinter, module này đóng vai trò lớp vỏ thị giác bao bọc toàn bộ hệ thống. Nội dung triển khai bao gồm việc xây dựng khung ứng dụng chính, quản lý các trạng thái màn hình (từ màn hình chờ IDLE sang màn hình điểm danh trực tiếp). Yêu cầu kỹ thuật trọng tâm là hiển thị luồng video từ camera một cách mượt mà, duy trì tốc độ khung hình trên 24 FPS. Phân hệ này cũng chịu trách nhiệm tiếp nhận các lệnh từ phím tắt (S, E, Q) và cung cấp các phản hồi thị giác rõ ràng bằng mã màu (Xanh, Vàng, Đỏ) dựa trên trạng thái điểm danh."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Operate Attendance Screen States (Priority: P1)

As a lecturer, I need the application to move clearly between idle and live attendance views so I can run attendance sessions without confusion.

**Why this priority**: State transitions define whether attendance is operational; unclear transitions block core classroom use.

**Independent Test**: Can be fully tested by starting from IDLE, triggering session start, verifying transition to live attendance view, then ending session and verifying return to IDLE with correct visual indicators.

**Acceptance Scenarios**:

1. **Given** the system is in IDLE state, **When** a lecturer starts an attendance session, **Then** the interface switches to the live attendance screen and shows that attendance is active.
2. **Given** the system is in live attendance state, **When** the lecturer ends the session, **Then** the interface returns to IDLE and no longer presents the session as active.

---

### User Story 2 - View Smooth Live Camera Feed (Priority: P2)

As a lecturer, I need a smooth live camera preview so I can confidently monitor attendee recognition activity in real time.

**Why this priority**: Smooth video is required for trust and usability during live operation and directly affects operator effectiveness.

**Independent Test**: Can be fully tested by running a live attendance session for a fixed interval and confirming the displayed feed remains at or above the required frame-rate threshold under normal classroom conditions.

**Acceptance Scenarios**:

1. **Given** a live attendance session is active, **When** the camera feed is displayed continuously for at least 60 seconds, **Then** the displayed stream remains smooth and maintains an effective frame rate of at least 24 FPS.
2. **Given** the camera feed is temporarily unavailable, **When** the UI cannot render new frames, **Then** the interface shows a clear non-blocking status message and remains responsive to operator commands.

---

### User Story 3 - Control Workflow with Hotkeys and Colors (Priority: P3)

As a lecturer, I need keyboard shortcuts and color-coded feedback so I can operate quickly and interpret attendance outcomes at a glance.

**Why this priority**: Fast controls and immediate visual cues reduce operator error and speed up in-class interactions.

**Independent Test**: Can be fully tested by pressing configured hotkeys in each valid state and verifying the expected action and corresponding color feedback are shown consistently.

**Acceptance Scenarios**:

1. **Given** the attendance UI is focused, **When** the lecturer presses `S`, `E`, or `Q` in a valid context, **Then** the corresponding action executes and visible state feedback updates immediately.
2. **Given** a recognition outcome is received, **When** the UI updates status feedback, **Then** it uses green for success, yellow for caution/pending, and red for warning/failure in a consistent legend.

---

### Edge Cases

- A hotkey is pressed while the UI is not in a state that allows the requested action.
- Multiple hotkeys are pressed rapidly during state transition.
- The camera device disconnects during a live session and reconnects later.
- Recognition outcome updates arrive faster than the UI refresh cadence.
- The application window is minimized or temporarily unfocused during live attendance.

## Constitution Alignment *(mandatory)*

- **Attendance Integrity**: The UI presents active/idle states and outcome cues unambiguously to reduce operator actions that could cause duplicate or invalid attendance handling.
- **Privacy by Design**: The interface displays only operational attendance feedback and avoids exposing unnecessary biometric internals or retained raw imagery.
- **Offline-First Reliability**: All UI navigation and live-session controls remain available without internet dependency, with local status messaging for degraded camera or pipeline conditions.
- **Deterministic AI Pipeline**: The UI consumes finalized pipeline outcomes in order and renders deterministic, color-mapped statuses without altering underlying recognition decisions.
- **Measurable Quality Gates**: Validation covers frame-rate threshold compliance, keyboard control responsiveness, state-transition correctness, and color-feedback consistency.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST provide a primary application shell that can present at least IDLE and live attendance states.
- **FR-002**: The system MUST allow transition from IDLE to live attendance state when a session start action is initiated.
- **FR-003**: The system MUST allow transition from live attendance state back to IDLE when a session end action is initiated.
- **FR-004**: The system MUST render a continuous live camera stream while in live attendance state.
- **FR-005**: The system MUST maintain a displayed camera stream frame rate of at least 24 FPS under normal operating conditions.
- **FR-006**: The system MUST keep the UI responsive to operator input while rendering live video.
- **FR-007**: The system MUST support keyboard shortcuts for start (`S`), end (`E`), and quit (`Q`) actions.
- **FR-008**: The system MUST ignore or safely reject invalid hotkey actions for the current state and provide clear user feedback.
- **FR-009**: The system MUST provide color-coded visual feedback for attendance outcomes using green, yellow, and red with consistent meaning.
- **FR-010**: The system MUST present a visible status indicator for current attendance mode (IDLE or live attendance).
- **FR-011**: The system MUST present a recoverable, non-blocking warning when camera frames cannot be acquired.
- **FR-012**: The system MUST continue operating core navigation and control workflows when internet connectivity is unavailable.

### Key Entities *(include if feature involves data)*

- **UI State**: Represents the current interface mode, including IDLE and live attendance, with allowed transitions and visible indicators.
- **Video Stream Status**: Represents runtime camera feed health, including frame cadence, availability, and user-facing status messages.
- **Operator Command**: Represents a keyboard-triggered UI action (start, end, quit) and its validation outcome.
- **Visual Outcome Signal**: Represents the standardized color-coded feedback shown for attendance status updates.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In user acceptance tests, lecturers complete IDLE-to-live-to-IDLE workflow in under 10 seconds for 95% of attempts.
- **SC-002**: During a 10-minute live session test, the displayed camera feed remains at or above 24 FPS for at least 95% of sampled intervals.
- **SC-003**: 99% of valid hotkey presses trigger the expected action and visible UI response within 200 milliseconds.
- **SC-004**: 100% of attendance status messages in test scenarios use the defined green/yellow/red mapping consistently.
- **SC-005**: In offline operation tests, 100% of core UI controls (start, end, quit, state navigation) remain available without internet.
- **SC-006**: At least 90% of pilot users report they can correctly interpret current attendance state and outcome signals without additional guidance.

## Assumptions

- The camera and AI pipeline modules provide frame and recognition outcome inputs through existing internal interfaces.
- The start/end session business logic is owned by adjacent modules; this feature focuses on UI flow, state visibility, and operator interaction.
- Desktop operation is the primary target context; mobile and web interfaces are out of scope.
- Keyboard focus is available on the main attendance window during normal operator usage.
