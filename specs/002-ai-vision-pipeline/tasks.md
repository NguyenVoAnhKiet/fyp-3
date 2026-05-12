# Tasks: AI Engine & Vision Pipeline

**Input**: Design documents from `/specs/002-ai-vision-pipeline/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Included because this feature changes anti-spoofing, offline processing, and threshold-governed AI behavior.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure for the vision pipeline module

- [X] T001 [P] Add frame-processing and pipeline-state dataclasses to `src/models/entities.py`
- [X] T002 [P] Add normalized vision event adapter helpers to `src/services/vision_event_adapter.py`
- [X] T003 [P] Add fake camera and event-sink fixtures to `tests/conftest.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T004 Implement threaded pipeline lifecycle, bounded queues, and camera recovery in `src/services/vision_pipeline_service.py`
- [X] T005 Implement session threshold snapshot loading and deterministic face selection in `src/services/vision_pipeline_service.py`
- [X] T006 [P] Implement vision event contract constants and result mapping in `src/services/vision_event_adapter.py`

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Process Live Camera Stream Safely (Priority: P1) 🎯 MVP

**Goal**: Process live frames in the detect -> liveness -> recognize order and stop spoofed inputs before recognition.

**Independent Test**: A controlled real-face frame emits a recognized or unknown event, while a spoof frame stops at liveness and emits a spoof warning.

### Tests for User Story 1 (OPTIONAL - only if tests requested) ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T007 [P] [US1] Add unit tests for detect -> liveness -> recognize ordering in `tests/unit/test_vision_pipeline_order.py`
- [X] T008 [P] [US1] Add integration tests for real-face and spoof outcomes in `tests/integration/test_vision_pipeline_flow.py`

### Implementation for User Story 1

- [X] T009 [US1] Implement face detection, liveness scoring, and recognition branching in `src/services/vision_pipeline_service.py`
- [X] T010 [US1] Wire no-face-detected and spoof-warning paths into `src/services/vision_pipeline_service.py`
- [X] T011 [US1] Emit normalized recognized and unknown identity events through `src/services/vision_event_adapter.py`

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently

---

## Phase 4: User Story 2 - Keep UI Responsive During AI Workloads (Priority: P2)

**Goal**: Keep the AI worker off the UI path so live attendance controls remain responsive during continuous processing.

**Independent Test**: Starting and stopping the worker returns immediately, and sustained frame input does not block a responsiveness probe while camera interruption is recoverable.

### Tests for User Story 2 (OPTIONAL - only if tests requested) ⚠️

- [X] T012 [P] [US2] Add unit tests for non-blocking start/stop and bounded queue behavior in `tests/unit/test_vision_pipeline_threading.py`
- [X] T013 [P] [US2] Add integration tests for sustained processing and camera recovery in `tests/integration/test_vision_pipeline_responsiveness.py`

### Implementation for User Story 2

- [X] T014 [US2] Expose start, stop, and runtime-state APIs in `src/services/vision_pipeline_service.py`
- [X] T015 [US2] Add queue-depth reporting and recoverable interruption handling in `src/services/vision_pipeline_service.py`

**Checkpoint**: At this point, User Stories 1 and 2 should both work independently

---

## Phase 5: User Story 3 - Publish Standardized AI Events for Downstream Modules (Priority: P3)

**Goal**: Emit a stable event contract that downstream attendance handling can consume without ambiguity.

**Independent Test**: A contract consumer can validate the event fields for recognized, unknown, spoof-warning, and no-face-detected outcomes.

### Tests for User Story 3 (OPTIONAL - only if tests requested) ⚠️

- [X] T016 [P] [US3] Add contract tests for required vision event fields in `tests/contract/test_vision_event_contract.py`
- [X] T017 [P] [US3] Add unit tests for event mapping and no-face diagnostics in `tests/unit/test_vision_event_adapter.py`

### Implementation for User Story 3

- [X] T018 [US3] Finalize the vision event contract mapping in `specs/002-ai-vision-pipeline/contracts/vision-event-contract.md`
- [X] T019 [US3] Align normalized event aliases with `recognition_events` schema fields in `src/services/vision_event_adapter.py`

**Checkpoint**: All user stories should now be independently functional

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [X] T020 [P] Update validation steps and operational flow in `specs/002-ai-vision-pipeline/quickstart.md`
- [X] T021 Add end-to-end privacy, offline, and anti-spoof assertions in `tests/integration/test_vision_pipeline_flow.py`
- [X] T022 Run final repository validation for `src/services/vision_pipeline_service.py` with `PYTHONPATH=src pytest tests/` and `ruff check src/`

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
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - May integrate with US1 but should be independently testable
- **User Story 3 (P3)**: Can start after Foundational (Phase 2) - May integrate with US1/US2 but should be independently testable

### Within Each User Story

- Tests (if included) MUST be written and FAIL before implementation
- Constitution-required validations (privacy/offline/integrity) MUST be included when impacted
- Models before services
- Services before endpoints
- Core implementation before integration
- Story complete before moving to next priority

### Parallel Opportunities

- Setup tasks T001, T002, and T003 can run in parallel because they touch different files
- Foundational task T006 can run in parallel with T004 and T005 because it lives in a separate adapter file
- User Story 1 tests T007 and T008 can run in parallel
- User Story 2 tests T012 and T013 can run in parallel
- User Story 3 tests T016 and T017 can run in parallel
- Different user stories can be worked on in parallel after the foundational phase completes

---

## Parallel Example: User Story 1

```bash
# Launch all tests for User Story 1 together:
Task: "Add unit tests for detect -> liveness -> recognize ordering in tests/unit/test_vision_pipeline_order.py"
Task: "Add integration tests for real-face and spoof outcomes in tests/integration/test_vision_pipeline_flow.py"

# Launch all setup scaffolding together:
Task: "Add frame-processing and pipeline-state dataclasses to src/models/entities.py"
Task: "Add normalized vision event adapter helpers to src/services/vision_event_adapter.py"
Task: "Add fake camera and event-sink fixtures to tests/conftest.py"
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