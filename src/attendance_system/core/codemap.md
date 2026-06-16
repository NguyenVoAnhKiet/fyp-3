# src/attendance_system/core/

## Responsibility

Core infrastructure layer: manages configuration resolution (CLI > env > DB > default), SQLite database lifecycle (connection, schema, migrations), face-image disk storage, and bootstrap CLI. This is the lowest-level module — everything in `repositories/` and `services/` depends on it. No UI or business-logic code lives here.

## Key Modules

### `config.py` — Centralized configuration resolution (Plan 0005)

- **`SystemConfig`** — `@dataclass(slots=True, frozen=True)` holding all resolved system tunables exactly once: database/model paths, camera index, feature flags (`antispoof_enabled`, `headpose_enabled`), AI thresholds, timezone, attendance UX settings. Immutable; constructed by `SettingsResolver` at startup.
- **`SettingsResolver`** — Class that performs resolution in two modes:
  - `"runtime"` (default) — full resolution; used by `main.py`. For DB-seedable keys, resolution is **DB > defaults.py** (env vars not consulted). For non-DB settings (paths, camera, feature flags): CLI > env > default.
  - `"init"` — minimal resolution for `attendance-storage-init`; only `database_path` matters, skips env seeding (bootstrap does not call `load_dotenv()`).
- **`resolve_config()`** — Convenience factory that wires `SettingsService.get` as the `db_reader` for the resolver.
- **`seed_db_from_defaults()`** — Idempotent defaults→DB seeding: reads values from `defaults.py` constants via `getattr` and writes to `system_settings` only if the DB key is unset (preserving Admin UI overrides). Skipped in init mode.
- **`_SEED_SETTINGS`** — Dict mapping DB key → value_type string for the 9 seedable settings.
- **Module-level assertion** — Verifies every `_SEED_SETTINGS` key has a corresponding `DEFAULT_*` constant in `defaults.py` at import time. Fail-fast on drift.
- **Per-type resolvers** — `_resolve_path`, `_resolve_int`, `_resolve_float`, `_resolve_bool`, `_resolve_timezone`. Each encapsulates CLI > env > [DB] > default fallback logic with proper empty-string and parse-error handling. Timezone uses DB > default (no CLI flag, no env) with `zoneinfo.ZoneInfo` validation.

**Important**: `bootstrap.py` uses `SettingsResolver(mode="init")` with `env={}` for hermetic resolution — no `os.environ` consulted, no `.env` loaded. The `SettingsResolver` owns all parsing logic (int/bool/float) so call sites don't duplicate it.

### `defaults.py` — Default values for all system tunables

- Single source of truth for every tunable default. Referenced by `SystemConfig` field defaults and `SettingsResolver` when no DB value is set (also used for first-run DB seeding).
- Centralizing defaults here makes threshold migrations (e.g., `0.5 → 0.3`) a one-file change instead of touching 4+ call sites.
- Key constants: `DEFAULT_LIVENESS_THRESHOLD`, `DEFAULT_SIMILARITY_THRESHOLD`, `DEFAULT_CAMERA_INDEX`, `DEFAULT_ATTENDANCE_FREEZE_SECONDS`, model file paths, feature flag defaults (`DEFAULT_ANTISPOOF_ENABLED`, `DEFAULT_HEADPOSE_ENABLED`), `DEFAULT_TIMEZONE`.

### `db.py` — Database connection management

- **`DatabaseConfig`** — `@dataclass(slots=True)` holding `path: Path` and `timeout: float`. Validates path in `__post_init__` (rejects parent-traversal `..` segments).
- **`Database`** — connection factory, **not** a singleton. Creates fresh `sqlite3.Connection` per call with:
  - `check_same_thread=False` (required for cross-thread usage from PyQt workers).
  - `row_factory = sqlite3.Row` for dict-like row access.
  - PRAGMAs: `foreign_keys = ON`, `journal_mode = WAL`, `synchronous = NORMAL`.
- **`Database.session()`** — `@contextmanager` that yields a connection, commits on success, rollbacks on exception, always closes. Preferred over raw `connect()`.

**Important**: Not a singleton. Each `Database` instance is configured with its own `DatabaseConfig`. The caller (e.g., `DatabaseManager` in `services/`) is responsible for reuse.

### `schema.py` — SQL schema definitions and migrations

- **`SCHEMA_STATEMENTS`** — tuple of 7 `CREATE TABLE IF NOT EXISTS` strings:
  1. `users` — students with `student_id` (unique), `full_name`, `is_active`, `face_registered`, timestamps.
  2. `admin_credentials` — `username` (unique), `password_hash`, timestamps.
  3. `face_references` — per-user embedding blob, `model_name`, `vector_length`, `pose_label`, `UNIQUE(user_id, pose_label)`, FK → `users(id) ON DELETE CASCADE`.
  4. `sessions` — attendance sessions with `subject_name`, `class_name`, `status`, `start_time`/`end_time`, threshold snapshots.
  5. `recognition_events` — per-event recognition results, FK → `sessions(id) CASCADE`, FK → `users(id) SET NULL`.
  6. `attendance_records` — `UNIQUE(session_id, user_id)`, FKs → sessions CASCADE, users SET NULL.
  7. `system_settings` — key-value store with `value_type` hint.
- **`initialize_schema(connection)`** — runs all `SCHEMA_STATEMENTS`, then applies migrations:
  - Adds `face_registered` column to `users` (idempotent — catches `OperationalError`).
  - Migrates `attendance_records.user_id` from `NOT NULL CASCADE` to nullable `SET NULL` (detected by checking `sqlite_master` for old schema string).
  - Adds `pose_label` column and `UNIQUE(user_id, pose_label)` to `face_references` (detected via `PRAGMA table_info`).
- **`_migrate_attendance_records_cascade_to_setnull(connection)`** — heavy migration: disables FK checks, renames old table, creates new table with correct constraints, copies data, drops old table.
- **`_migrate_face_references_add_pose_label(connection)`** — similar table-recreate migration adding `pose_label TEXT NOT NULL DEFAULT 'center'` and `UNIQUE(user_id, pose_label)`. Existing rows preserved with `pose_label = 'center'`; duplicate user_id rows resolved by keeping smallest id.
- Migration errors are logged explicitly and re-raised (no silent failures).

### `storage_manager.py` — Schema initialization + admin seeding

- **`StorageManager`** — `@dataclass(slots=True)` with a `database: Database` field.
- **`initialize()`** — opens a session, calls `initialize_schema(connection)`, then `_seed_admin(connection)`.
- **`_seed_admin(connection)`** — checks if `admin_credentials` is empty; if so, inserts a default admin from environment variables `ADMIN_USERNAME` / `ADMIN_PASSWORD` (fallback: `admin`/`admin`). Password is bcrypt-hashed with `bcrypt.gensalt()`.

**Important**: `StorageManager` is **not** a disk-storage manager (despite its name). It manages database schema + seed state. Actual face-image file storage lives in `services/` or `repositories/`.

### `bootstrap.py` — CLI entry point `attendance-storage-init`

- **`build_parser()`** — `argparse.ArgumentParser` with `--database-path` (default from `DATABASE_PATH` env var or `attendance.db`).
- **`initialize_storage(database_path)`** — constructs `Database(DatabaseConfig(path=database_path))` and passes it to `StorageManager.initialize()`.
- **`main(argv)`** — creates a `SettingsResolver(mode="init")`, calls `resolver.resolve(cli=args, env={}, db_reader=None)` to get the database path (hermetic — no `os.environ` or `.env`), then calls `initialize_storage`. Returns 0.
- **`__main__` guard** — `raise SystemExit(main())`.

**Important**: bootstrap does **not** call `load_dotenv()`. It uses `SettingsResolver` in `"init"` mode with an empty env mapping so it is fully hermetic. Environment variables (`DATABASE_PATH`, `ADMIN_USERNAME`, `ADMIN_PASSWORD`) for seeding are read directly by `StorageManager` via `os.getenv`.

### `liveness_tracker.py` — Backward-compatibility re-export shim

- Deprecated re-export shim (`attendance_system.core.liveness_tracker` → `attendance_system.services.liveness_tracker`).
- Re-exports: `LivenessTracker`, `TrackedFace`, `compute_iou`, and constants (`ALPHA`, `IOU_THRESHOLD`, `MAX_MISSES`).
- Canonical implementation moved to `services/` in Plan 0004; this shim preserves existing imports.

### `__init__.py` — Package init

- Single docstring `"""Core storage utilities."""`. Exposes no symbols — all imports are explicit (e.g., `from .db import Database`).

## Integration

### Consumed by

| Consumer | What it uses |
|---|---|
| `repositories/` | `Database.session()` for all CRUD operations |
| `services/` | `DatabaseConfig`, `Database` — `AuthService`, `EnrollmentService`, `SettingsService` etc. compose their own `Database` instances |
| `main.py` (runtime init) | `SettingsResolver.resolve()` → `SystemConfig`, then `seed_db_from_defaults()` for first-run defaults→DB seeding |
| `attendance-storage-init` CLI | `bootstrap.main()` — the only way to initialize a fresh DB |
| `src/main.py` bootstrap order | `load_dotenv()` → `SettingsResolver.resolve()` → `set_timezone_config()` → `initialize_storage()` |

### Data flow

1. **Startup**: `attendance-app` → `load_dotenv()` → `SettingsResolver.resolve()` builds frozen `SystemConfig` (CLI > env > DB > default) → `set_timezone_config()` → `initialize_storage()` creates/upgrades schema → `seed_db_from_defaults()` idempotently writes `defaults.py` values → wire services → launch UI.
2. **Storage init**: `attendance-storage-init` CLI → `bootstrap.main()` → `SettingsResolver(mode="init")` resolves only `database_path` → `StorageManager.initialize()` → `initialize_schema(connection)` creates tables → `_seed_admin()` inserts default admin.
3. **Runtime**: `Database` is instantiated (via `DatabaseConfig` from `SystemConfig`) → wired into repositories → services call `database.session()` for transactional DB access.
4. **Schema changes**: New `CREATE TABLE` statements go into `SCHEMA_STATEMENTS`. Backward-compatible migrations (column additions, constraint changes, table recreations) go into `initialize_schema()` after the schema loop.
5. **Admin UI overrides**: Admin changes a threshold/timezone/UX setting in UI → `SettingsService.set()` writes to `system_settings` DB → takes effect immediately. On next app restart, `SettingsResolver` reads from DB (priority level 3) — seeded env values do not overwrite because `seed_db_from_env` is idempotent (only writes if key is unset).

### Key design decisions

- **WAL mode** — enables concurrent reads while a write is in progress; critical for camera threads writing recognition events while the UI reads attendance records.
- **`check_same_thread=False`** — required because PyQt camera threads (`QThread` workers) call DB methods from non-main threads.
- **Context manager pattern** — `database.session()` provides auto-commit/rollback/close, preventing leaked connections.
- **Schema-as-tuple** — all DDL is in a single immutable tuple; migrations are imperative after the schema loop. Simple and auditable.
- **No ORM** — raw SQL with `sqlite3.Row` keeps the dependency footprint minimal and avoids ORM overhead for a single-process desktop app.
- **Frozen `SystemConfig`** — immutable config object prevents accidental post-construction mutation; single injection point for all tunables instead of ad-hoc env reads throughout the codebase.
- **`SettingsResolver` two modes** — `"init"` mode keeps `bootstrap.py` hermetic (no `load_dotenv()`, no `os.environ` consultation), while `"runtime"` mode provides full resolution. This prevents the init CLI from accidentally pulling in `.env` values meant for the app.
- **Idempotent defaults→DB seeding** — `seed_db_from_defaults()` only writes if the DB key is unset, so Admin UI changes survive restarts. All defaults come from `defaults.py`.
- **Defaults centralized** — all default values in `defaults.py` instead of scattered across modules. Threshold migrations become a one-file change.
- **Liveness tracker re-export** — the old `core/liveness_tracker.py` re-exports from `services/` for backward compatibility without code duplication.
