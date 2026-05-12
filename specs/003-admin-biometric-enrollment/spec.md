# Feature Specification: Admin User and Biometric Enrollment

**Feature Branch**: `003-admin-biometric-enrollment`  
**Created**: 2026-04-25  
**Status**: Draft  
**Input**: User description: "Module 3: Phan he Quan tri Nguoi dung va Dang ky Sinh trac hoc"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Register a New User Identity (Priority: P1)

As an administrator, I can create a new user profile and complete biometric enrollment in one guided flow so the person is ready for attendance recognition.

**Why this priority**: Without a completed enrollment flow, no new person can be recognized in attendance sessions.

**Independent Test**: Can be fully tested by starting enrollment for a new person, capturing required samples, finishing enrollment, and confirming a reusable biometric reference is available for later attendance matching.

**Acceptance Scenarios**:

1. **Given** an administrator is authenticated and enrollment mode is active, **When** the administrator enters required identity information and confirms enrollment start, **Then** the system creates an enrollment session tied to that user profile.
2. **Given** an active enrollment session, **When** the user follows the guided capture prompts and enough valid samples are collected, **Then** the system stores one finalized biometric reference for that user and marks enrollment as completed.

---

### User Story 2 - Guided Capture Quality Control (Priority: P2)

As an administrator, I receive clear step-by-step guidance and quality feedback during capture so low-quality images are rejected before final enrollment.

**Why this priority**: High-quality enrollment data directly affects downstream recognition reliability.

**Independent Test**: Can be tested by running enrollment with mixed-quality samples and verifying only samples that meet quality rules are accepted toward completion.

**Acceptance Scenarios**:

1. **Given** an active enrollment session, **When** a captured sample fails quality rules, **Then** the system rejects that sample, explains the reason, and keeps the session active.
2. **Given** an active enrollment session, **When** a captured sample passes quality rules, **Then** the system accepts the sample and updates progress toward completion.

---

### User Story 3 - Privacy-Safe Completion and Auditability (Priority: P3)

As an administrator, I need enrollment to remove raw facial images immediately after feature extraction while still keeping enough audit history to prove who performed enrollment and when.

**Why this priority**: The feature must satisfy privacy requirements while preserving accountability for administrative actions.

**Independent Test**: Can be tested by completing and cancelling enrollments, then verifying no raw images remain and required audit records still exist.

**Acceptance Scenarios**:

1. **Given** enrollment completes successfully, **When** feature extraction finishes, **Then** all raw image data from that session is irreversibly deleted before the session is marked complete.
2. **Given** enrollment is cancelled or fails before completion, **When** the session closes, **Then** all captured raw image data from that attempt is irreversibly deleted and the failure reason is recorded.

### Edge Cases

- What happens when the administrator starts enrollment for a user that already has an active enrollment session?
- What happens when capture is interrupted after some valid samples are accepted but before reaching the required minimum?
- How does the system handle two users with identical display names but different institutional identifiers?
- How does the system behave when storage capacity is insufficient during enrollment finalization?
- What happens when a finalized enrollment is retried for the same user in the same day?

## Constitution Alignment *(mandatory)*

- **Attendance Integrity**: Enrollment must create exactly one active biometric reference per target user for a single completion event, and every enrollment action must be attributable to a responsible administrator to prevent identity ambiguity in later attendance sessions.
- **Privacy by Design**: Raw facial image data is transient and must be deleted immediately after extraction or when a session ends; only the minimum required biometric reference and audit metadata are retained.
- **Offline-First Reliability**: Enrollment runs fully on local resources and remains available without internet connectivity, including profile creation, sample capture, completion, cancellation, and audit logging.
- **Deterministic AI Pipeline**: Enrollment processing follows a consistent ordered flow (capture -> quality check -> feature extraction -> aggregate reference -> persistence) so identical valid inputs produce the same acceptance decisions under unchanged thresholds.
- **Measurable Quality Gates**: The feature must demonstrate enrollment completion rate, average enrollment duration, rejection-rate visibility, and verified zero raw-image persistence after session closure.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST restrict access to enrollment operations to administrators with valid active privileges.
- **FR-002**: System MUST allow an administrator to create a new user profile with required identity fields before capture begins.
- **FR-003**: System MUST create an explicit enrollment session record containing administrator identity, target user identity, start time, and session status.
- **FR-004**: System MUST provide a guided capture workflow that includes a live camera preview, reports current progress, provides an explicit capture action (e.g. button or hotkey), and displays required remaining samples.
- **FR-005**: System MUST evaluate each captured sample against predefined enrollment quality rules and classify it as accepted or rejected.
- **FR-006**: System MUST present rejection reasons for failed samples so the administrator can correct posture, distance, or framing.
- **FR-007**: System MUST finalize enrollment only after the minimum required number of accepted samples is reached.
- **FR-008**: System MUST compute one aggregate biometric reference from accepted samples and store it as the user enrollment result.
- **FR-009**: System MUST permanently delete all raw facial image data from the enrollment attempt immediately after feature extraction or session termination.
- **FR-010**: System MUST preserve an enrollment audit trail that includes session outcome (completed, cancelled, failed), timestamps, and acting administrator identity.
- **FR-011**: System MUST prevent parallel active enrollment sessions for the same target user.
- **FR-012**: System MUST support administrator-initiated cancellation at any point and execute the same raw-image deletion guarantees as failed sessions.
- **FR-013**: System MUST function without internet connectivity for all core enrollment actions and queue no required step for online-only completion.

### Key Entities *(include if feature involves data)*

- **User Profile**: Canonical identity of a person being enrolled, including institutional identifiers and display metadata used in attendance flows.
- **Enrollment Session**: Lifecycle record of one biometric registration attempt, including operator, target user, progress, outcome, and timestamps.
- **Enrollment Sample Assessment**: Per-capture decision record containing acceptance result and quality rejection reason when applicable.
- **Biometric Reference**: Finalized aggregate feature representation linked to one user profile and used by attendance recognition.
- **Enrollment Audit Record**: Immutable accountability log for administrative enrollment actions and outcomes.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: At least 95% of standard enrollment attempts are completed by administrators in 3 minutes or less under normal room lighting.
- **SC-002**: At least 98% of completed enrollments produce a reusable biometric reference without requiring a second full enrollment attempt.
- **SC-003**: 100% of completed, cancelled, and failed enrollment sessions leave zero retained raw facial image files or blobs after session closure verification.
- **SC-004**: 100% of enrollment sessions contain a complete audit trail with administrator identity, timestamps, and final outcome.
- **SC-005**: In user acceptance validation, at least 90% of administrators can complete first-time enrollment without external training materials.
- **SC-006**: Duplicate active enrollment sessions for the same target user occur in 0% of tested concurrency scenarios.

## Assumptions

- Administrators already have access to an existing secure sign-in flow and role assignments.
- Enrollment is performed on a workstation with a functioning camera and stable local storage.
- A user can have only one active biometric reference used for attendance at any given time.
- Historical audit records are retained according to institutional policy outside this feature's scope.
