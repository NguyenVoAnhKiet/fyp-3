# Module Reference

## Package Structure

```
src/
├── main.py                              # Entry point: CLI, config, wiring, launch
└── attendance_system/
    ├── __init__.py
    ├── core/
    │   ├── config.py                   # SettingsResolver + SystemConfig (CLI > env > DB > default)
    │   ├── db.py                        # Database + DatabaseConfig + session()
    │   ├── schema.py                    # DDL + migration helpers
    │   ├── bootstrap.py                 # CLI entry point for DB init
    │   └── storage_manager.py           # Schema init + admin seeding
    ├── models/
    │   └── entities.py                  # @dataclass entities (slots=True)
    ├── repositories/
    │   ├── base_repository.py           # BaseRepository + StorageError
    │   ├── admin_repository.py          # Admin credentials
    │   ├── attendance_repository.py     # Attendance records
    │   ├── face_reference_repository.py # Face embeddings (encrypted)
    │   ├── recognition_event_repository.py
    │   ├── session_repository.py        # Attendance sessions
    │   ├── system_setting_repository.py
    │   └── user_repository.py           # User CRUD
    ├── services/
    │   ├── ai_pipeline.py               # FaceRecognizer + LivenessChecker
    │   ├── attendance_service.py        # Session lifecycle + export
    │   ├── authentication_service.py    # bcrypt auth
    │   ├── enrollment_service.py        # Face registration
    │   ├── exceptions.py                # ONNX error hierarchy
    │   ├── head_pose.py                 # HeadPoseEstimator
    │   └── settings_service.py          # System settings CRUD
    ├── ui/
    │   ├── main_window.py               # QMainWindow + QStackedWidget router
    │   ├── admin_dashboard_view.py      # Admin shell: sidebar + content
    │   ├── attendance_history_widget.py # Session browser + export
    │   ├── camera_thread.py             # Attendance camera QThread
    │   ├── constants.py                 # QFont constants (JetBrains Mono)
    │   ├── enrollment_camera_thread.py  # Enrollment camera QThread
    │   ├── enrollment_widget.py         # Face capture UI
    │   ├── login_widget.py              # Admin login form
    │   ├── settings_widget.py           # Camera scan + threshold config
    │   ├── user_management_widget.py    # User CRUD table
    │   └── user_mode_view.py            # Attendance session UI
    └── utils/
        ├── face_utils.py                # _crop_face(), _create_face_detector()
        └── time_utils.py                # set_timezone_config, get_timezone_name, utc_to_local, local_to_utc, format_tz_label, timezone_signals
```

## Entry Points

| Command | Module:function | Description |
|---------|----------------|-------------|
| `attendance-app` | `main:main` | Launch the GUI application |
| `attendance-storage-init` | `attendance_system.core.bootstrap:main` | Initialize DB schema |

## Detailed Module Reference

### `src/main.py`

The application entry point. Accepts optional `argv` list for testability (never calls `sys.argv` directly).

**CLI Arguments:**
| Flag | Env Var | Default | Description |
|------|---------|---------|-------------|
| `--database-path` | `DATABASE_PATH` | `attendance.db` | SQLite path |
| `--liveness-model` | `FACE_ANTISPOOF_MODEL_PATH` | `models/anti_spoof/best_model_quantized.onnx` | MiniFASNet ONNX |
| `--recognition-model` | `FACE_RECOGNITION_MODEL_PATH` | `models/face_recognition/face_recognition_sface_2021dec.onnx` | SFace ONNX |
| `--detector-model` | `FACE_DETECTOR_MODEL_PATH` | `models/face_detection/face_detection_yunet_2023mar.onnx` | YuNet ONNX |
| `--headpose-model` | `FACE_HEADPOSE_MODEL_PATH` | `models/head_pose/mobilenetv2.onnx` | MobileNetV2 ONNX |
| `--camera-index` | `CAMERA_INDEX` | `0` | Camera device index |

**Key functions:**
- `main(argv=None)` — Full application lifecycle: parses CLI args, builds a `SystemConfig` via `resolve_config(...)`, applies timezone via `set_timezone_config(config.timezone)`, validates model files, initializes storage, wires services, and launches `MainWindow`.
- Note: The per-type resolvers (`_resolve_path`, `_resolve_int`, `_resolve_float`, `_resolve_bool`, `_resolve_timezone`) live in `attendance_system.core.config.SettingsResolver`, not in `main.py`.
- First-run seeding from env is done by `SettingsResolver.seed_db_from_env()` (not `_seed_threshold`).

### `src/attendance_system/core/`

#### `db.py`
- `DatabaseConfig` — dataclass with path traversal guard (`__post_init__` rejects `..`)
- `Database` — `connect()` returns connection with WAL+FK pragmas; `session()` is the primary API

#### `schema.py`
- `SCHEMA_STATEMENTS` — tuple of 7 `CREATE TABLE` statements
- `initialize_schema(connection)` — Executes DDL + migrations

#### `bootstrap.py`
- Standalone CLI entry point (`attendance-storage-init`)
- Does NOT call `load_dotenv()` — reads `DATABASE_PATH` from env directly if not passed as CLI arg

#### `config.py`
- `SystemConfig` — frozen dataclass (`slots=True, frozen=True`) with all resolved tunables: paths, camera index, feature flags, AI thresholds, timezone, attendance-freeze UX. Single source of truth passed to services and UI.
- `SettingsResolver` — class that performs `CLI > env > DB > default` resolution. Two modes: `"runtime"` (default, used by `main.py`) and `"init"` (used by `bootstrap.py`).
  - `resolve(cli, env, db_reader)` → `SystemConfig`
  - `seed_db_from_env(settings, env)` — idempotent one-time env→DB seeding
  - Per-type resolvers: `_resolve_path`, `_resolve_int`, `_resolve_float`, `_resolve_bool`, `_resolve_timezone` (validates against `zoneinfo.ZoneInfo`, catches `ZoneInfoNotFoundError`)
- `resolve_config(cli_args, env, settings_service, mode)` — convenience factory wiring `SettingsService.get` as the DB reader.

#### `storage_manager.py`
- `StorageManager.initialize()` — schema + seed admin
- `_seed_admin()` — Only seeds if `admin_credentials` table is empty

### `src/attendance_system/models/entities.py`

Six dataclasses with `slots=True`:

| Entity | Fields |
|--------|--------|
| `UserAccount` | `student_id`, `full_name`, `is_active` |
| `FaceReference` | `user_id`, `embedding`, `model_name`, `vector_length` |
| `AttendanceSession` | `subject_name`, `class_name`, `status`, `liveness_threshold_snapshot`, `similarity_threshold_snapshot` |
| `RecognitionEvent` | `session_id`, `user_id`, `event_time`, `result`, `liveness_score`, `similarity_score`, `details` |
| `AttendanceRecord` | `session_id`, `user_id`, `status`, `recorded_at` |
| `SystemSetting` | `setting_key`, `setting_value`, `value_type` |
| `AdminCredential` | `username`, `password_hash` |

### `src/attendance_system/repositories/`

All repositories inherit from `BaseRepository` and use parameter validation:

#### `base_repository.py`
- `StorageError`, `DuplicateAttendanceError` — custom exceptions
- `BaseRepository.database` — reference to `Database` instance
- `connection()` — context manager wrapping `Database.session()`
- `fetch_one()`, `fetch_all()`, `execute()` — validated SQL helpers
- `require_positive_int()`, `require_non_empty_text()` — input guards

#### Repository Key Methods
| Repository | Key Methods |
|------------|-------------|
| `UserRepository` | `create`, `get_by_id`, `get_by_student_id`, `list_active`, `list_unregistered`, `update`, `deactivate` |
| `FaceReferenceRepository` | `upsert` (ON CONFLICT), `get_by_user_id`, `get_all`, `delete_by_user_id`; transparent encryption/decryption |
| `SessionRepository` | `create`, `get_by_id`, `close`, `update_status`, `get_sessions` (filtered), `list_active`, `list_unique_classes`, `list_unique_subjects` |
| `AttendanceRepository` | `record`, `get`, `correct`, `list_by_session`, `get_records_with_users` (join) |
| `RecognitionEventRepository` | `create`, `list_by_session` |
| `AdminRepository` | `get_by_username`, `create` |
| `SystemSettingRepository` | `get`, `upsert`, `list_all`, `delete` |

### `src/attendance_system/services/`

#### `exceptions.py`
```
ONNXInferenceError(message, input_shape=None, model_path=None)
├── PoseInferenceError
└── LivenessInferenceError
```

#### `ai_pipeline.py`
- **`LivenessResult`** — `NamedTuple(is_real: bool, score: float)`
- **`RecognitionResult`** — `NamedTuple(user_id, full_name, student_id, similarity)`
- **`LivenessChecker`** — MiniFASNet wrapper. `check(face_rgb, threshold)` → `LivenessResult`. Bypass when `model_path=None`.
- **`FaceRecognizer`** — SFace wrapper. `get_embedding(frame, face_row)` → `np.ndarray | None`. `identify(frame, face_row, threshold)` → `RecognitionResult | None`. `average_embeddings(list)` → unit normalized mean.

#### `attendance_service.py`
- Orchestrates `SessionRepository`, `AttendanceRepository`, `RecognitionEventRepository`, `UserRepository`
- `start_session()` — Creates session with threshold snapshots (records config at session start)
- `record_success()` — Atomically inserts recognition_event + attendance_record
- `record_duplicate()` — Handles `IntegrityError` gracefully, returns existing record ID
- `record_spoof_warning()` / `record_unrecognized()` — Log events without attendance records
- `end_session()` — Sets status to "closed"
- `get_sessions()` — Filtered by date range, class, subject
- `export_session_to_csv()` / `export_session_to_excel()` — Pandas-based export (soft dependency)

#### `enrollment_service.py`
- Thin wrapper: `save_face_reference(user_id, embedding, model_name, vector_length)` → upserts face + marks user as registered

#### `head_pose.py`
- **`PoseAngles(pitch, yaw, roll)`** — NamedTuple
- **`HeadPoseEstimator`** — MobileNetV2 ONNX wrapper
- `estimate(face_crop_bgr)` → `(pitch, yaw, roll)` in degrees
- `_preprocess()` — Resize to 224×224, ImageNet normalization
- `_rotation_matrix()` — Extract 3×3 matrix from model output
- `_matrix_to_euler()` — Convert to pitch/yaw/roll in degrees

#### `authentication_service.py`
- `authenticate(username, password)` → `bool` — bcrypt `checkpw` with graceful error handling
- `hash_password(password)` → `str` — bcrypt hash helper

#### `settings_service.py`
- Wraps `SystemSettingRepository`
- `get(key)` → `str | None`
- `set(key, value, value_type)` → upsert

### `src/attendance_system/ui/`

#### `main_window.py`
- `MainWindow(QMainWindow)` — 3-view router via `QStackedWidget`
- Keyboard shortcuts: `Q` quits, others delegated to active view
- `_quit()` stops camera before closing

#### `constants.py`
- `FONT_TITLE` — 20pt Bold JetBrains Mono
- `FONT_STATUS` — 16pt Bold JetBrains Mono
- `FONT_BODY` — 14pt Normal JetBrains Mono

#### `camera_thread.py`
- `CameraThread(QThread)` — Attendance camera pipeline
- Signals: `frame_ready`, `recognition_result`, `camera_error`, `inference_warning`
- Frame skip: process every 3rd frame, display every frame
- Cooldown: 3s between re-recognitions of same user
- Bbox colors: gray (detecting), green (success), red (spoof), yellow (unknown)

#### `enrollment_camera_thread.py`
- `EnrollmentCameraThread(QThread)` — Enrollment camera pipeline
- Signals: `frame_ready`, `capture_progress`, `camera_error`, `enrollment_complete`, `inference_warning`
- Mirror flip: `cv2.flip(frame, 1)` for natural UX
- Pose sequence: 5 targets (front, left, right, up, down)
- Legacy fallback: landmark ratio when head-pose model unavailable

#### `user_mode_view.py`
- Two-panel: IDLE (subject/class input) → ACTIVE (camera + sidebar)
- Keyboard shortcuts: `S` start, `E` end, `Ctrl+L` admin login
- Reads thresholds from `system_settings` at session start
- Connects to `timezone_signals.timezone_changed` to re-render the attendance sidebar mid-session
- Clears the camera preview pixmap + resets placeholder text on both session start and session end (extracted to `_reset_camera_preview()` helper)

#### `admin_dashboard_view.py`
- Sidebar navigation with emoji icons
- Content area with 5 views (welcome, settings, users, enrollment, history)

#### `login_widget.py`
- Username/password form with Enter-key support
- Vietnamese labels + styling

#### `enrollment_widget.py`
- User dropdown (shows unregistered users only), camera feed, progress bar, guidance
- Intentionally bypasses liveness during enrollment (pose sequence is sufficient)

#### `settings_widget.py`
- Camera scanner (`_CameraScanThread` — probes indices 0–4 in background)
- AI thresholds: liveness + similarity spinboxes
- Display: timezone `QComboBox` (13 curated IANA choices; on save applies immediately via `set_timezone_config` + `timezone_signals.timezone_changed` signal)
- Attendance Freeze: `QSpinBox` (seconds, 0=disabled) + `QCheckBox` (sound enabled)
- Imports `format_tz_label` from `utils.time_utils`

#### `user_management_widget.py`
- QTableWidget with Add/Edit/Delete buttons
- Student ID is immutable after creation
- Delete is soft (deactivate) + removes face references

#### `attendance_history_widget.py`
- Split pane: session list (left) + records (right)
- Date range, class, subject filters
- Export to CSV/Excel per session
- Connects to `timezone_signals.timezone_changed` to re-run the search when the user switches timezone
- Export button uses a plain `QPushButton` + manual `QMenu.exec_()` (no `setStyleSheet` override, no custom triangle — click anywhere on the button opens the menu)

### `src/attendance_system/utils/`

#### `face_utils.py`
- `_crop_face(frame, bbox, scale=1.5)` — Centered crop with padding
- `_create_face_detector(model_path, input_size, score_threshold, nms_threshold)` — Creates YuNet `cv2.FaceDetectorYN`

#### `time_utils.py`
- `set_timezone_config(tz_name)` — Configure the local timezone. Falls back to UTC on invalid input. Emits `timezone_signals.timezone_changed` iff the effective timezone differs.
- `get_timezone_name()` → IANA name string
- `get_timezone_config()` → `zoneinfo.ZoneInfo` object
- `format_tz_label(name)` → IANA name with UTC offset (e.g. `"UTC (UTC+00:00)"`)
- `utc_now_iso()` → ISO 8601 UTC timestamp string
- `local_now_iso()` → ISO 8601 in configured local timezone
- `utc_to_local(iso_str)` / `local_to_utc(iso_str)` — display/storage conversions
- `timezone_signals` — module-level `QObject` singleton exposing `pyqtSignal(str) timezone_changed` for cross-widget timezone-change notifications
- `_TimezoneSignals` — private `QObject` class (module-internal) — wrapped by `timezone_signals`
- `_load_zoneinfo()` — lazy loader for `zoneinfo.ZoneInfo` (module-internal; safe-import on Python < 3.9)

## Test Structure

```
tests/
├── conftest.py       # database fixture (tmp_path SQLite, full schema)
├── unit/             # 10 files — fast, no camera/GUI
│   ├── test_ai_pipeline.py
│   ├── test_attendance_history_service.py
│   ├── test_attendance_service.py
│   ├── test_authentication.py
│   ├── test_enrollment_and_settings_unit.py
│   ├── test_head_pose.py
│   ├── test_recognition_event_repository.py
│   ├── test_storage_repositories.py
│   ├── test_time_utils.py          # set_timezone_config, signal emission, conversions, invalid-input fallbacks
│   └── test_user_mode_freeze.py    # Freeze delay + camera preview reset (exercised indirectly)
├── integration/      # 9 files — DB, storage, offline behavior
│   ├── test_attendance_audit.py
│   ├── test_attendance_history.py
│   ├── test_bootstrap_entry_point.py
│   ├── test_database_init.py
│   ├── test_head_pose_enrollment.py
│   ├── test_offline_behavior.py
│   ├── test_performance.py
│   ├── test_settings_and_enrollment_integration.py
│   └── test_storage_bootstrap.py
└── contract/         # Empty (future contract tests)
```
