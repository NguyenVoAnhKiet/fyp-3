# System Architecture

## Overview

Face attendance system with anti-spoofing — a single-process Python desktop application using PyQt5 for the GUI, SQLite for storage, and ONNX Runtime for AI inference. The application runs 100% offline on a personal computer with a webcam.

```
┌─────────────────────────────────────────────────────────────────────┐
│                        attendance-app (main.py)                     │
│                                                                     │
│  ┌─────────┐   ┌──────────┐   ┌──────────────┐   ┌─────────────┐  │
│  │  PyQt5  │──▶│ Services │──▶│ Repositories │──▶│  SQLite DB  │  │
│  │   GUI   │   │          │   │              │   │             │  │
│  │ 30+ fps │   │ Business │   │   CRUD per   │   │ WAL mode    │  │
│  │         │   │  Logic   │   │   entity     │   │ bcrypt pwd  │  │
│  └─────────┘   └──────────┘   └──────────────┘   └─────────────┘  │
│       │              │                                              │
│       │              ▼                                              │
│       │   ┌──────────────────┐                                     │
│       │   │   AI Pipeline    │    ┌──────────────┐                 │
│       │   │  (CameraThread)  │───▶│ YuNet → SFace │                 │
│       │   │                  │    │ → MiniFASNet  │                 │
│       │   │   ~10 Hz infer   │    │ → MobileNetV2 │                 │
│       │   └──────────────────┘    └──────────────┘                 │
│       │              │                                              │
│       ▼              ▼                                              │
│  ┌──────────────────────────────────────────────────────┐          │
│  │           ONNX Runtime (shared native lib)           │          │
│  └──────────────────────────────────────────────────────┘          │
└─────────────────────────────────────────────────────────────────────┘
```

## Startup Sequence (`main.py`)

1. **Phase 1: Environment** — `load_dotenv()`, parse CLI args
2. **Phase 2: Configuration** — `SettingsResolver` class in `core/config.py` builds a frozen `SystemConfig` from **CLI > env > DB > default**. `set_timezone_config(config.timezone)` applies the resolved timezone to the global `time_utils._tz`.
3. **Phase 3: Bootstrap** — `initialize_storage()` creates schema + seeds admin
4. **Phase 4: Validate models** — Check ONNX files exist; graceful fallback for head-pose
5. **Phase 5: Wire services** — Build `FaceRecognizer`, `LivenessChecker`, `HeadPoseEstimator`, `Database`, all service classes
6. **Phase 6: Launch UI** — `MainWindow` with `QStackedWidget` routing
7. **Phase 7: Seed DB from env** — `SettingsResolver.seed_db_from_env()` writes env values into `system_settings` (idempotent: only writes if DB has no value yet; admin UI wins after first run).

```
main()
├── load_dotenv()
├── build_parser().parse_args()
├── SettingsResolver.resolve() → provisional SystemConfig
├── initialize_storage()
├── QApplication()
├── SettingsResolver.seed_db_from_env()
├── resolve_config() → final SystemConfig (includes DB)
├── set_timezone_config(config.timezone)
├── validate model files
├── HeadPoseEstimator (optional, graceful fallback)
├── Database, Services, AI components
└── MainWindow.show() → app.exec_()
```

## Layered Architecture

### 1. Core Layer (`attendance_system/core/`)

| Module | Responsibility |
|--------|---------------|
| `db.py` | `Database` class with `session()` context manager, WAL mode, `check_same_thread=False` |
| `schema.py` | DDL statements + migration framework (try/except `ALTER TABLE`) |
| `bootstrap.py` | CLI entry point `attendance-storage-init`; calls `StorageManager.initialize()` |
| `storage_manager.py` | Orchestrates schema creation + admin seeding from env |

### 2. Service Layer (`attendance_system/services/`)

| Service | Role | Key Dependencies |
|---------|------|-----------------|
| `ai_pipeline.py` | `FaceRecognizer` (SFace), `LivenessChecker` (MiniFASNet) | ONNX Runtime, OpenCV |
| `attendance_service.py` | Session lifecycle, check-in, duplicate detection, export | Repositories |
| `enrollment_service.py` | Save face embedding after capture | `FaceReferenceRepository` |
| `head_pose.py` | `HeadPoseEstimator` (MobileNetV2 ONNX) | ONNX Runtime |
| `authentication_service.py` | bcrypt password verification | `AdminRepository` |
| `settings_service.py` | Read/write `system_settings` table | `SystemSettingRepository` |
| `exceptions.py` | `ONNXInferenceError`, `PoseInferenceError`, `LivenessInferenceError` | — |

### 3. Repository Layer (`attendance_system/repositories/`)

All inherit from `BaseRepository` which provides:
- `connection()` — context manager wrapping `Database.session()`
- `fetch_one()`, `fetch_all()`, `execute()` — parameter-validated SQL helpers
- Input guards: `require_positive_int()`, `require_non_empty_text()`

| Repository | Table | Key Operations |
|------------|-------|---------------|
| `UserRepository` | `users` | CRUD, list_active, list_unregistered, soft delete |
| `FaceReferenceRepository` | `face_references` | upsert, get_by_user_id, decrypt embeddings |
| `SessionRepository` | `sessions` | create, close, get_sessions (filtered) |
| `AttendanceRepository` | `attendance_records` | record, duplicate, correct, join queries |
| `RecognitionEventRepository` | `recognition_events` | create, list_by_session |
| `AdminRepository` | `admin_credentials` | get_by_username, create |
| `SystemSettingRepository` | `system_settings` | get, upsert, delete |

### 4. UI Layer (`attendance_system/ui/`)

Three top-level views routed by `MainWindow` via `QStackedWidget`:

```
MainWindow (QMainWindow)
├── UserModeView      [idx 0] — attendance camera + session controls
├── LoginWidget       [idx 1] — admin authentication form
└── AdminDashboardView [idx 2] — sidebar navigation to sub-views
    ├── UserManagementWidget    — CRUD users (QTableWidget)
    ├── EnrollmentWidget        — face capture with pose guidance
    ├── AttendanceHistoryWidget — session browser + export
    └── SettingsWidget          — camera scan + threshold config
```

UI sub-views inside `AdminDashboardView` content area:
- `UserManagementWidget` — CRUD dialog, student_id is immutable after creation
- `EnrollmentWidget` — camera, progress bar, guidance text; auto-saves embedding
- `AttendanceHistoryWidget` — date/class/subject filters, export CSV/Excel
- `SettingsWidget` — camera scan thread, liveness/similarity spinboxes, timezone QComboBox (13 IANA choices, applies immediately via `set_timezone_config` + `timezone_signals.timezone_changed` signal), attendance-freeze QSpinBox (seconds) + QCheckBox (sound enabled)

### 5. Utils Layer (`attendance_system/utils/`)

| Module | Contents |
|--------|----------|
| `face_utils.py` | `_crop_face()` (scale param), `_create_face_detector()` (YuNet) |
| `time_utils.py` | `utc_now_iso()` |

## Threading Model

The AI pipeline runs on background QThreads to keep the UI responsive:

```
Main Thread (GUI)              CameraThread (QThread)
┌─────────────────┐           ┌──────────────────────┐
│  QApplication   │           │  cv2.VideoCapture    │
│  event loop     │◀─signal──│  YuNet detect         │
│  30+ fps paint  │  frame    │  MiniFASNet liveness  │
│                 │◀─signal──│  SFace recognize      │
│  result label   │  result  │  ~10 Hz inference     │
│  sidebar list   │           │  (every 3rd frame)   │
└─────────────────┘           └──────────────────────┘
```

- **Attendance Camera (`CameraThread`)**: Frame-skip (`_AI_FRAME_SKIP=3`), runs full pipeline at ~10 Hz. Circuit-breaker: 30 consecutive failures kills the thread.
- **Enrollment Camera (`EnrollmentCameraThread`)**: Horizontally mirrored for mirror-like UX. Pose-guided sequence (5 targets) or legacy landmark-based fallback.

## AI Pipeline

```
Camera frame (BGR)
    │
    ▼
YuNet FaceDetectorYN ──── [N×15] detection rows
    │
    ▼
MiniFASNet LivenessChecker ──── logit_diff → is_real?
    │
    ├── spoof → emit alert, skip
    │
    ▼ (real face)
SFace FaceRecognizer
    ├── alignCrop + feature → 128-dim embedding
    ├── cosine similarity against all DB references
    └── best match > threshold → RecognitionResult
```

## Configuration Resolution

The resolution logic lives in `attendance_system/core/config.py` as the `SettingsResolver` class. It builds a frozen `SystemConfig` dataclass using this priority order:

**CLI > env > DB > default**

Per-type resolvers:

| Resolver | Signature | Priority |
|----------|-----------|----------|
| `_resolve_path` | `(cli_value, env_key, default) → Path` | CLI > env > default (DB not consulted for paths) |
| `_resolve_int` | `(cli_value, env_value, db_value, default) → int` | CLI > env > DB > default |
| `_resolve_float` | `(cli_value, env_value, db_value, default) → float` | CLI > env > DB > default |
| `_resolve_bool` | `(cli_value, env_value, db_value, default) → bool` | CLI > env > DB > default |
| `_resolve_timezone` | `(env_value, db_value, default) → str` | **DB > env > default** (no CLI flag); validated against `zoneinfo.ZoneInfo` |

Key notes:

- **Timezone** has no CLI flag; its order is **DB > env > default** (env from `.env`, DB from admin UI change). Invalid IANA names fall back to the default.
- `_resolve_timezone` catches only `ZoneInfoNotFoundError` (not bare `Exception`) — narrowed per plan 0008 to expose real bugs.
- `seed_db_from_env()` performs idempotent one-time seeding: if `system_settings` already has a value for a key, the env var is **not** written (admin UI wins after first run). Seeds: `TIMEZONE`, `FACE_ANTISPOOF_CONFIDENCE_THRESHOLD`, `FACE_SIMILARITY_THRESHOLD`, `ATTENDANCE_FREEZE_SECONDS`, `ATTENDANCE_FREEZE_SOUND_ENABLED`.
- `SystemConfig` is `@dataclass(slots=True, frozen=True)` and is passed to services and UI as a single injected value.

## Timezone Subsystem

The timezone feature spans multiple files and is tied together by the module-level singleton in `time_utils.py`:

- **Storage**: All DB timestamps are UTC ISO-8601 (`utc_now_iso` from `utils/time_utils.py`).
- **Display**: Conversion to the configured local timezone is done at the presentation layer (`utc_to_local()`, `local_now_iso()`).
- **Configuration**: `set_timezone_config(tz_name)` mutates the module-level `_tz`. Called once at startup (from `main.py`) and again at runtime (from `SettingsWidget._save()`).
- **Cross-widget signal**: `time_utils.timezone_signals.timezone_changed` is a `pyqtSignal(str)` that fires on effective timezone change. `UserModeView` and `AttendanceHistoryWidget` connect to it to re-render their displays immediately.
- **Admin UX**: 13 curated IANA choices in `TIMEZONE_CHOICES` (Asia, Australia, Europe, America, UTC). `SettingsWidget` renders labels via `format_tz_label()` (e.g. `"Asia/Ho_Chi_Minh (UTC+07:00)"`).
- **Pre-existing stdlib quirk**: `ZoneInfo(name).utcoffset(None)` returns `None` for fixed-offset zones in Python's stdlib `zoneinfo`, so non-UTC dropdown labels currently render as the raw IANA name. The UTC entry is the only one that shows the offset. This is a pre-existing behavior; not addressed by plan 0008.

## Attendance Freeze UX

After a successful check-in, the camera feed freezes for `attendance_freeze_seconds` (default 4, 0 = disabled) and a green "✓ ĐIỂM DANH THÀNH CÔNG" overlay appears:

- **Optional sound**: `attendance_freeze_sound_enabled` plays a platform-default beep at the start of the freeze.
- **Persistence**: Both tunables are persisted via `SettingsService` and seeded from `.env` on first run via `SettingsResolver.seed_db_from_env()`.

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| `check_same_thread=False` | Required for PyQt5 camera thread accessing the same DB |
| `onnxruntime` imported before `PyQt5` | Avoids native DLL conflicts on Windows |
| WAL mode + synchronous=NORMAL | Read concurrency during camera threads writes |
| Embedding encryption (Fernet) | Optional, privacy-by-design; lazy import `cryptography` |
| Multi-pose enrollment bypasses liveness | Pose sequence provides implicit anti-spoofing |
| Enrollment frame mirrored horizontally | Mirror-like UX for natural head turns |
| `SystemConfig` is `frozen=True` and threaded through services/UI as a single value | Replaces the legacy "read from DB at every call site" pattern. See plan 0005 (archived 2026-06-05). |
| `timezone_signals.timezone_changed` decouples timezone-source widgets (Settings UI) from timezone-consumer widgets (User Mode, History) | No direct cross-widget coupling; consumer widgets connect to the signal once and re-render immediately. |
