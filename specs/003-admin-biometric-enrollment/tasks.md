# Tasks: Admin User and Biometric Enrollment

**Input**: Design documents from `/specs/003-admin-biometric-enrollment/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, quickstart.md

**Tests**: Tests are required for this feature because the spec has privacy, offline, and auditability requirements that must be verified automatically.

**Organization**: Tasks are grouped by user story so each story can be implemented and validated independently.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Prepare the test surface and feature-specific files for enrollment work

- [X] T001 [P] Create enrollment test scaffolding in `tests/unit/test_enrollment_service.py` and `tests/integration/test_enrollment_flow.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core schema, models, and repositories that all enrollment stories depend on

**Checkpoint**: No user story work can begin until this phase is complete

- [X] T002 Update `src/core/schema.py` with enrollment session, sample assessment, and audit tables plus active-session uniqueness enforcement
- [X] T003 [P] Add enrollment dataclasses in `src/models/entities.py` for session, sample assessment, and audit records
- [X] T004 [P] Add repository modules in `src/repositories/enrollment_session_repository.py`, `src/repositories/enrollment_sample_repository.py`, and `src/repositories/enrollment_audit_repository.py`
- [X] T005 Update `src/services/security.py` and `src/services/enrollment_service.py` with admin-only access checks and raw-image cleanup hooks

---

## Phase 3: User Story 1 - Register a New User Identity (Priority: P1) 🎯 MVP

**Goal**: Create a new user enrollment session and persist one derived biometric reference when capture completes successfully

**Independent Test**: Start an enrollment session for a new user, complete sample collection, and verify one biometric reference is stored while raw images are removed

### Tests for User Story 1

- [X] T006 [P] [US1] Add unit coverage for session creation and final reference persistence in `tests/unit/test_enrollment_service.py`
- [X] T007 [P] [US1] Add integration coverage for a successful enrollment completion in `tests/integration/test_enrollment_flow.py`

### Implementation for User Story 1

- [X] T008 [P] [US1] Implement session creation and lookup in `src/repositories/enrollment_session_repository.py`
- [X] T009 [US1] Implement guided completion flow and derived biometric reference persistence in `src/services/enrollment_service.py` using `src/repositories/face_reference_repository.py`

**Checkpoint**: User Story 1 should now be fully functional and testable on its own

---

## Phase 4: User Story 2 - Guided Capture Quality Control (Priority: P2)

**Goal**: Reject low-quality samples with clear feedback while advancing accepted samples toward completion

**Independent Test**: Run enrollment with mixed-quality captures and verify rejected samples are not counted toward completion, while accepted samples do advance progress

### Tests for User Story 2

- [X] T010 [P] [US2] Add unit coverage for sample acceptance, rejection, and progress updates in `tests/unit/test_enrollment_service.py`
- [X] T011 [P] [US2] Add integration coverage for mixed-quality capture handling in `tests/integration/test_enrollment_quality.py`

### Implementation for User Story 2

- [X] T012 [P] [US2] Implement sample assessment storage in `src/repositories/enrollment_sample_repository.py`
- [X] T013 [US2] Implement quality-rule evaluation and rejection feedback in `src/services/enrollment_service.py` using `src/repositories/enrollment_audit_repository.py`

**Checkpoint**: User Story 2 should work independently and keep User Story 1 behavior intact

---

## Phase 5: User Story 3 - Privacy-Safe Completion and Auditability (Priority: P3)

**Goal**: Delete raw images immediately after enrollment exits while preserving a usable audit trail for completed, cancelled, and failed sessions

**Independent Test**: Complete, cancel, and fail enrollment attempts, then verify raw images are gone and audit/session records still explain what happened

### Tests for User Story 3

- [X] T014 [P] [US3] Add unit coverage for cancellation, failure cleanup, and audit retention in `tests/unit/test_enrollment_service.py`
- [X] T015 [P] [US3] Add integration coverage for raw-image deletion and session closure in `tests/integration/test_enrollment_privacy.py`

### Implementation for User Story 3

- [X] T016 [P] [US3] Implement terminal session outcomes in `src/repositories/enrollment_session_repository.py` and `src/repositories/enrollment_audit_repository.py`
- [X] T017 [US3] Implement cancellation and failure cleanup in `src/services/enrollment_service.py` so raw images are deleted immediately on exit

**Checkpoint**: All user stories should now be independently functional

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final validation and documentation updates that span multiple stories

- [X] T018 [P] Update `specs/003-admin-biometric-enrollment/quickstart.md` with the implemented validation commands and scenario steps
- [X] T019 Run `PYTHONPATH=src pytest tests/` and `ruff check src/` to verify privacy, offline, and enrollment behavior
- [X] T020 [P] Add edge-case regression coverage for duplicate active sessions and interrupted enrollment cleanup in `tests/integration/test_enrollment_privacy.py`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies; can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion and blocks all user stories
- **User Stories (Phase 3+)**: All depend on Foundational completion
- **Polish (Final Phase)**: Depends on the desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational; no dependency on other stories
- **User Story 2 (P2)**: Can start after Foundational; may reuse User Story 1 components but must remain independently testable
- **User Story 3 (P3)**: Can start after Foundational; may reuse User Story 1 and 2 components but must remain independently testable

### Within Each User Story

- Tests are written before implementation and should fail first
- Models and repositories before services
- Core implementation before integration verification
- Story complete before moving to the next priority

### Parallel Opportunities

- Setup task T001 can run alongside other documentation or file-scaffolding work
- Foundational tasks T003 and T004 can run in parallel after T002 is started
- User Story 1 tests T006 and T007 can run in parallel
- User Story 2 tests T010 and T011 can run in parallel
- User Story 3 tests T014 and T015 can run in parallel
- Different user stories can be worked on in parallel once the foundational phase is complete

---

## Parallel Example: User Story 1

```bash
# Run the User Story 1 tests together:
Task: "Add unit coverage for session creation and final reference persistence in tests/unit/test_enrollment_service.py"
Task: "Add integration coverage for a successful enrollment completion in tests/integration/test_enrollment_flow.py"

# Implement the User Story 1 data path in sequence after the tests:
Task: "Implement session creation and lookup in src/repositories/enrollment_session_repository.py"
Task: "Implement guided completion flow and derived biometric reference persistence in src/services/enrollment_service.py using src/repositories/face_reference_repository.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational
3. Complete Phase 3: User Story 1
4. Stop and validate User Story 1 independently
5. Demo or release if the enrollment MVP is sufficient

### Incremental Delivery

1. Complete Setup and Foundational work
2. Deliver User Story 1 as the MVP
3. Add User Story 2 for capture quality control
4. Add User Story 3 for privacy-safe cleanup and auditability
5. Finish with cross-cutting validation and documentation

### Parallel Team Strategy

With multiple developers:

1. One developer can prepare schema and repository work while another prepares tests
2. After the foundational phase, User Story 1, 2, and 3 can proceed in parallel on separate files
3. Finish by running the full test suite and quickstart validation together

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] labels map each task to a specific user story for traceability
- This feature requires automated validation for privacy cleanup, offline behavior, and auditability
- Keep the implementation focused on the existing single-project Python layout in `src/` and `tests/`