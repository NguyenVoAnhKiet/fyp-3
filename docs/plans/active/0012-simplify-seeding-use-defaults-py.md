# 0012 — Simplify Seeding: Use defaults.py Directly

## Status

Draft

## Context

Plan 0011 introduced `system_defaults.json` to replace env-var seeding (completed 2026-06-16, archived). However, this created a **dual-source-of-truth problem**: `system_defaults.json` and `defaults.py` have different values for 5 of 9 seedable keys:

| Key | JSON value | defaults.py value |
|-----|-----------|-------------------|
| `timezone` | `"UTC"` | `"Asia/Ho_Chi_Minh"` |
| `attendance_freeze_seconds` | `30` | `4` |
| `attendance_freeze_sound_enabled` | `true` | `false` |
| `hybrid_liveness_enabled` | `true` | `false` |
| `recognition_interval` | `3` | `5` |

This creates confusion: which is the "real" default? The plan's own goal was to eliminate sources of confusion, not add new ones.

## Goal

Remove `system_defaults.json` and simplify `seed_db_from_defaults()` to read directly from `defaults.py`. This eliminates the dual-source problem and reduces code complexity.

## Non-Goals

- Changing the Admin UI or Settings widget.
- Changing the `SettingsService` DB layer.
- Changing non-DB settings resolution (paths, camera index, feature flags).
- Changing `resolve()` logic (already uses `defaults.py` as fallback).

## Design Decisions

| Decision | Options Considered | Choice | Rationale |
|----------|-------------------|--------|-----------|
| Source of truth for defaults | JSON / Python dict / Both | **Python (`defaults.py`)** | Already the fallback in `resolve()`, provides type hints, IDE autocomplete, static analysis. JSON adds no value for a desktop app. |
| `_SEED_DEFAULTS` structure | Explicit dict / Dynamic derivation | **Explicit dict** | Not all `DEFAULT_*` constants are seedable (e.g., model paths). `value_type` needed for `settings.set()`. Explicit dict documents the contract. |
| Startup validation | None / Module-level assertion | **Module-level assertion** | Verify all DB keys have corresponding `defaults.py` constants at import time. Fail-fast on drift. |
| Bool stringification | `"true"`/`"false"` / `"1"`/`"0"` | **`"1"`/`"0"`** | Match existing DB convention (`_BOOL_TRUE`/`_BOOL_FALSE` sets). |

## Tasks

| # | Task | Agent | Depends On | Status |
|---|------|-------|------------|--------|
| 1 | Update `config.py`: remove JSON loading, simplify seeding | @fixer | — | Pending |
| 2 | Delete `system_defaults.json` | @fixer | 1 | Pending |
| 3 | Update `pyproject.toml`: remove JSON package-data | @fixer | 2 | Pending |
| 4 | Update tests: remove JSON tests, update seed tests | @fixer | 1 | Pending |
| 5 | Update codemap docs | @fixer | 1 | Pending |
| 6 | Oracle review of implementation | @oracle | 1-5 | Pending |

## Implementation

### File changes

| File | Change |
|------|--------|
| `src/attendance_system/core/config.py` | Remove `import json`, `_load_defaults()`, `_SYSTEM_DEFAULTS`. Rename `_SEED_SETTINGS` → `_SEED_DEFAULTS`. Add module-level assertion. Simplify `seed_db_from_defaults()` to use `getattr(defaults, ...)`. |
| `src/attendance_system/core/system_defaults.json` | **Delete.** |
| `pyproject.toml` | Remove `[tool.setuptools.package-data]` section. |
| `tests/unit/test_config_resolver.py` | Remove JSON-specific tests. Update seed tests to not patch `_SYSTEM_DEFAULTS`. Add assertion test. |
| `src/codemap.md` | Update seeding description. |
| `src/attendance_system/codemap.md` | Update seeding description. |
| `src/attendance_system/core/codemap.md` | Remove `system_defaults.json` section, update seeding description. |

### Key code change

**Before (current):**
```python
_SEED_SETTINGS: dict[str, str] = { ... }

def _load_defaults() -> dict[str, Any]:
    json_path = Path(__file__).parent / "system_defaults.json"
    try:
        return json.loads(json_path.read_text())
    except ...:
        return {}

_SYSTEM_DEFAULTS = _load_defaults()

def seed_db_from_defaults(self, settings):
    for db_key, value_type in _SEED_SETTINGS.items():
        if settings.get(db_key) is not None:
            continue
        value = _SYSTEM_DEFAULTS.get(db_key)
        if value is None:
            continue
        settings.set(db_key, _stringify_for_db(value, value_type), value_type)
```

**After (simplified):**
```python
_SEED_DEFAULTS: dict[str, str] = {
    "timezone": "str",
    "liveness_threshold": "float",
    "similarity_threshold": "float",
    "attendance_freeze_seconds": "int",
    "attendance_freeze_sound_enabled": "bool",
    "hybrid_voting_window": "int",
    "hybrid_boost_amount": "float",
    "hybrid_liveness_enabled": "bool",
    "recognition_interval": "int",
}

# Module-level assertion: verify all keys have defaults.py constants
for _db_key in _SEED_DEFAULTS:
    _const_name = f"DEFAULT_{_db_key.upper()}"
    if not hasattr(defaults, _const_name):
        raise RuntimeError(f"Missing default constant: {_const_name} for seed key {_db_key}")

def seed_db_from_defaults(self, settings):
    if self._mode == "init":
        return
    for db_key, value_type in _SEED_DEFAULTS.items():
        if settings.get(db_key) is not None:
            continue
        value = getattr(defaults, f"DEFAULT_{db_key.upper()}")
        settings.set(db_key, _stringify_for_db(value, value_type), value_type)
```

### Default values (from defaults.py — canonical)

```python
DEFAULT_TIMEZONE = "Asia/Ho_Chi_Minh"
DEFAULT_LIVENESS_THRESHOLD = 0.5
DEFAULT_SIMILARITY_THRESHOLD = 0.6
DEFAULT_ATTENDANCE_FREEZE_SECONDS = 4
DEFAULT_ATTENDANCE_FREEZE_SOUND_ENABLED = False
DEFAULT_HYBRID_VOTING_WINDOW = 5
DEFAULT_HYBRID_BOOST_AMOUNT = 0.10
DEFAULT_HYBRID_LIVENESS_ENABLED = False
DEFAULT_RECOGNITION_INTERVAL = 5
```

## Testing

### Unit tests to update

1. `test_seed_db_from_defaults_writes_when_key_missing` — update to use `getattr(defaults, ...)` instead of patching `_SYSTEM_DEFAULTS`
2. `test_seed_db_from_defaults_skips_when_key_exists` — unchanged
3. `test_seed_db_from_defaults_converts_json_types_to_strings` — rename, update to use `defaults` constants
4. `test_seed_db_from_defaults_skips_null_json_value` — **remove** (no null values from `defaults.py`)
5. `test_seed_db_from_defaults_valid_zero_and_false_are_valid` — update to use `defaults` constants
6. `test_seed_db_from_defaults_json_file_missing_falls_back_to_empty` — **remove** (no JSON file)
7. `test_all_seed_keys_have_defaults_constant` — **new** (verify module-level assertion)

### Tests to remove

- `test_system_defaults_json_loads_successfully`
- `test_system_defaults_json_has_all_seedable_keys`

### Manual smoke test

1. Delete DB, run `attendance-app` → verify seedable keys populated from `defaults.py`
2. Change a value via Admin UI → restart → verify UI change preserved
3. Run `attendance-storage-init` → verify no DB seeding (init mode)
