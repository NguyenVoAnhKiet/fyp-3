# Tasks: Report and System Configuration Utilities

**Input**: Design documents from `/specs/006-module-6-module/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, quickstart.md

**Tests**: Included because this feature changes persisted settings, offline behavior, threshold governance, and report export/privacy boundaries.

**Organization**: Tasks are grouped by user story so each story can be implemented and validated independently.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel across different files with no dependency on unfinished tasks
- **[Story]**: Which user story the task belongs to, e.g. `[US1]`
- Include exact file paths in each description

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Prepare dependencies and shared constants used by the settings and export flows

- [ ] T001 Add the XLSX export dependency to `pyproject.toml`
- [ ] T002 [P] Add shared setting keys, report field names, and export format enums to `src/core/constants.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Add shared data structures and service scaffolding used by the user stories

- [ ] T003 [P] Add report row and export data classes to `src/models/entities.py`
- [ ] T004 [P] Create the camera discovery service scaffold in `src/services/camera_device_service.py`
- [ ] T005 [P] Create the report export service scaffold in `src/services/report_export_service.py`

**Checkpoint**: Shared models and service entry points are ready for user story implementation.

---

## Phase 3: User Story 1 - Configure Camera and Thresholds (Priority: P1) 🎯 MVP

**Goal**: Let an authorized user choose a camera input and persist liveness and similarity thresholds for future use.

**Independent Test**: Open settings, pick a camera, change the thresholds, save, restart the app, and confirm the same values are restored.

### Tests for User Story 1

- [ ] T006 [P] [US1] Add unit coverage for saving and loading camera and threshold settings in `tests/unit/test_settings_configuration_unit.py`
- [ ] T007 [P] [US1] Add integration coverage for settings persistence across restart in `tests/integration/test_settings_configuration_integration.py`

### Implementation for User Story 1

- [ ] T008 [P] [US1] Extend `src/services/settings_service.py` with typed helpers for camera index, liveness threshold, and similarity threshold values
- [ ] T009 [P] [US1] Implement camera device discovery in `src/services/camera_device_service.py`
- [ ] T010 [US1] Build the settings UI for camera selection and threshold sliders in `src/ui/settings_panel.py`
- [ ] T011 [US1] Wire the settings panel into `src/ui/main_window.py` and persist user changes through `src/services/settings_service.py`
- [ ] T012 [US1] Add validation and user feedback for out-of-range threshold values in `src/ui/settings_panel.py`

**Checkpoint**: Camera and threshold configuration works independently and can be demonstrated on its own.

---

## Phase 4: User Story 2 - Export Completed Session Reports (Priority: P2)

**Goal**: Let an administrator or lecturer export a completed attendance session to CSV or XLSX without altering attendance history.

**Independent Test**: Close a session, export it as CSV and XLSX, and confirm the file contains the expected session, student, timestamp, and outcome columns.

### Tests for User Story 2

- [ ] T013 [P] [US2] Add unit coverage for completed-session CSV and XLSX export in `tests/unit/test_report_export_unit.py`
- [ ] T014 [P] [US2] Add integration coverage for exported report contents and format in `tests/integration/test_report_export_integration.py`

### Implementation for User Story 2

- [ ] T015 [P] [US2] Add session and attendance data assembly helpers in `src/services/report_export_service.py` using `src/repositories/session_repository.py`, `src/repositories/attendance_repository.py`, and `src/repositories/user_repository.py`
- [ ] T016 [US2] Implement CSV and XLSX export writers in `src/services/report_export_service.py`
- [ ] T017 [US2] Create the report export UI in `src/ui/report_export_dialog.py` and connect it from `src/ui/main_window.py`
- [ ] T018 [US2] Add read-only completed-session guards and report column mapping in `src/services/report_export_service.py`

**Checkpoint**: Completed sessions can be exported locally without mutating attendance data.

---

## Phase 5: User Story 3 - Guard Report and Settings Boundaries (Priority: P3)

**Goal**: Reject invalid settings values and invalid report export attempts with clear feedback.

**Independent Test**: Try an out-of-range threshold, request export from an active session, and confirm each action is blocked with a clear message.

### Tests for User Story 3

- [ ] T019 [P] [US3] Add unit coverage for rejected thresholds, missing camera devices, and blocked exports in `tests/unit/test_settings_and_report_boundaries_unit.py`
- [ ] T020 [P] [US3] Add integration coverage for active-session export rejection and offline/local-only behavior in `tests/integration/test_settings_and_report_boundaries_integration.py`

### Implementation for User Story 3

- [ ] T021 [P] [US3] Add threshold range validation and error messaging in `src/services/settings_service.py`
- [ ] T022 [P] [US3] Add completed-session, empty-report, and non-completed export guards in `src/services/report_export_service.py`
- [ ] T023 [US3] Add non-blocking UI warnings for missing camera devices and blocked exports in `src/ui/settings_panel.py` and `src/ui/report_export_dialog.py`

**Checkpoint**: Invalid configuration and export paths are blocked cleanly without disturbing valid flows.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final validation and documentation alignment across settings and export flows

- [ ] T024 [P] Update the feature quickstart with the finalized settings and export smoke flow in `specs/006-module-6-module/quickstart.md`
- [ ] T025 [P] Run the targeted pytest suite for settings and report export flows in `tests/unit/` and `tests/integration/`
- [ ] T026 Verify the exported report schema excludes biometric fields and matches stored attendance history in `src/services/report_export_service.py` and the related tests

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies; can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion; blocks all user stories
- **User Stories (Phase 3+)**: Depend on Foundational completion
- **Polish (Final Phase)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational completion; no dependency on other stories
- **User Story 2 (P2)**: Can start after Foundational completion; may reuse shared settings/report scaffolding but remains independently testable
- **User Story 3 (P3)**: Can start after Foundational completion; validates the negative paths for stories 1 and 2 without requiring a new feature surface

### Within Each User Story

- Tests should be written before implementation and should fail before the code is added
- Shared data structures and service scaffolding should be complete before the story-specific UI or business logic
- User-facing validation should be added after the core flow is working
- Each story should be independently verifiable before moving to the next priority

### Parallel Opportunities

- Setup tasks T002 can run in parallel with other repository-independent preparation work
- Foundational tasks T003-T005 can run in parallel because they touch different files
- In User Story 1, T006 and T007 can run in parallel, and T008-T009 can run in parallel
- In User Story 2, T013 and T014 can run in parallel, and T015 can be developed alongside the UI task once the service scaffold exists
- In User Story 3, T019 and T020 can run in parallel, and T021 and T022 can proceed in parallel because they touch different services

---

## Parallel Example: User Story 1

```bash
# Run the settings tests together:
Task: "Add unit coverage for saving and loading camera and threshold settings in tests/unit/test_settings_configuration_unit.py"
Task: "Add integration coverage for settings persistence across restart in tests/integration/test_settings_configuration_integration.py"

# Build the shared service pieces together:
Task: "Extend src/services/settings_service.py with typed helpers for camera index, liveness threshold, and similarity threshold values"
Task: "Implement camera device discovery in src/services/camera_device_service.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational
3. Complete Phase 3: User Story 1
4. Stop and validate settings persistence independently
5. Demo the configuration flow if ready

### Incremental Delivery

1. Complete Setup + Foundational
2. Add User Story 1 and validate it independently
3. Add User Story 2 and validate completed-session export independently
4. Add User Story 3 and validate negative-path guards independently
5. Keep report export read-only and camera/threshold persistence local at every step

### Parallel Team Strategy

1. One developer can own User Story 1 while another starts User Story 2 after the foundation is complete
2. A third developer can prepare User Story 3 tests and guard rails in parallel with the positive-path work
3. Final validation should cover persistence, export contents, and biometric-data exclusion across the finished feature

---

## Notes

- [P] tasks should touch different files and have no dependency on incomplete tasks
- [Story] labels map tasks to specific user stories for traceability
- The report export flow must remain read-only and local-only
- The settings flow must persist camera and threshold choices across restarts
- Verify the tests fail before implementing each story
- Prefer small, reversible changes within the existing `src/` and `tests/` layout
