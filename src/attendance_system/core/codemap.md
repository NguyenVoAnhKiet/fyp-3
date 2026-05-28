# src/attendance_system/core/

## Responsibility

Core infrastructure layer: manages the SQLite database lifecycle (connection, schema, migrations), face-image disk storage, and bootstrap CLI. This is the lowest-level module — everything in `repositories/` and `services/` depends on it. No UI or business-logic code lives here.

## Key Modules

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
  3. `face_references` — per-user embedding blob, `model_name`, `vector_length`, FK → `users(id) ON DELETE CASCADE`.
  4. `sessions` — attendance sessions with `subject_name`, `class_name`, `status`, `start_time`/`end_time`, threshold snapshots.
  5. `recognition_events` — per-event recognition results, FK → `sessions(id) CASCADE`, FK → `users(id) SET NULL`.
  6. `attendance_records` — `UNIQUE(session_id, user_id)`, FKs → sessions CASCADE, users SET NULL.
  7. `system_settings` — key-value store with `value_type` hint.
- **`initialize_schema(connection)`** — runs all `SCHEMA_STATEMENTS`, then applies migrations:
  - Adds `face_registered` column to `users` (idempotent — catches `OperationalError`).
  - Migrates `attendance_records.user_id` from `NOT NULL CASCADE` to nullable `SET NULL` (detected by checking `sqlite_master` for old schema string).
- **`_migrate_attendance_records_cascade_to_setnull(connection)`** — heavy migration: disables FK checks, renames old table, creates new table with correct constraints, copies data, drops old table.

### `storage_manager.py` — Schema initialization + admin seeding

- **`StorageManager`** — `@dataclass(slots=True)` with a `database: Database` field.
- **`initialize()`** — opens a session, calls `initialize_schema(connection)`, then `_seed_admin(connection)`.
- **`_seed_admin(connection)`** — checks if `admin_credentials` is empty; if so, inserts a default admin from environment variables `ADMIN_USERNAME` / `ADMIN_PASSWORD` (fallback: `admin`/`admin`). Password is bcrypt-hashed with `bcrypt.gensalt()`.

**Important**: `StorageManager` is **not** a disk-storage manager (despite its name). It manages database schema + seed state. Actual face-image file storage lives in `services/` or `repositories/`.

### `bootstrap.py` — CLI entry point `attendance-storage-init`

- **`build_parser()`** — `argparse.ArgumentParser` with `--database-path` (default from `DATABASE_PATH` env var or `attendance.db`).
- **`initialize_storage(database_path)`** — constructs `Database(DatabaseConfig(path=database_path))` and passes it to `StorageManager.initialize()`.
- **`main(argv)`** — parses args, calls `initialize_storage`, prints confirmation, returns 0.
- **`__main__` guard** — `raise SystemExit(main())`.

**Important**: bootstrap does **not** call `load_dotenv()`. Environment variables (`DATABASE_PATH`, `ADMIN_USERNAME`, `ADMIN_PASSWORD`) must be set by the caller (the `attendance-app` entry point handles this).

### `__init__.py` — Package init

- Single docstring `"""Core storage utilities."""`. Exposes no symbols — all imports are explicit (e.g., `from .db import Database`).

## Integration

### Consumed by

| Consumer | What it uses |
|---|---|
| `repositories/` | `Database.session()` for all CRUD operations |
| `services/` | `DatabaseConfig`, `Database` — `AuthService`, `EnrollmentService`, `SettingsService` etc. compose their own `Database` instances |
| `attendance-storage-init` CLI | `bootstrap.main()` — the only way to initialize a fresh DB |

### Data flow

1. **Setup**: `attendance-storage-init` CLI → `bootstrap.main()` → `StorageManager.initialize()` → `initialize_schema(connection)` creates tables → `_seed_admin()` inserts default admin.
2. **Runtime**: `attendance-app` → `Database` is instantiated (via `DatabaseConfig` from env/settings) → wired into repositories → services call `database.session()` for transactional DB access.
3. **Schema changes**: New `CREATE TABLE` statements go into `SCHEMA_STATEMENTS`. Backward-compatible migrations (column additions, constraint changes) go into `initialize_schema()` after the schema loop.

### Key design decisions

- **WAL mode** — enables concurrent reads while a write is in progress; critical for camera threads writing recognition events while the UI reads attendance records.
- **`check_same_thread=False`** — required because PyQt camera threads (QThread workers) call DB methods from non-main threads.
- **Context manager pattern** — `database.session()` provides auto-commit/rollback/close, preventing leaked connections.
- **Schema-as-tuple** — all DDL is in a single immutable tuple; migrations are imperative after the schema loop. Simple and auditable.
- **No ORM** — raw SQL with `sqlite3.Row` keeps the dependency footprint minimal and avoids ORM overhead for a single-process desktop app.
