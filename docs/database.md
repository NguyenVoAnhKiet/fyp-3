# Database Design

## Technology

- **Engine**: SQLite3 (Python standard library)
- **Connector**: `sqlite3` with `check_same_thread=False` (required for PyQt5 camera thread)
- **Mode**: WAL (`PRAGMA journal_mode = WAL`)
- **Sync**: `PRAGMA synchronous = NORMAL`
- **FK enforcement**: `PRAGMA foreign_keys = ON` (set on every connection)

## Entity-Relationship Diagram

```
┌──────────────┐       ┌──────────────────┐       ┌────────────────────┐
│    users     │       │  face_references │       │     sessions       │
├──────────────┤       ├──────────────────┤       ├────────────────────┤
│ PK id         │──1:1──│ PK id            │       │ PK id              │
│    student_id │       │ FK user_id (UNQ) │       │    subject_name    │
│    full_name  │       │    embedding BLOB│       │    class_name      │
│    is_active  │       │    model_name    │       │    status          │
│ face_registered│      │    vector_length │       │    start_time      │
│    created_at │       │    created_at    │       │    end_time        │
│    updated_at │       └──────────────────┘       │ liveness_threshold │
└──────┬───────┘                                   │ similarity_thresh  │
       │                                           └─────────┬──────────┘
       │                                                     │
       │   ┌──────────────────┐      ┌────────────────────┐  │
       │   │  admin_creds     │      │ attendance_records │  │
       │   ├──────────────────┤      ├────────────────────┤  │
       │   │ PK id            │      │ PK id              │  │
       │   │    username (UNQ)│      │ FK session_id      │──┘
       │   │    password_hash │      │ FK user_id         │──┘
       │   │    created_at    │      │    status          │
       │   │    updated_at    │      │    recorded_at     │
       │   └──────────────────┘      │ UNIQUE(session_id, │
       │                             │       user_id)     │
       │                             └────────────────────┘
       │
       │   ┌──────────────────┐      ┌────────────────────┐
       │   │ recognition_events│     │  system_settings   │
       │   ├──────────────────┤      ├────────────────────┤
       │   │ PK id            │      │ PK setting_key     │
       │   │ FK session_id    │      │    setting_value   │
       │   │ FK user_id (NULL)│      │    value_type      │
       │   │    event_time    │      │    updated_at      │
       │   │    result        │      └────────────────────┘
       │   │    liveness_score│
       │   │    similarity_sc │
       │   │    details       │
       └───┴──────────────────┘
```

## Schema (7 tables)

### `users`
| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PK AUTOINCREMENT | Internal ID |
| `student_id` | TEXT | NOT NULL UNIQUE | Student/employee identifier |
| `full_name` | TEXT | NOT NULL | Display name |
| `is_active` | INTEGER | NOT NULL DEFAULT 1 | Soft delete flag |
| `face_registered` | INTEGER | NOT NULL DEFAULT 0 | Migration-added column |
| `created_at` | TEXT | NOT NULL | ISO 8601 timestamp |
| `updated_at` | TEXT | NOT NULL | ISO 8601 timestamp |

### `admin_credentials`
| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PK AUTOINCREMENT | — |
| `username` | TEXT | NOT NULL UNIQUE | Login name |
| `password_hash` | TEXT | NOT NULL | bcrypt hash |
| `created_at` | TEXT | NOT NULL | ISO 8601 |
| `updated_at` | TEXT | NOT NULL | ISO 8601 |

### `face_references`
| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PK AUTOINCREMENT | — |
| `user_id` | INTEGER | NOT NULL UNIQUE, FK→users(id) ON DELETE CASCADE | 1:1 mapping |
| `embedding` | BLOB | NOT NULL | Raw float32 bytes (optionally Fernet-encrypted) |
| `model_name` | TEXT | NOT NULL | e.g. "SFace" |
| `vector_length` | INTEGER | NOT NULL | e.g. 128 |
| `created_at` | TEXT | NOT NULL | ISO 8601 |

### `sessions`
| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PK AUTOINCREMENT | — |
| `subject_name` | TEXT | NOT NULL | e.g. "Trí Tuệ Nhân Tạo" |
| `class_name` | TEXT | NOT NULL | e.g. "IT01" |
| `status` | TEXT | NOT NULL | "active" or "closed" |
| `start_time` | TEXT | NOT NULL | ISO 8601 |
| `end_time` | TEXT | NULLABLE | ISO 8601 when closed |
| `liveness_threshold_snapshot` | REAL | NOT NULL | Threshold at session start |
| `similarity_threshold_snapshot` | REAL | NOT NULL | Threshold at session start |

### `recognition_events`
| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PK AUTOINCREMENT | — |
| `session_id` | INTEGER | NOT NULL, FK→sessions(id) ON DELETE CASCADE | Parent session |
| `user_id` | INTEGER | NULLABLE, FK→users(id) ON DELETE SET NULL | NULL for spoof/unrecognized |
| `event_time` | TEXT | NOT NULL | ISO 8601 |
| `result` | TEXT | NOT NULL | `success` / `duplicate` / `spoof_warning` / `unrecognized` / `correction` |
| `liveness_score` | REAL | NULLABLE | Raw logit_diff |
| `similarity_score` | REAL | NULLABLE | Cosine similarity |
| `details` | TEXT | NULLABLE | Additional context |

### `attendance_records`
| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PK AUTOINCREMENT | — |
| `session_id` | INTEGER | NOT NULL, FK→sessions(id) ON DELETE CASCADE | — |
| `user_id` | INTEGER | NOT NULL, FK→users(id) ON DELETE CASCADE | — |
| `status` | TEXT | NOT NULL | `success` / `duplicate` |
| `recorded_at` | TEXT | NOT NULL | ISO 8601 |
| | | UNIQUE(session_id, user_id) | One record per user per session |

### `system_settings`
| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `setting_key` | TEXT | PK | e.g. `liveness_threshold`, `camera_index` |
| `setting_value` | TEXT | NOT NULL | String value (parse per value_type) |
| `value_type` | TEXT | NULLABLE | `int`, `float`, `str` |
| `updated_at` | TEXT | NOT NULL | ISO 8601 |

## Access Patterns

### Database connection (`db.py`)

```python
@dataclass(slots=True)
class DatabaseConfig:
    path: Path
    timeout: float = 5.0  # SQLite busy timeout

class Database:
    def connect(self) -> sqlite3.Connection:
        # Creates parent dirs, sets pragmas, returns connection
    
    @contextmanager
    def session(self) -> Iterator[sqlite3.Connection]:
        # Auto-commits on success, rollbacks on exception
        # Always closes connection
```

### Repository pattern (`base_repository.py`)

```python
class BaseRepository:
    database: Database
    
    @contextmanager
    def connection(self):
        with self.database.session() as conn:
            yield conn
    
    def fetch_one(self, query, params) -> sqlite3.Row | None
    def fetch_all(self, query, params) -> list[sqlite3.Row]
    def execute(self, query, params) -> int  # returns lastrowid
```

Validates queries and parameters before execution. All SQL uses `?` placeholders.

### Migration Strategy

New columns are added via `ALTER TABLE ... ADD COLUMN` wrapped in try/except:

```python
try:
    connection.execute("ALTER TABLE users ADD COLUMN face_registered INTEGER NOT NULL DEFAULT 0")
except sqlite3.OperationalError:
    pass  # Column already exists
```

### Embedding Encryption

Optional (soft dependency on `cryptography`):

| Env var | Behavior |
|---------|----------|
| `FACE_EMBEDDING_FERNET_KEY` not set | Embeddings stored as raw float32 bytes |
| `FACE_EMBEDDING_FERNET_KEY` set | Embeddings encrypted/decrypted transparently via `FaceReferenceRepository` |

### Admin Seeding

On first boot, `StorageManager._seed_admin()` reads from env:
```python
username = os.getenv("ADMIN_USERNAME", "admin")
password = os.getenv("ADMIN_PASSWORD", "admin")
```
Password is bcrypt-hashed before storage.
