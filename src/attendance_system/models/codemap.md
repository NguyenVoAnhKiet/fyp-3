# `models/` — Domain Model Layer

## Responsibility

Defines the domain entities as plain `@dataclass` objects that mirror database rows. These are the single source of truth for data shape across the application — consumed by repositories for persistence and services for business logic. No ORM, no business logic, no behaviour beyond what `dataclass` provides.

## Entities

| Class | Purpose |
|---|---|
| `UserAccount` | A registered student with `student_id`, `full_name`, and `is_active` flag. |
| `FaceReference` | A face-embedding vector (`embedding` blob) for a `user_id`, tagged with `model_name` and `vector_length`. |
| `AttendanceSession` | An attendance-taking session scoped to a `subject_name` / `class_name`, carrying frozen threshold values (`liveness_threshold_snapshot`, `similarity_threshold_snapshot`) captured at creation time. |
| `RecognitionEvent` | A single recognition attempt within a session — links `session_id` and optional `user_id`, stores timestamps (`event_time`), outcome (`result`), and optional scores/details. |
| `AttendanceRecord` | The final attendance outcome for a user in a session — `session_id`, `user_id`, `status`, and `recorded_at`. |
| `SystemSetting` | Key-value configuration row (`setting_key`, `setting_value`, `value_type`). |
| `AdminCredential` | Admin login credentials: `username` and `password_hash`. |

## Design

- All classes use `@dataclass(slots=True)` — frozen by convention (no `frozen=True` set explicitly, but treated as immutable DTOs).
- No inheritance, no mixins, no custom `__init__`, no methods with side effects.
- Nullable fields use `| None` (e.g. `RecognitionEvent.user_id`, `*.score`, `*.details`).
- Optional fields with defaults are declared last per PEP 8 / `@dataclass` ordering requirements.

## Integration

- **Repositories** (`repositories/`) map these entities to/from SQLite rows via `sqlite3.Row` factories and raw SQL. Each repository handles CRUD for one entity type.
- **Services** (`services/`) compose repositories and AI pipeline outputs into higher-level operations (attendance processing, enrollment, auth, settings management).
- **UI** (`ui/`) never imports entities directly — it works through services, receiving serialised data or service-layer return types.
- **`__init__.py`** re-exports nothing; consumers import directly from `entities.py`.
