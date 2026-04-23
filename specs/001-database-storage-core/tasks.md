# Tasks: Database & Storage Core

## Phase 1: Setup

**Goal**: Establish the Python package layout and shared project scaffolding for local SQLite storage.

**Independent Test**: The project structure exists and the storage package can be imported without errors.

- [X] T001 Create the storage package skeleton in `src/core/`, `src/models/`, `src/repositories/`, and `src/services/`
- [X] T002 Create the initial test directories in `tests/unit/` and `tests/integration/`
- [X] T003 [P] Add a lightweight package initializer in `src/__init__.py` and package markers for storage subpackages

## Phase 2: Foundational

**Goal**: Build the shared database and security primitives that all stories depend on.

**Independent Test**: The database can be opened, tables can be created, and password hashing works independently of user-facing flows.

- [X] T004 Implement SQLite connection and initialization helpers in `src/core/db.py`
- [X] T005 [P] Implement a schema bootstrap module for foreign keys, WAL mode, and table creation in `src/core/schema.py`
- [X] T006 [P] Implement credential hashing helpers with bcrypt in `src/services/security.py`
- [X] T007 Add shared persistence/base repository utilities in `src/repositories/base_repository.py`
- [X] T008 [P] Add foundational integration tests for database initialization and restart persistence in `tests/integration/test_database_init.py`
- [X] T009 [P] Add foundational unit tests for credential hashing helpers in `tests/unit/test_security.py`

## Phase 3: User Story 1 - Initialize Core Storage (Priority: P1)

**Goal**: Ensure first-run initialization creates all required record types and preserves existing data across restarts.

**Independent Test**: A fresh database initializes successfully, and an existing database remains readable after restart.

- [X] T010 [US1] Implement user, face reference, session, recognition event, attendance record, and setting models in `src/models/`
- [X] T011 [P] [US1] Implement repository classes for core table creation and basic CRUD in `src/repositories/user_repository.py` and `src/repositories/system_setting_repository.py`
- [X] T012 [US1] Implement storage bootstrap and migration-safe initialization logic in `src/core/storage_manager.py`
- [X] T013 [P] [US1] Add integration tests for first-run schema creation and restart persistence in `tests/integration/test_storage_bootstrap.py`
- [X] T014 [US1] Add unit tests for repository CRUD and schema creation behavior in `tests/unit/test_storage_repositories.py`

## Phase 4: User Story 2 - Record Attendance History Reliably (Priority: P2)

**Goal**: Persist session activity, recognition outcomes, and duplicate-safe attendance records.

**Independent Test**: A live session can record one successful attendance event, and a duplicate attempt for the same learner is blocked.

- [X] T015 [US2] Implement attendance session and recognition event repositories in `src/repositories/session_repository.py` and `src/repositories/recognition_event_repository.py`
- [X] T016 [P] [US2] Implement duplicate-prevention constraints and transactional attendance write flow in `src/repositories/attendance_repository.py`
- [X] T017 [US2] Implement attendance session lifecycle and event logging service methods in `src/services/attendance_service.py`
- [X] T018 [P] [US2] Add integration tests for session creation, attendance success, and duplicate prevention in `tests/integration/test_attendance_history.py`
- [X] T019 [US2] Add unit tests for attendance session lifecycle and duplicate-handling rules in `tests/unit/test_attendance_service.py`

## Phase 5: User Story 3 - Manage Settings and Protected Enrollment Data (Priority: P3)

**Goal**: Persist settings safely and store biometric enrollment data only in derived form.

**Independent Test**: Updating a setting persists across restart, and enrollment data is retained only as embeddings without raw images.

- [X] T020 [US3] Implement system settings management in `src/services/settings_service.py` and `src/repositories/system_setting_repository.py`
- [X] T021 [P] [US3] Implement face reference persistence with derived embedding storage in `src/repositories/face_reference_repository.py`
- [X] T022 [US3] Implement enrollment cleanup rules that discard raw images after embedding extraction in `src/services/enrollment_service.py`
- [X] T023 [P] [US3] Add integration tests for settings persistence and privacy-safe enrollment cleanup in `tests/integration/test_settings_and_enrollment.py`
- [X] T024 [US3] Add unit tests for setting validation and raw-image cleanup rules in `tests/unit/test_settings_and_enrollment.py`

## Phase 6: Polish & Cross-Cutting Concerns

**Goal**: Verify the completed storage core against the constitution and feature acceptance criteria.

**Independent Test**: The feature passes targeted validation for integrity, privacy, offline use, and performance expectations.

- [X] T025 [P] Add end-to-end validation for offline storage operations in `tests/integration/test_offline_behavior.py`
- [X] T026 [P] Add regression coverage for immutable attendance history and auditable corrections in `tests/integration/test_attendance_audit.py`
- [X] T027 Validate CRUD latency and core workflow timings against the plan in `tests/integration/test_performance.py`
- [X] T028 Update `specs/001-database-storage-core/quickstart.md` with the final implementation verification steps
- [X] T029 Review `specs/001-database-storage-core/data-model.md` and `specs/001-database-storage-core/research.md` for any implementation-driven follow-up notes

## Dependencies

- Setup must complete before foundational tasks.
- Foundational tasks must complete before any user story work.
- User Story 1 is the MVP foundation and should be implemented before User Stories 2 and 3.
- User Story 2 depends on the session, attendance, and recognition persistence groundwork from User Story 1.
- User Story 3 depends on the shared persistence layer and security primitives from the foundational phase.
- Final polish depends on completion of the user story phases.

## Parallel Execution Examples

### User Story 1

- T011 and T013 can run in parallel after T010 because they touch different files.
- T012 can proceed alongside T011/T013 once the model definitions are clear.

### User Story 2

- T015 and T016 can run in parallel after the shared storage foundation exists.
- T018 and T019 can run in parallel after T017 is implemented.

### User Story 3

- T020 and T021 can run in parallel after the shared storage foundation exists.
- T023 and T024 can run in parallel after T022 is implemented.

### Implementation Strategy

1. Deliver MVP first by completing Setup, Foundational, and User Story 1 so the database can initialize and persist data.
2. Add User Story 2 next to make attendance capture reliable and duplicate-safe.
3. Finish with User Story 3 to lock down privacy-safe enrollment storage and configurable settings.
4. End with polish tasks that verify offline operation, auditability, and performance against the constitution.
