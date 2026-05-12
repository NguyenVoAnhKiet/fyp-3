# Tasks: Attendance UI Navigation Architecture

**Input**: Design documents from `/specs/005-attendance-ui-navigation/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Included because this feature impacts attendance integrity signals, offline-first behavior, and measurable quality gates (FPS and response latency).

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Prepare UI module scaffolding and baseline test harness for Module 5.

- [x] T001 Create UI package scaffold in src/ui/__init__.py
- [x] T002 [P] Create UI constants for state, command, and color tokens in src/ui/constants.py
- [x] T003 [P] Add shared UI fixtures for state and frame stubs in tests/conftest.py
- [x] T004 [P] Add baseline UI module import smoke test in tests/unit/test_ui_bootstrap.py

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Build core UI architecture required before any user story implementation.

**CRITICAL**: No user story work can begin until this phase is complete.

- [x] T005 [P] Define UI state and render-health models in src/ui/models.py
- [x] T006 [P] Implement state transition policy (`IDLE <-> LIVE_ATTENDANCE`) in src/ui/state_machine.py
- [x] T007 [P] Implement hotkey command parser (`S`, `E`, `Q`) in src/ui/command_router.py
- [x] T008 [P] Implement fixed outcome-to-color mapping service in src/ui/status_signal.py
- [x] T009 [P] Implement non-blocking frame queue adapter for UI consumption in src/ui/frame_bridge.py
- [x] T010 [P] Implement UI event bus contract between UI and services in src/ui/event_bus.py
- [x] T011 Wire foundational UI components into module exports in src/ui/__init__.py
- [x] T012 Add foundational unit coverage for state machine, command validation, and color mapping in tests/unit/test_ui_foundation.py

**Checkpoint**: Foundation ready - user story implementation can now begin.

---

## Phase 3: User Story 1 - Operate Attendance Screen States (Priority: P1) MVP

**Goal**: Let lecturers transition clearly between IDLE and live attendance screens with deterministic behavior.

**Independent Test**: Start from IDLE, trigger start action, verify LIVE_ATTENDANCE state, trigger end action, verify return to IDLE with visible mode indicator.

### Tests for User Story 1

- [x] T013 [P] [US1] Add integration test for IDLE -> LIVE_ATTENDANCE -> IDLE lifecycle in tests/integration/test_ui_state_navigation.py
- [x] T014 [P] [US1] Add unit test for invalid start/end transition rejection in tests/unit/test_ui_state_machine.py

### Implementation for User Story 1

- [x] T015 [US1] Implement main attendance window state container in src/ui/main_window.py
- [x] T016 [US1] Integrate start/end session commands with attendance service in src/services/attendance_service.py
- [x] T017 [P] [US1] Implement visible mode indicator rendering for IDLE and LIVE_ATTENDANCE in src/ui/main_window.py
- [x] T018 [P] [US1] Emit deterministic state transition events for UI observers in src/ui/event_bus.py
- [x] T019 [US1] Add state-navigation regression coverage in tests/unit/test_ui_navigation_regression.py

**Checkpoint**: User Story 1 is independently functional and testable.

---

## Phase 4: User Story 2 - View Smooth Live Camera Feed (Priority: P2)

**Goal**: Render live camera preview smoothly while keeping UI responsive and surfacing recoverable stream warnings.

**Independent Test**: Run live preview continuously and verify >=24 FPS for threshold windows; simulate camera outage and confirm non-blocking warning while controls still respond.

### Tests for User Story 2

- [x] T020 [P] [US2] Add integration test for live-preview frame cadence and UI responsiveness in tests/integration/test_ui_live_preview.py
- [x] T021 [P] [US2] Add integration test for camera-unavailable warning behavior in tests/integration/test_ui_camera_degraded.py
- [x] T022 [P] [US2] Add performance threshold test for 24+ FPS sampling rule in tests/integration/test_ui_fps_threshold.py

### Implementation for User Story 2

- [x] T023 [US2] Implement PyQt5 render loop with timer-driven frame updates in src/ui/video_panel.py
- [x] T024 [US2] Integrate frame bridge with existing vision pipeline producer in src/services/vision_pipeline_service.py
- [x] T025 [P] [US2] Implement rolling FPS tracker and stream health status model in src/ui/render_metrics.py
- [x] T026 [P] [US2] Implement non-blocking stream warning banner for `UNAVAILABLE` state in src/ui/main_window.py
- [x] T027 [US2] Add responsiveness guard to prevent UI-thread blocking during frame render in src/ui/video_panel.py
- [x] T028 [US2] Add unit/integration assertions for frame queue backpressure handling in tests/unit/test_ui_frame_bridge.py

**Checkpoint**: User Story 2 is independently functional and testable.

---

## Phase 5: User Story 3 - Control Workflow with Hotkeys and Colors (Priority: P3)

**Goal**: Provide reliable keyboard operation and consistent green/yellow/red visual feedback for attendance outcomes.

**Independent Test**: Press hotkeys in valid/invalid contexts and verify command outcome + response timing; feed representative outcomes and verify fixed color mapping.

### Tests for User Story 3

- [x] T029 [P] [US3] Add contract-style test for hotkey command response schema in tests/contract/test_ui_command_contract.py
- [x] T030 [P] [US3] Add integration test for hotkey latency target (<=200ms for valid commands) in tests/integration/test_ui_hotkey_latency.py
- [x] T031 [P] [US3] Add integration test for fixed outcome-color mapping in tests/integration/test_ui_status_color_mapping.py

### Implementation for User Story 3

- [x] T032 [US3] Implement hotkey bindings and state-aware dispatch in src/ui/hotkeys.py
- [x] T033 [US3] Integrate hotkey router with main window command handling in src/ui/main_window.py
- [x] T034 [P] [US3] Implement response payload (`ACCEPTED|REJECTED`, reason, handled_at) in src/ui/command_router.py
- [x] T035 [P] [US3] Implement outcome rendering adapter for SUCCESS/CAUTION/WARNING in src/ui/status_signal.py
- [x] T036 [US3] Add deterministic color legend and status label presentation in src/ui/status_panel.py
- [x] T037 [US3] Add unit tests for command validity matrix by state in tests/unit/test_ui_hotkeys.py

**Checkpoint**: User Story 3 is independently functional and testable.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final validation and cross-story hardening.

- [x] T038 [P] Update Module 5 quickstart validation steps and troubleshooting in specs/005-attendance-ui-navigation/quickstart.md
- [x] T039 [P] Validate offline-first UI operation paths in tests/integration/test_ui_offline_navigation.py
- [x] T040 [P] Validate no raw image persistence introduced by UI flows in tests/integration/test_enrollment_privacy.py
- [x] T041 [P] Add end-to-end UI + attendance smoke scenario in tests/integration/test_vision_pipeline_flow.py
- [x] T042 Run full feature validation suite listed in specs/005-attendance-ui-navigation/quickstart.md

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies; can start immediately.
- **Foundational (Phase 2)**: Depends on Setup completion; blocks all user stories.
- **User Stories (Phase 3+)**: Depend on Foundational completion.
- **Polish (Phase 6)**: Depends on selected user stories being complete.

### User Story Dependency Graph

- **US1 (P1)** -> **US2 (P2)** -> **US3 (P3)**
- US2 can start after Foundational, but for incremental delivery it should follow US1 because live preview screen integration reuses US1 main window state container.
- US3 can start after Foundational, but for incremental delivery it should follow US2 because hotkey and color feedback are attached to active live preview workflows.

### Within Each User Story

- Tests should be written first and fail before implementation.
- Models/policies before UI integration.
- UI integration before service wiring refinements.
- Core implementation before cross-cutting polish.

### Parallel Opportunities

- Phase 1: T002-T004 can run in parallel.
- Phase 2: T005-T010 can run in parallel, then T011-T012.
- US1: T013-T014 parallel; T017-T018 parallel after T015.
- US2: T020-T022 parallel; T025-T026 parallel after T023.
- US3: T029-T031 parallel; T034-T035 parallel after T032.
- Phase 6: T038-T041 can run in parallel before T042.

---

## Parallel Example: User Story 1

```bash
Task: "Add integration test for IDLE -> LIVE_ATTENDANCE -> IDLE lifecycle in tests/integration/test_ui_state_navigation.py"
Task: "Add unit test for invalid start/end transition rejection in tests/unit/test_ui_state_machine.py"
Task: "Implement visible mode indicator rendering for IDLE and LIVE_ATTENDANCE in src/ui/main_window.py"
Task: "Emit deterministic state transition events for UI observers in src/ui/event_bus.py"
```

## Parallel Example: User Story 2

```bash
Task: "Add integration test for live-preview frame cadence and UI responsiveness in tests/integration/test_ui_live_preview.py"
Task: "Add integration test for camera-unavailable warning behavior in tests/integration/test_ui_camera_degraded.py"
Task: "Add performance threshold test for 24+ FPS sampling rule in tests/integration/test_ui_fps_threshold.py"
Task: "Implement rolling FPS tracker and stream health status model in src/ui/render_metrics.py"
Task: "Implement non-blocking stream warning banner for `UNAVAILABLE` state in src/ui/main_window.py"
```

## Parallel Example: User Story 3

```bash
Task: "Add contract-style test for hotkey command response schema in tests/contract/test_ui_command_contract.py"
Task: "Add integration test for hotkey latency target (<=200ms for valid commands) in tests/integration/test_ui_hotkey_latency.py"
Task: "Add integration test for fixed outcome-color mapping in tests/integration/test_ui_status_color_mapping.py"
Task: "Implement response payload (`ACCEPTED|REJECTED`, reason, handled_at) in src/ui/command_router.py"
Task: "Implement outcome rendering adapter for SUCCESS/CAUTION/WARNING in src/ui/status_signal.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1 and Phase 2.
2. Complete User Story 1.
3. Validate User Story 1 independently using T013-T014.
4. Demo/deploy MVP slice.

### Incremental Delivery

1. Deliver US1 state navigation and validate.
2. Deliver US2 live preview quality and validate.
3. Deliver US3 hotkeys and color feedback and validate.
4. Run cross-cutting validation in Phase 6.

### Parallel Team Strategy

1. Team completes Phase 1 and Phase 2 together.
2. After foundation:
   - Developer A: US1 state lifecycle tasks.
   - Developer B: US2 render pipeline tasks.
   - Developer C: US3 command and status tasks.
3. Merge at phase checkpoints and run shared validation.

---

## Notes

- [P] tasks use different files and avoid incomplete dependency overlap.
- [USx] labels preserve story-level traceability.
- Each story phase is independently testable at its checkpoint.
- Use quickstart.md as the acceptance-run script at the end of each increment.

