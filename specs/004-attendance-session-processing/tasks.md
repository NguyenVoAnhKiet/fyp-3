# Tasks: Attendance Session Processing

**Input**: Design documents from `/specs/004-attendance-session-processing/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Included because this feature affects attendance integrity, spoof handling, and offline reliability.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and shared test scaffolding needed before implementation

- [x] T001 [P] Add shared attendance-session and recognition-event fixtures in `tests/conftest.py`
- [x] T002 [P] Add normalized attendance-event samples for contract tests in `tests/contract/test_vision_event_contract.py`
- [x] T003 [P] Add offline-mode and session-lifecycle helper coverage in `tests/integration/test_offline_behavior.py`
- [x] T004 Add ISO 8601 timestamp validation expectations in `tests/unit/test_attendance_service.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T005 [P] Define attendance session and outcome entities in `src/models/entities.py`
- [x] T006 [P] Extend session persistence helpers for active-session lifecycle in `src/repositories/session_repository.py`
- [x] T007 [P] Extend attendance persistence helpers for duplicate-safe writes in `src/repositories/attendance_repository.py`
- [x] T008 [P] Extend recognition event persistence helpers for auditable history writes in `src/repositories/recognition_event_repository.py`
- [x] T009 [P] Add session-state and outcome mapping helpers in `src/services/vision_event_adapter.py`
- [x] T010 Add attendance session orchestration service scaffolding in `src/services/attendance_service.py`
- [x] T011 Add shared validation rules for malformed event rejection and ISO 8601 timestamps in `src/utils/time_utils.py`
- [x] T012 Add foundational regression coverage for repository/service integration in `tests/unit/test_storage_repositories.py`

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Start Attendance Session (Priority: P1) 🎯 MVP

**Goal**: Allow a lecturer to create a new attendance session with course and class metadata and move it to ACTIVE state.

**Independent Test**: Create a session with valid metadata and confirm it becomes ACTIVE; invalid metadata must be rejected without creating an active session.

### Tests for User Story 1 (OPTIONAL - included for this feature) ⚠️

- [x] T013 [P] [US1] Add integration coverage for session start and ACTIVE transition in `tests/integration/test_attendance_history.py`
- [x] T014 [P] [US1] Add integration coverage for invalid session metadata rejection in `tests/integration/test_attendance_audit.py`

### Implementation for User Story 1

- [x] T015 [US1] Implement session creation and activation flow in `src/services/attendance_service.py`
- [x] T016 [US1] Persist new attendance session records in `src/repositories/session_repository.py`
- [x] T017 [P] [US1] Add validation for required course and class metadata in `src/services/attendance_service.py`
- [x] T018 [P] [US1] Ensure active-session lookup and lifecycle transitions in `src/repositories/session_repository.py`
- [x] T019 [US1] Add start-session behavior coverage in `tests/unit/test_attendance_service.py`

**Checkpoint**: User Story 1 should be fully functional and testable independently

---

## Phase 4: User Story 2 - Process Live Attendance Events (Priority: P2)

**Goal**: Consume AI recognition results in real time, persist the first successful attendance for each student, and block duplicates within the same session.

**Independent Test**: Feed repeated valid recognition events into an ACTIVE session and confirm the first event is recorded while duplicates are rejected and audited.

### Tests for User Story 2 (OPTIONAL - included for this feature) ⚠️

- [x] T020 [P] [US2] Add contract coverage for normalized attendance events in `tests/contract/test_vision_event_contract.py`
- [x] T021 [P] [US2] Add integration coverage for duplicate-safe attendance writes in `tests/integration/test_attendance_audit.py`
- [x] T022 [P] [US2] Add integration coverage for live event processing order in `tests/integration/test_vision_pipeline_flow.py`

### Implementation for User Story 2

- [x] T023 [US2] Implement event-to-attendance mapping for success outcomes in `src/services/vision_event_adapter.py`
- [x] T024 [US2] Implement duplicate-prevention logic for successful attendance in `src/services/attendance_service.py`
- [x] T025 [P] [US2] Persist first-time attendance records with timestamps in `src/repositories/attendance_repository.py`
- [x] T026 [P] [US2] Persist session history entries for success and duplicate-blocked outcomes in `src/repositories/recognition_event_repository.py`
- [x] T027 [US2] Add live event processing coverage in `tests/unit/test_vision_event_adapter.py`
- [x] T028 [US2] Add attendance service coverage for first-success and duplicate-blocked outcomes in `tests/unit/test_attendance_service.py`

**Checkpoint**: User Story 2 should be fully functional and testable independently

---

## Phase 5: User Story 3 - Handle Spoof Warnings in Session History (Priority: P3)

**Goal**: Store spoof-detected events as warnings in session history without counting them as successful attendance.

**Independent Test**: Submit spoof-flagged events during an ACTIVE session and confirm warning history is written while attendance remains unchanged.

### Tests for User Story 3 (OPTIONAL - included for this feature) ⚠️

- [x] T029 [P] [US3] Add spoof-warning contract coverage in `tests/contract/test_vision_event_contract.py`
- [x] T030 [P] [US3] Add integration coverage for spoof warnings in `tests/integration/test_attendance_audit.py`
- [x] T031 [P] [US3] Add offline-mode coverage for spoof and invalid event handling in `tests/integration/test_offline_behavior.py`

### Implementation for User Story 3

- [x] T032 [US3] Implement spoof-warning mapping in `src/services/vision_event_adapter.py`
- [x] T033 [US3] Persist spoof and invalid-event history entries in `src/repositories/recognition_event_repository.py`
- [x] T034 [US3] Ensure spoof warnings never create attendance records in `src/services/attendance_service.py`
- [x] T035 [P] [US3] Add audit-history coverage for spoof-warning and invalid-event outcomes in `tests/unit/test_attendance_service.py`
- [x] T036 [P] [US3] Add contract assertions for outcome mapping and required fields in `tests/contract/test_vision_event_contract.py`

**Checkpoint**: All user stories should now be independently functional

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [x] T037 [P] Update feature documentation to reflect implemented behavior in `specs/004-attendance-session-processing/quickstart.md`
- [x] T038 [P] Validate no raw biometric image persistence and offline-first behavior in `tests/integration/test_offline_behavior.py`
- [x] T039 [P] Validate end-to-end attendance history and audit integrity in `tests/integration/test_attendance_history.py`
- [x] T040 Run the feature validation suite described in `specs/004-attendance-session-processing/quickstart.md`
- [x] T041 Verify session lifecycle, duplicate prevention, and spoof warning paths in `tests/integration/test_attendance_audit.py`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3+)**: All depend on Foundational phase completion
  - User stories can then proceed in parallel (if staffed)
  - Or sequentially in priority order (P1 → P2 → P3)
- **Polish (Final Phase)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - May integrate with User Story 1 but should be independently testable
- **User Story 3 (P3)**: Can start after Foundational (Phase 2) - May integrate with User Story 1 and User Story 2 but should be independently testable

### Within Each User Story

- Tests (if included) MUST be written and FAIL before implementation
- Constitution-required validations (privacy/offline/integrity) MUST be included when impacted
- Models before services
- Services before repositories where orchestration is needed
- Core implementation before integration
- Story complete before moving to next priority

### Parallel Opportunities

- T005-T009 can run in parallel because they touch different files
- T013-T014 can run in parallel because they cover different scenarios
- T017-T018 can run in parallel because they touch different parts of the same service/repository boundary
- T020-T022 can run in parallel because they cover contract and integration surfaces
- T025-T026 can run in parallel because they touch different persistence helpers
- T029-T031 can run in parallel because they cover contract and offline behavior separately
- T037-T039 can run in parallel because they are documentation and validation updates

---

## Parallel Example: User Story 1

```bash
Task: "Add integration coverage for session start and ACTIVE transition in tests/integration/test_attendance_history.py"
Task: "Add integration coverage for invalid session metadata rejection in tests/integration/test_attendance_audit.py"
Task: "Add validation for required course and class metadata in src/services/attendance_service.py"
Task: "Ensure active-session lookup and lifecycle transitions in src/repositories/session_repository.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Test User Story 1 independently
5. Deploy/demo if ready

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → Deploy/Demo (MVP!)
3. Add User Story 2 → Test independently → Deploy/Demo
4. Add User Story 3 → Test independently → Deploy/Demo
5. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1
   - Developer B: User Story 2
   - Developer C: User Story 3
3. Stories complete and integrate independently

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Verify tests fail before implementing
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Avoid: vague tasks, same file conflicts, cross-story dependencies that break independence

## Validation

- Feature test suite run on 2026-04-26: `44 passed, 1 skipped`
