# Plan 0005: Centralize Configuration Resolution (`SystemConfig`)

**Parent plan:** [0002 — Architecture Deepening Checklist](0002-architecture-deepening.md) (candidate #3).

## Status

**Draft** — design pending grilling. Surfaced by `improve-codebase-architecture` skill; see friction recap in parent plan.

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

_To be filled by grilling session. Five design questions in scope:_

| # | Question | Constraints |
|---|----------|-------------|
| 1 | `SystemConfig` dataclass with all tunables, or a `ConfigResolver` with named entries? | Dataclass = data; resolver = behavior. The resolution order is the complex part; the dataclass is just the result type. |
| 2 | Is `bootstrap.py` a different resolver, or should it share the same one? | A shared resolver that knows "I am in init mode" couples the two paths. A separate resolver makes the difference explicit. |
| 3 | Where do defaults live — in the dataclass, in a separate `defaults.py`, or in `.env.example`? | `.env.example` is docs, not executable. Defaults must be in Python to be testable. |
| 4 | Is the threshold-seeding pattern (env → DB on first run, then DB owns) encoded in the resolver, or in a separate seeding step? | Seeding is a one-time migration; resolution is per-read. These are different concerns. |
| 5 | Does `SettingsService` earn its keep post-refactor? | If the resolver does the work, the service may be unnecessary. If it stays, it must add real value (caching, validation, transformation). |

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
