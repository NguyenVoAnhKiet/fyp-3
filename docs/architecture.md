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
2. **Phase 2: Configuration** — Resolve paths (CLI > `.env` > defaults)
3. **Phase 3: Bootstrap** — `initialize_storage()` creates schema + seeds admin
4. **Phase 4: Validate models** — Check ONNX files exist; graceful fallback for head-pose
5. **Phase 5: Wire services** — Build `FaceRecognizer`, `LivenessChecker`, `HeadPoseEstimator`, `Database`, all service classes
6. **Phase 6: Launch UI** — `MainWindow` with `QStackedWidget` routing

```
main()
├── load_dotenv()
├── build_parser().parse_args()
├── initialize_storage()
├── QApplication()
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
- `SettingsWidget` — camera scan thread, liveness/similarity spinboxes

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

Priority: **CLI args > `.env` vars > code defaults**

```python
_resolve_path(cli_value, env_key, default)  # Path
_resolve_camera_index(cli_value)            # int
_resolve_enabled(env_key, default)          # bool
```

Thresholds are seeded from `.env` into `system_settings` on first run only — subsequent changes go through the Settings UI.

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| `check_same_thread=False` | Required for PyQt5 camera thread accessing the same DB |
| `onnxruntime` imported before `PyQt5` | Avoids native DLL conflicts on Windows |
| WAL mode + synchronous=NORMAL | Read concurrency during camera threads writes |
| Embedding encryption (Fernet) | Optional, privacy-by-design; lazy import `cryptography` |
| Multi-pose enrollment bypasses liveness | Pose sequence provides implicit anti-spoofing |
| Enrollment frame mirrored horizontally | Mirror-like UX for natural head turns |
