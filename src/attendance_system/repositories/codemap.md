# Repositories — Data Access Layer

## Responsibility

Provide CRUD persistence for every entity in the system. Each repository encapsulates all SQL queries for a single database table, exposing domain-typed methods rather than raw SQL to the service layer. All repositories share the same `Database` session and connection lifecycle.

## Design

### BaseRepository pattern (`base_repository.py`)

All repositories inherit from `BaseRepository`, a `@dataclass(slots=True)` holding a `Database` instance. It provides:

| Method | Purpose |
|---|---|
| `connection()` | Context manager yielding a `sqlite3.Connection` (auto-commit on success, rollback on exception) |
| `fetch_one()` | Execute SELECT returning a single `sqlite3.Row` or `None` |
| `fetch_all()` | Execute SELECT returning `list[sqlite3.Row]` |
| `execute()` | Execute INSERT/UPDATE/DELETE returning `lastrowid` |

Validation helpers (`require_positive_int`, `require_non_empty_text`) are called by every public method before touching the DB. `StorageError` and `DuplicateAttendanceError` are defined here as well.

### FaceReferenceRepository class-level cache (`face_reference_repository.py`)

The most notable design choice: `_cache_all` is a **`ClassVar[dict[str, list[dict]]]` keyed by database path** (from `self.database.config.path`). This means:

- Every `FaceReferenceRepository` instance (across `FaceRecognizer`, `EnrollmentService`, `UserManagementWidget`) shares the same cached data automatically — no singleton or dependency-injection container needed.
- `get_all()` reads from cache if present, otherwise fetches from DB and populates the cache.
- Every write path (`upsert()`, `delete_by_user_id()`) calls `_invalidate_cache()` to clear the entry for that database path.
- **Must be invalidated on every write path** — the AGENTS.md hard-gotcha explicitly warns about this.

Encryption is handled transparently: if `FACE_EMBEDDING_FERNET_KEY` is set, embeddings are encrypted/decrypted on-the-fly using `cryptography.fernet`.

## Key Files

| File | Repository | Table | Key Methods |
|---|---|---|---|
| `base_repository.py` | `BaseRepository` | — | Shared CRUD primitives, validation, errors |
| `admin_repository.py` | `AdminRepository` | `admin_credentials` | `get_by_username()`, `create()` |
| `attendance_repository.py` | `AttendanceRepository` | `attendance_records` | `record()`, `get()`, `correct()`, `list_by_session()`, `get_records_with_users()` |
| `face_reference_repository.py` | `FaceReferenceRepository` | `face_references` | `upsert()`, `get_by_user_id()`, `get_all()`, `delete_by_user_id()` |
| `recognition_event_repository.py` | `RecognitionEventRepository` | `recognition_events` | `create()`, `list_by_session()` |
| `session_repository.py` | `SessionRepository` | `sessions` | `create()`, `get_by_id()`, `update_status()`, `close()`, `list_active()`, `get_sessions()` |
| `system_setting_repository.py` | `SystemSettingRepository` | `system_settings` | `upsert()`, `get()`, `list_all()`, `delete()` |
| `user_repository.py` | `UserRepository` | `users` | `create()`, `get_by_id()`, `get_by_student_id()`, `list_active()`, `list_unregistered()`, `update()`, `deactivate()` |

## Integration

- **Consumed by:** `src/attendance_system/services/` — every service (`AuthService`, `AttendanceService`, `EnrollmentService`, `FaceRecognizer`, `SettingsService`, etc.) constructs its repositories by passing a `Database` instance.
- **Depends on:** `attendance_system.core.db.Database` (which provides `sqlite3.Connection` sessions with WAL mode, foreign keys, and `sqlite3.Row` factory) and `attendance_system.models.entities` (dataclass entities often used to represent rows returned from repositories).
- **Transaction scope:** Each repository method opens its own connection via `self.connection()` (auto-commit on exit). Cross-repository transactions must be managed at the service layer using `database.session()` directly.
