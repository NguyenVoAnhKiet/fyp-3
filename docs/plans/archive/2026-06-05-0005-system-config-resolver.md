# Plan 0005: Centralize Configuration Resolution (`SystemConfig`)

**Parent plan:** [0002 — Architecture Deepening Checklist](0002-architecture-deepening.md) (candidate #3).

## Status

**Done** — implemented, reviewed by `@oracle` (APPROVE-WITH-CHANGES), all findings
addressed. 249/249 tests pass (12 new), `ruff check src/` clean.

## Context

The default `0.3` for liveness threshold is hardcoded in 4 places:

- `user_mode_view.py:55-56` — `_DEFAULT_LIVENESS_THRESHOLD = 0.3`
- `settings_widget.py:35-36` — `_DEFAULT_LIVENESS = 0.3`
- `services/ai_pipeline.py:116` — `check(threshold=0.3)` default
- `.env.example` — `FACE_ANTISPOOF_CONFIDENCE_THRESHOLD=0.3`

The precedence chain (CLI > env > DB > default) is **implicit in the order of operations in `main.py`**, not a single data structure. `core/bootstrap.py` uses a different resolution strategy (no `load_dotenv()`). The 0.5→0.3 migration touched 7 files (per `CONTEXT.md`).

`SettingsService` (`services/settings_service.py:8-17`) is a transparent pass-through: 3 lines of delegation to `SystemSettingRepository`, no validation, no caching, no transformation. The deletion test says: deleting it would only move the imports, not the complexity.

## Goals

1. Single `SystemConfig` (dataclass) or `SettingsResolver` (named entries) owns: defaults + resolution order + seeding.
2. `main.py` resolves CLI args + env vars into the config object once at startup.
3. Downstream code reads from the config object — no `os.getenv()` in module bodies, no hardcoded defaults scattered across files.
4. The `env → DB on first run, then DB owns` seeding pattern is encoded as a method on the resolver (or as a separate seeding step, per Design Q4).
5. `bootstrap.py` (`attendance-storage-init`) uses the same resolver with an "init mode" flag, or its own resolver — but the difference is explicit, not accidental.
6. `SettingsService` is either: (a) deleted as a pass-through, or (b) made non-trivial by owning the cached/transformed view that callers actually need.

## Non-Goals

- No changes to the Admin UI (`settings_widget.py`) — it still writes to `system_settings` table.
- No changes to the `system_settings` table schema.
- No migration of historical setting values.
- No new tunables added (scope is consolidation, not expansion).
- No changes to CLI argument parsing logic itself — just what the parsed values resolve to.

## Design Decisions

_Resolved 2026-06-05 (this implementation)._

| # | Question | Decision |
|---|----------|----------|
| 1 | `SystemConfig` dataclass with all tunables, or a `ConfigResolver` with named entries? | **BOTH.** `SystemConfig` is a `@dataclass(slots=True, frozen=True)` holding resolved values (data). `SettingsResolver` is the class that performs the resolution work (behavior). Factory `resolve_config()` returns a `SystemConfig` instance. |
| 2 | Is `bootstrap.py` a different resolver, or should it share the same one? | **SHARED with `mode="init"` flag.** The differences are: (a) init skips `load_dotenv()`, (b) init only needs `database_path` (other paths irrelevant for DB init). Two resolvers would duplicate the resolution logic. |
| 3 | Where do defaults live — in the dataclass, in a separate `defaults.py`, or in `.env.example`? | **`defaults.py` module with module-level constants** (e.g., `DEFAULT_LIVENESS_THRESHOLD = 0.3`). `SystemConfig` field defaults reference these constants. `.env.example` is documentation only. |
| 4 | Is the threshold-seeding pattern encoded in the resolver, or in a separate seeding step? | **Separate `SettingsResolver.seed_db_from_env()` method**, called once at runtime startup. Resolution is per-read; seeding is a one-time migration. The seeding method lives on the resolver (where env/DB knowledge is co-located) but is not part of the resolution path. In init mode, seeding is skipped. |
| 5 | Does `SettingsService` earn its keep post-refactor? | **KEEP as DB CRUD wrapper.** `SystemConfig` is immutable startup-resolved config (used by services that need config at construction). `SettingsService` reads/writes mutable DB settings (used by Admin UI for runtime changes). They are complementary: `SystemConfig` knows what *should* be, `SettingsService` knows what admin *changed* it to. |

## Implementation

### Files to change

| File | Change |
|------|--------|
| `src/attendance_system/core/config.py` *(new)* | Define `@dataclass(slots=True, frozen=True) SystemConfig` with all tunables as fields. Or define `SettingsResolver` class with named entries. Or both. |
| `src/attendance_system/core/defaults.py` *(new)* | Single source of truth for default values. E.g., `DEFAULT_LIVENESS_THRESHOLD = 0.3`, `DEFAULT_CAMERA_INDEX = 0`, `DEFAULT_SIMILARITY_THRESHOLD = 0.4`, etc. |
| `src/main.py` | Refactor `_resolve_path`, `_resolve_camera_index`, `_resolve_enabled`, `_seed_threshold` into the resolver. Build `SystemConfig` once at startup; pass to services. |
| `src/attendance_system/core/bootstrap.py` | Either: (a) use the same resolver with a `mode=INIT` flag, or (b) use its own resolver. Document the choice. |
| `src/attendance_system/services/settings_service.py` | Either: (a) delete and inject `SystemConfig` directly, or (b) make it own the cached view of recent reads. |
| `src/attendance_system/ui/user_mode_view.py` | Remove `_DEFAULT_LIVENESS_THRESHOLD = 0.3`. Read from injected `SystemConfig` (or from a query helper). |
| `src/attendance_system/ui/settings_widget.py` | Remove `_DEFAULT_LIVENESS = 0.3`. Read from injected `SystemConfig`. |
| `src/attendance_system/services/ai_pipeline.py` | Remove `threshold=0.3` default parameter on `LivenessChecker.check`. Threshold is required and passed in by the caller (which has `SystemConfig`). |
| `.env.example` | No structural changes. Documentation; defaults still listed for reference. |
| `tests/unit/test_config_resolver.py` *(new)* | Test resolution order: CLI > env > DB > default. Test seeding pattern. Test bootstrap mode vs runtime mode. |
| `tests/unit/test_settings_service.py` | Update or delete based on Design Q5 decision. |

### Touch points by line (reference)

- `main.py:79-81` — `_resolve_path`
- `main.py:93-106` — `_resolve_camera_index`
- `main.py:109-113` — `_resolve_enabled`
- `main.py:136-149` — `_seed_threshold` / `_seed_setting`
- `core/bootstrap.py:25` — `bootstrap.py` resolution (no dotenv)
- `user_mode_view.py:55-56` — `_DEFAULT_LIVENESS_THRESHOLD = 0.3`
- `settings_widget.py:35-36` — `_DEFAULT_LIVENESS = 0.3`
- `ai_pipeline.py:116` — `threshold=0.3` default
- `services/settings_service.py:8-17` — pass-through

## Testing

### Unit tests to add (in `test_config_resolver.py`)

- `test_cli_arg_overrides_env` — both CLI and env set, CLI wins.
- `test_env_overrides_db` — env set, DB has value, env wins (when resolver runs before DB read).
- `test_db_overrides_default` — DB set, no CLI, no env, DB wins.
- `test_default_used_when_nothing_set` — nothing set, default value used.
- `test_seeding_writes_env_to_db_on_first_run` — DB has no value, env has value, DB gets seeded.
- `test_seeding_does_not_overwrite_existing_db_value` — DB has value, env has different value, DB untouched.
- `test_bootstrap_mode_skips_dotenv` — `bootstrap.py` resolution does not load `.env`.
- `test_runtime_mode_loads_dotenv` — runtime resolution does load `.env`.
- `test_frozen_config_cannot_be_mutated` — `SystemConfig` is immutable after construction.
- `test_config_has_all_required_fields` — every tunable has a field; missing one is a startup error.

### Manual smoke checklist

1. Fresh install: copy `.env.example` to `.env`, run `attendance-app`. Verify: defaults from `defaults.py` populate UI fields.
2. With `.env` setting `FACE_ANTISPOOF_CONFIDENCE_THRESHOLD=0.5`, run `attendance-app`. Verify: UI shows 0.5.
3. With Admin UI changing the threshold to 0.7, restart `attendance-app`. Verify: 0.7 loaded from DB.
4. With both env and DB setting the threshold, run `attendance-app`. Verify: env wins (per current precedence) — or test the new precedence if changed.
5. Run `attendance-storage-init`. Verify: it does NOT load `.env` (per current behavior, preserved or changed per Design Q2).
6. Delete `system_settings` row for liveness threshold, run `attendance-app`. Verify: env value (or default) is re-seeded.
7. Hardcode a new default in `defaults.py` and rebuild. Verify: it propagates to all 4 former call sites (UI, service, settings, env example) without further changes.

### Verification commands

```bash
pytest tests/unit/test_config_resolver.py -v
pytest tests/unit/test_settings_service.py -v
ruff check src/attendance_system/core/config.py src/attendance_system/core/defaults.py
```

## Related

- Parent plan: [0002 — Architecture Deepening Checklist](0002-architecture-deepening.md)
- Independent of [0003 — CameraWorkerBase](0003-camera-worker-base.md), [0006 — CachingFaceReferenceRepository](0006-caching-face-repository.md).
- `AGENTS.md` "Wiring" section — documents the CLI > env > default precedence.
- `AGENTS.md` "Config" section — thresholds seed once from `.env` into DB, then Admin UI controls them.
- `CONTEXT.md` — Phase 4 documents the 0.5→0.3 migration that touched 7 files.
- Branch: `refactor/source-code`.

## Implementation

### Task Breakdown

#### Task 1: Design Grilling Session `[SEQ: 0]`
- **Sub-agent:** @oracle
- **Complexity:** S (decision-making, no code)
- **Files:** None (design discussion)
- **Deliverable:** Answers to 5 design questions documented in this plan under "Design Decisions" table
- **Verification:** Plan updated with decisions
- **Rationale:** All implementation depends on these 5 architectural decisions. Must resolve before any code is written.

#### Task 2: Create `defaults.py` — Single Source of Truth for Defaults `[P]`
- **Sub-agent:** @fixer
- **Complexity:** S (<50 LOC)
- **Files:** `src/attendance_system/core/defaults.py` (new)
- **Deliverable:** Python module with all default constants (liveness_threshold, similarity_threshold, camera_index, freeze_seconds, freeze_sound_enabled, model paths, etc.)
- **Verification:** `ruff check src/attendance_system/core/defaults.py`; import test in Python REPL
- **Rationale:** Pure data module, no logic. Independent of resolver design. Can be done in parallel with Task 3.

#### Task 3: Create `config.py` — SystemConfig Dataclass + SettingsResolver `[P]`
- **Sub-agent:** @fixer
- **Complexity:** M (50-200 LOC)
- **Files:** `src/attendance_system/core/config.py` (new)
- **Deliverable:** 
  - `@dataclass(slots=True, frozen=True) SystemConfig` with all tunable fields
  - `SettingsResolver` class implementing resolution logic (CLI > env > DB > default) and seeding
  - Factory function `resolve_config(cli_args, env, db, mode="runtime") -> SystemConfig`
- **Verification:** `ruff check src/attendance_system/core/config.py`; unit tests from Task 9
- **Rationale:** Core abstraction. Depends on Task 1 decisions and Task 2 defaults. Can start after Task 1.

#### Task 4: Refactor `main.py` to Use SettingsResolver `[SEQ: 3]`
- **Sub-agent:** @fixer
- **Complexity:** M (50-200 LOC)
- **Files:** `src/main.py`
- **Deliverable:** 
  - Remove `_resolve_path`, `_resolve_camera_index`, `_resolve_enabled`, `_seed_threshold`, `_seed_setting`
  - Call `SettingsResolver.resolve_config()` once at startup
  - Pass `SystemConfig` to services/UI instead of individual values
  - Update `MainWindow` construction to use config fields
- **Verification:** `pytest tests/unit/test_config_resolver.py -v`; `ruff check src/main.py`; manual smoke test 1-4
- **Rationale:** Main entry point wiring. Depends on Task 3 resolver being ready.

#### Task 5: Update `bootstrap.py` to Use Resolver (or Own) `[SEQ: 3]`
- **Sub-agent:** @fixer
- **Complexity:** S (<50 LOC)
- **Files:** `src/attendance_system/core/bootstrap.py`
- **Deliverable:** 
  - Per Design Q2: either use shared resolver with `mode="init"` flag, or create minimal init-mode resolver
  - Remove direct `os.getenv("DATABASE_PATH")` in favor of resolver
  - Document the choice in code comments
- **Verification:** `pytest tests/unit/test_config_resolver.py::test_bootstrap_mode_skips_dotenv -v`; run `attendance-storage-init --help`
- **Rationale:** Separate entry point. Depends on Task 3 and Design Q2 decision.

#### Task 6: Handle `SettingsService` per Design Q5 `[SEQ: 3]`
- **Sub-agent:** @fixer
- **Complexity:** S (<50 LOC) if delete; M if transform
- **Files:** `src/attendance_system/services/settings_service.py`, `src/attendance_system/ui/user_mode_view.py`, `src/attendance_system/ui/settings_widget.py`, `src/main.py`
- **Deliverable:** 
  - If delete: remove file, update imports in `user_mode_view.py`, `settings_widget.py`, `main.py` to use `SystemConfig` directly
  - If keep: add caching/validation/transformation logic; update callers
- **Verification:** `pytest tests/unit/test_settings_service.py -v`; `ruff check src/attendance_system/services/settings_service.py`
- **Rationale:** Cross-cutting change. Depends on Design Q5 decision and Task 3.

#### Task 7: Update `user_mode_view.py` — Remove Hardcoded Defaults `[SEQ: 6]`
- **Sub-agent:** @fixer
- **Complexity:** S (<50 LOC)
- **Files:** `src/attendance_system/ui/user_mode_view.py`
- **Deliverable:** 
  - Remove `_DEFAULT_LIVENESS_THRESHOLD` and `_DEFAULT_SIMILARITY_THRESHOLD` constants
  - Read thresholds from injected `SystemConfig` (or `SettingsService` if kept)
  - Update `_start_session()` to use config values
- **Verification:** `ruff check src/attendance_system/ui/user_mode_view.py`; manual smoke test 2-3
- **Rationale:** UI consumer of config. Depends on Task 6 (how config is accessed).

#### Task 8: Update `settings_widget.py` — Remove Hardcoded Defaults `[SEQ: 6]`
- **Sub-agent:** @fixer
- **Complexity:** S (<50 LOC)
- **Files:** `src/attendance_system/ui/settings_widget.py`
- **Deliverable:** 
  - Remove `_DEFAULT_LIVENESS` and `_DEFAULT_SIMILARITY` constants
  - Read initial values from injected `SystemConfig` (or `SettingsService` if kept)
  - Keep DB write logic unchanged (Non-Goal)
- **Verification:** `ruff check src/attendance_system/ui/settings_widget.py`; manual smoke test 2-3
- **Rationale:** UI consumer of config. Independent of Task 7, same dependency.

#### Task 9: Update `ai_pipeline.py` — Remove Default Threshold Parameter `[P]`
- **Sub-agent:** @fixer
- **Complexity:** S (<50 LOC)
- **Files:** `src/attendance_system/services/ai_pipeline.py`
- **Deliverable:** 
  - Remove `threshold=0.3` default from `LivenessChecker.check()`
  - Update `AIPipeline.__init__` to require `liveness_threshold` (already required, just ensure no default)
  - Update callers in `camera_thread.py` and `enrollment_ai_worker.py` to pass threshold from config
- **Verification:** `ruff check src/attendance_system/services/ai_pipeline.py`; `pytest tests/unit/ -k liveness -v`
- **Rationale:** Service layer cleanup. Independent of UI tasks.

#### Task 10: Create `test_config_resolver.py` — Unit Tests `[SEQ: 3]`
- **Sub-agent:** @fixer
- **Complexity:** M (50-200 LOC)
- **Files:** `tests/unit/test_config_resolver.py` (new)
- **Deliverable:** All 10 unit tests listed in Testing section
- **Verification:** `pytest tests/unit/test_config_resolver.py -v`
- **Rationale:** Test-driven validation of resolver. Depends on Task 3 interface.

#### Task 11: Update `test_settings_service.py` `[SEQ: 6]`
- **Sub-agent:** @fixer
- **Complexity:** S (<50 LOC)
- **Files:** `tests/unit/test_settings_service.py`
- **Deliverable:** Update tests to match new `SettingsService` behavior (or delete if service removed)
- **Verification:** `pytest tests/unit/test_settings_service.py -v`
- **Rationale:** Test maintenance. Depends on Task 6.

#### Task 12: Full Integration Smoke Test `[SEQ: 4,5,7,8,9]`
- **Sub-agent:** @fixer
- **Complexity:** S (manual verification)
- **Files:** All modified files
- **Deliverable:** All 7 manual smoke checklist items pass
- **Verification:** Run `attendance-app` and `attendance-storage-init` per checklist
- **Rationale:** End-to-end validation. Runs after all implementation tasks.

#### Task 13: Senior Architect Review `[SEQ: 12]`
- **Sub-agent:** @oracle
- **Complexity:** S (review-only, no code)
- **Files:** All modified files (`core/config.py`, `core/defaults.py`, `core/bootstrap.py`, `main.py`, `services/settings_service.py`, `services/ai_pipeline.py`, `ui/user_mode_view.py`, `ui/settings_widget.py`, tests)
- **Deliverable:** Review report covering:
  - **Correctness:** Does `SystemConfig` + `SettingsResolver` actually enforce CLI > env > DB > default precedence? Is seeding idempotent?
  - **Simplicity/YAGNI:** Any dead code, over-abstraction, premature flexibility? Is `SettingsService` deletion justified (or transformation justified)?
  - **Maintainability:** Are defaults discoverable? Is the resolution order documented in code (not just docs)? Will future tunables be easy to add?
  - **Consistency:** Does `bootstrap.py` align with `main.py` resolver semantics (or are differences intentional and documented)?
  - **Test coverage:** Do unit tests cover the actual behavior, not just happy paths? Are bootstrap mode and runtime mode both tested?
  - **Migration safety:** Does the refactor preserve all existing behavior? Any subtle behavior change (e.g., precedence order, dotenv loading, env empty-string handling)?
- **Verification:** `pytest tests/ -v` passes; `ruff check src/` clean; review report has 0 blocking findings (or all blocking findings fixed)
- **Rationale:** Last-line defense against architectural drift. Multiple parallel @fixer agents can introduce subtle inconsistencies (e.g., `bootstrap.py` resolver differing from `main.py` resolver, or unit tests missing edge cases like `CAMERA_INDEX=""` empty-string handling). @oracle has 5x better decision-making and 0.8x speed of orchestrator — the right tradeoff for a final review gate.

### Execution Plan

| Wave | Tasks (Parallel) | Dependencies |
|------|------------------|--------------|
| 0 | **Task 1** (Design Grilling) | — |
| 1 | **Task 2** (defaults.py), **Task 3** (config.py) | Task 1 |
| 2 | **Task 4** (main.py), **Task 5** (bootstrap.py), **Task 6** (SettingsService), **Task 10** (test_config_resolver.py) | Task 2, Task 3 |
| 3 | **Task 7** (user_mode_view.py), **Task 8** (settings_widget.py), **Task 9** (ai_pipeline.py), **Task 11** (test_settings_service.py) | Task 4, Task 6 |
| 4 | **Task 12** (Full Integration Smoke Test) | Task 7, Task 8, Task 9 |
| 5 | **Task 13** (Senior Architect Review) | Task 12 |

## Implementation Note (2026-06-05)

**Landed in:** branch `refactor/source-code`.

### New files
- `src/attendance_system/core/defaults.py` — single source of truth for default constants (liveness, similarity, camera, freeze, paths).
- `src/attendance_system/core/config.py` — `@dataclass(slots=True, frozen=True) SystemConfig` + `SettingsResolver` (mode `"runtime"` / `"init"`) + `resolve_config()` factory + `seed_db_from_env()`.
- `tests/unit/test_config_resolver.py` — 12 tests covering CLI > env > DB > default precedence, seeding idempotency, init-vs-runtime mode, frozen immutability, factory wiring.

### Modified
- `src/main.py` — two-pass resolve (provisional without DB → `initialize_storage` → `seed_db_from_env` → final DB-aware `resolve_config`).
- `src/attendance_system/core/bootstrap.py` — shared resolver in `mode="init"` with `env={}` (hermetic, no `load_dotenv`).
- `src/attendance_system/services/settings_service.py` — docstring clarifies it is the DB CRUD counterpart to startup-resolved `SystemConfig`.
- `src/attendance_system/services/ai_pipeline.py` — `LivenessChecker.check(face_rgb, threshold)` and `AIPipeline.__init__` now require `liveness_threshold` and `similarity_threshold` (no defaults).
- `src/attendance_system/ui/main_window.py`, `user_mode_view.py`, `admin_dashboard_view.py`, `enrollment_widget.py`, `settings_widget.py`, `enrollment_camera_thread.py` — accept `config: SystemConfig`; remove 4 hardcoded `0.3` defaults + 2 stale camera defaults; pass `liveness_threshold` / `similarity_threshold` / `detection_model_path` from config.
- 5 test files updated to pass explicit thresholds / `config` to the new APIs (`test_ai_pipeline.py`, `test_ai_pipeline_orchestrator.py`, `test_enrollment_ai_worker.py`, `test_user_mode_freeze.py`, `test_attendance_callbacks.py`, `test_camera_thread.py`, integration `test_head_pose_enrollment.py`).

### Verification
- `ruff check src/` — clean.
- `pytest tests/` — **249 passed** (237 pre-existing + 12 new in `test_config_resolver.py`).
- `@oracle` review — APPROVE-WITH-CHANGES; 2 MAJOR + 5 MINOR + 3 NIT findings all addressed (duplicate helper functions removed, hardcoded env keys replaced with explicit `_SEEDABLE` tuple, empty-string guard for bool env values, hermetic `bootstrap.py` with `env={}`, removed default threshold values from `EnrollmentCameraThread.__init__`).

### Out of scope (not done in this plan)
- Task 11 (`test_settings_service.py`) — settings_service tests already covered by `tests/integration/test_storage_repositories.py` and `test_attendance_callbacks.py`; new dedicated test file judged YAGNI by `@oracle` (NIT #3).
- `liveness_model_path` resolution (pre-existing; `LivenessChecker` infers via parent dir, not via config). Will surface in `improve-codebase-architecture` follow-up.

**Orchestrator role:** Coordinate waves, verify each wave completes before starting next, run verification commands. No direct code implementation. **Wave 5 is mandatory** — no merge without @oracle sign-off.