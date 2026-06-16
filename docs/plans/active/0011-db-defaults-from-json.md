# 0011 — DB Defaults from JSON (Remove Env-var Seeding)

## Status

Draft

## Context

Currently, `seed_db_from_env()` reads `.env` variables and writes them to the `system_settings` DB table on first run (idempotent — only writes if key is unset). This couples the `.env` file to DB schema, creating confusion:

- Admins see seedable keys in `.env` and expect changing them to affect runtime — but they only take effect on first run.
- The `.env` file contains two categories of settings mixed together: DB-seedable settings and non-DB settings (paths, feature flags).
- The `_SEEDABLE` tuple maps env-var names to DB keys, adding an unnecessary indirection layer.

**Goal:** Decouple `.env` from DB seeding. Use a dedicated JSON defaults file for first-run initialization. After first run, the Admin UI is the only way to change DB settings.

## Goals

1. `.env` and `.env.example` only contain non-DB settings (paths, camera index, feature flags).
2. A new `system_defaults.json` file provides initial values for `system_settings` on first run.
3. `resolve()` for DB-seedable keys uses `DB > JSON defaults` — no env-var override.
4. `seed_db_from_env()` → `seed_db_from_defaults()`: reads JSON, writes to DB if key unset.
5. Admin UI remains the sole mechanism for runtime changes after first run.
6. All tests updated and passing.

## Non-Goals

- Changing the Admin UI or Settings widget.
- Changing the `SettingsService` DB layer.
- Adding new tunables or changing default values.
- Changing non-DB settings resolution (paths, camera index, feature flags still use CLI > env > default).
- Migrating existing DB data — existing values are preserved as-is.
- `attendance-storage-init` — init mode remains hermetic (schema + admin only, no JSON seeding). Seeding is a runtime concern.

## Migration Note

Existing `.env` files containing seedable keys will have those keys **silently ignored** after upgrade. This is intentional but should be communicated in release notes. Users can clean up their `.env` files at their convenience — no breakage occurs either way.

## Design Decisions

| Decision | Options Considered | Choice | Rationale |
|----------|-------------------|--------|-----------|
| Defaults file format | JSON / YAML / TOML / Python dict | **JSON** | Zero dependency (`json` built-in), simple key-value, low error risk, easy to edit manually. |
| File location | `core/system_defaults.json` / `config/system_defaults.json` / near `.env` | **`src/attendance_system/core/system_defaults.json`** | Co-located with `config.py` that consumes it, easy to find for developers. |
| Resolution priority for seedable keys | `env > DB > defaults` / `DB > JSON > defaults.py` (no env) | **DB > JSON > `defaults.py`** (no env) | Eliminates env-var override confusion. Admin UI is the single source of truth after first run. `defaults.py` serves as ultimate fallback if JSON file is missing or a key is absent from JSON. |
| JSON loading strategy | Module-level constant / per-call read / parameter injection | **Module-level constant with try/except** | Load once at import time. If file missing or invalid JSON: log warning, fall back to empty dict → `defaults.py` values win. Avoids hard crash on import. |
| JSON value types | Native types / string-only | **Native types, convert to str on seed** | JSON uses `true`/`0.5`/`5` (cleaner). `seed_db_from_defaults()` converts via `str(value)` before calling `settings.set()`. |
| JSON value emptiness | Falsy check / `is None` check | **`is None` only** | `false`, `0`, `0.0` are valid values. Only `null` or missing key should skip seeding. |
| `_SEEDABLE` structure | Keep tuple format / simplify to dict | **Dict `{db_key: value_type}`** | JSON key = DB key, no env-var column needed. Simpler and more readable. |
| Method naming | Keep `seed_db_from_env` / rename to `seed_db_from_defaults` | **`seed_db_from_defaults`** | Accurately describes the new data source. |
| `resolve_config()` interface | Change / keep unchanged | **Keep unchanged** | Internal changes only; callers don't need to know about the JSON defaults source. |
| `.env` cleanup | Remove seedable keys / keep with comments / no change | **Remove seedable keys** | Clean separation: `.env` = non-DB settings only. |
| Test scope | Full update / minimal rename | **Full update** | Ensure coverage for new behavior: JSON loading, idempotent seeding, resolution priority. |

## Tasks

| # | Task | Agent | Depends On | Status |
|---|------|-------|------------|--------|
| 1 | Create `system_defaults.json` with initial values for 9 seedable keys | @fixer | — | Pending |
| 2 | Refactor `config.py`: replace `_SEEDABLE` tuple with `_SEED_SETTINGS` dict, add JSON loading, update `resolve()` to skip env var for seedable keys, rename `seed_db_from_env` → `seed_db_from_defaults` | @fixer | 1 | Pending |
| 3 | Update `main.py` to call `seed_db_from_defaults()` | @fixer | 2 | Pending |
| 4 | Clean `.env` and `.env.example`: remove seedable keys | @fixer | — | Pending |
| 5 | Update all tests: rename, new test cases for JSON loading and resolution priority | @fixer | 2 | Pending |
| 6 | Update codemap docs to reflect new architecture | @fixer | 2 | Pending |
| 7 | Oracle review of implementation | @oracle | 1-6 | Completed (CONDITIONAL PASS — gaps addressed in this plan revision) |

## Implementation

### File changes

| File | Change |
|------|--------|
| `src/attendance_system/core/system_defaults.json` | **New.** JSON dict mapping 9 seedable DB keys to their default values (native types: `true`, `0.5`, `5`, `"UTC"`). |
| `src/attendance_system/core/config.py` | Replace `_SEEDABLE` tuple with `_SEED_SETTINGS: dict[str, str]`. Add `_load_defaults()` to read JSON at module level with try/except (fallback to empty dict on missing/corrupt file). Update `resolve()` to only use `read_db()` for seedable keys (remove `env_map.get(...)` calls for those keys). Rename `seed_db_from_env()` → `seed_db_from_defaults()` with JSON-based logic. Key behaviors: (a) `is None` check only — `false`/`0` are valid; (b) convert native JSON types → `str` via `str(value)` before `settings.set()`; (c) skip in init mode (unchanged). |
| `src/main.py` | Change `seed_db_from_env(...)` call to `seed_db_from_defaults(...)`. |
| `.env` | Remove: `TIMEZONE`, `FACE_ANTISPOOF_CONFIDENCE_THRESHOLD`, `FACE_SIMILARITY_THRESHOLD`, `ATTENDANCE_FREEZE_SECONDS`, `ATTENDANCE_FREEZE_SOUND_ENABLED`, `HYBRID_VOTING_WINDOW`, `HYBRID_BOOST_AMOUNT`, `HYBRID_LIVENESS_ENABLED`, `RECOGNITION_INTERVAL`. |
| `.env.example` | Same removals as `.env`. |
| `tests/unit/test_settings_resolver.py` | Rename seed tests. Add tests for JSON defaults loading. Update resolution tests to verify DB > JSON defaults (no env override). |
| `tests/unit/test_config.py` (if exists) | Update any seed-related tests. |
| `src/codemap.md` | Update startup flow description. |
| `src/attendance_system/codemap.md` | Update idempotent seeding description. |
| `src/attendance_system/core/codemap.md` | Update `seed_db_from_defaults()` description. |

### Seedable keys (9 keys)

```json
{
  "timezone": "UTC",
  "liveness_threshold": 0.5,
  "similarity_threshold": 0.6,
  "attendance_freeze_seconds": 30,
  "attendance_freeze_sound_enabled": true,
  "hybrid_voting_window": 5,
  "hybrid_boost_amount": 0.1,
  "hybrid_liveness_enabled": true,
  "recognition_interval": 3
}
```

### Non-DB settings (kept in `.env`)

```
DATABASE_PATH
FACE_RECOGNITION_MODEL_PATH
FACE_DETECTOR_MODEL_PATH
FACE_HEADPOSE_MODEL_PATH
FACE_ANTISPOOF_MODEL_PATH
CAMERA_INDEX
FACE_ANTISPOOF_ENABLED
FACE_HEADPOSE_ENABLED
```

## Testing

### Unit tests

1. `test_seed_db_from_defaults_writes_when_key_missing` — JSON value written to DB for unset key.
2. `test_seed_db_from_defaults_skips_when_key_exists` — Existing DB value preserved.
3. `test_seed_db_from_defaults_skips_null_json_value` — JSON value is `null` → no write.
4. `test_seed_db_from_defaults_converts_json_types_to_strings` — JSON `true` → `"true"`, `0.5` → `"0.5"`, `5` → `"5"`.
5. `test_seed_db_from_defaults_valid_zero_and_false_are_valid` — `0` and `false` are NOT skipped (only `null` skips).
6. `test_seed_db_from_defaults_json_file_missing_falls_back_to_empty` — FileNotFoundError → graceful fallback, no crash.
7. `test_seed_db_from_defaults_json_invalid_falls_back_to_empty` — JSONDecodeError → graceful fallback, no crash.
8. `test_seed_db_from_defaults_does_not_seed_in_init_mode` — Confirm `mode="init"` skips seeding.
9. `test_resolve_uses_db_for_seedable_keys` — DB value wins over JSON default.
10. `test_resolve_falls_back_to_json_default` — DB empty → JSON default used.
11. `test_resolve_falls_back_to_defaults_py_when_json_missing_key` — JSON lacks a key → `defaults.py` value used.
12. `test_resolve_ignores_env_for_seedable_keys` — Env var set but ignored for seedable keys.
13. `test_resolve_timezone_validated_by_zoneinfo` — Invalid timezone in JSON falls back to `defaults.py`.
14. `test_non_db_settings_still_use_env_override` — Paths, camera, feature flags still CLI > env > default.
15. `test_system_defaults_json_loads_successfully` — JSON file parses without error.
16. `test_system_defaults_json_has_all_seedable_keys` — All 9 keys present in JSON.

### Manual smoke test

1. Delete DB, run `attendance-app` → verify seedable keys populated from JSON.
2. Change a value via Admin UI → restart → verify UI change preserved.
3. Set env var for a seedable key → restart → verify env var does NOT override DB.
4. Run `attendance-storage-init` → verify no DB seeding (init mode).
