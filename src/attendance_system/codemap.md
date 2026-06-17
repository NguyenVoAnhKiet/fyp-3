# `src/attendance_system/` — Application Root Package

## Responsibility

Root package of the face-attendance desktop application. Owns the full
attendance pipeline — face detection, anti-spoofing liveness checking,
SFace recognition, multi-pose enrollment, session management, and the
PyQt5 GUI. All business logic, persistence, and UI live under this tree;
the only entry point (`src/main.py`) sits one level above and wires
everything together.

The package follows a layered architecture with strict dependency direction:
`core/` ← `models/` ← `repositories/` ← `services/` ← `ui/`, with `utils/`
available to all layers as a stateless helper library.

## Subdirectory Map

| Sub-package | Responsibility | Detailed Map |
|---|---|---|
| `core/` | Configuration resolution (CLI > env > DB > default), SQLite/WAL connection management, schema DDL/DML + migrations, `attendance-storage-init` CLI bootstrap, face-image disk-storage init. Lowest-level module — everything depends on it. | [View Map](core/codemap.md) |
| `models/` | Pure `@dataclass(slots=True)` entities (`UserAccount`, `FaceReference`, `AttendanceSession`, `AttendanceRecord`, `RecognitionEvent`, `SystemSetting`, `AdminCredential`) mirroring database rows. No business logic, no ORM. | [View Map](models/codemap.md) |
| `repositories/` | CRUD data-access layer parameterizing raw SQL behind typed methods. Each repository owns one database table. Caching wrapper (`CachingFaceReferenceRepository`) for face-reference reads with automatic invalidation on writes. Enforces `ON DELETE SET NULL` semantics. | [View Map](repositories/codemap.md) |
| `services/` | Business-logic layer — ONNX-based AI pipeline orchestration (liveness checking via MiniFASNet, SFace recognition, head-pose estimation via MobileNetV2, multi-frame HybridLivenessDecider for temporal liveness voting), attendance session lifecycle, face enrollment, bcrypt authentication, and settings CRUD. Consumes repositories; consumed by UI. | [View Map](services/codemap.md) |
| `ui/` | PyQt5 widgets, windows, and QThread workers — main window, attendance check-in view, admin dashboard, enrollment UI, camera capture threads (attendance + enrollment), and AI inference worker threads. Sole user-facing surface; no business logic. | [View Map](ui/codemap.md) |
| `utils/` | Stateless helper functions — face crop/detection (`_crop_face`, `_create_face_detector`) and timezone-aware datetime formatting (`utc_now_iso`, `utc_to_local`, `local_to_utc`, timezone-change signal bus). Available to all layers. | [View Map](utils/codemap.md) |

## Architecture & Dependency Flow

```
src/main.py  (entry point — wires everything)
     │
     ▼
attendance_system/
     │
     ├── core/          (config, Database, schema, bootstrap CLI)
     │   │
     │   ├──► models/  (entity dataclasses — consumed by repos)
     │   │
     │   ├──► repositories/  (per-entity CRUD, cache wrapper)
     │   │   │
     │   │   └──► services/  (AI pipeline, attendance, auth, enrollment, settings)
     │   │       │
     │   │       └──► ui/  (PyQt5 widgets, camera workers, AI workers)
     │   │
     │   └──► utils/   (face helpers, timezone — consumed by all layers)
     │
     ▼
  SQLite (WAL) + Disk (face images) + ONNX Runtime + OpenCV
```

**Strict dependency rule:** `core/` knows nothing above it. `models/` depends on nothing. `repositories/` depends on `core/` + `models/`. `services/` depends on `repositories/` + `core/`. `ui/` depends on `services/` + `core/` + `utils/`. `utils/` depends on nothing within the package.

## Key Integration Points

### Startup Sequence

1. **`attendance-app` CLI** → `src/main.py:main()`
2. `load_dotenv()` loads `.env` into environment
3. `SettingsResolver.resolve()` builds frozen `SystemConfig` (CLI > env > DB > default)
4. `set_timezone_config(config.timezone)` initialises `time_utils._tz`
5. `initialize_storage()` creates/upgrades SQLite schema (WAL mode, foreign keys)
6. `QApplication` created, ONNX model files validated
7. Repositories and services instantiated with shared `Database` instance
8. `seed_db_from_defaults()` writes `defaults.py`→DB if keys are unset (idempotent)
9. `MainWindow` launched with all dependencies injected → Qt event loop

### Data Flow — Attendance Check-In

```
Camera capture (CameraThread, every 30ms)
  → YuNet face detection (CameraThreadBase._detect_faces)
  → AIWorker queue (maxsize=1 backpressure)
  → AIPipeline.run_attendance()
      ├── FacePreprocessor(LIVENESS_CONFIG) — crop scale 2.7, 128×128
      ├── LivenessChecker — MiniFASNet ONNX → sigmoid probability [0, 1]
      ├── LivenessTracker — EMA smoothing + IoU tracking (pure tracking;
      │                      no temporal decisions made here)
      └── Decision (two paths selectable via hybrid_liveness_enabled):
          ├── Hybrid path (enabled):
          │     ├── Periodic recognition every N AI-frames
          │     │   (recognition_interval, default 5)
          │     └── HybridLivenessDecider — majority voting over
          │         circular buffer of FrameResult entries:
          │           ├── Recognition match → additive probability boost
          │           ├── >= ceil(window/2)+1 votes → REAL
          │           └── Buffer resets when face is lost
          └── Legacy path (disabled):
                ├── Simple EMA-score threshold (liveness_threshold)
                └── Recognition every frame
  → PipelineResult → CameraThread emits recognition_result signal
  → UserModeView handles result:
      ├── Success → AttendanceService.record_success()
      │     → SessionRepository (validate open)
      │     → AttendanceRepository (INSERT or IntegrityError→SELECT)
      │     → RecognitionEventRepository (INSERT)
      ├── Spoof  → AttendanceService.record_spoof_warning()
      └── Unrecognized → AttendanceService.record_unrecognized()
  → UI overlay update + freeze timer + stats increment
  → Display frame with bounding box annotation
```

### Data Flow — Enrollment

```
EnrollmentCameraThread capture (mirrored via cv2.flip)
  → YuNet face detection
  → EnrollmentAIWorker queue
  → AIPipeline.run_enrollment()
      ├── FacePreprocessor(HEAD_POSE_CONFIG) — crop scale 1.5, 224×224
      ├── HeadPoseEstimator — MobileNetV2 ONNX → pitch/yaw/roll
      └── If do_capture:
            ├── LivenessChecker (bypassed: model_path=None)
            └── FaceRecognizer.get_embedding() → 128-dim vector
  → PipelineResult → pose_estimated/capture_complete signals
  → EnrollmentWidget guides 5-pose sequence (center, left, right, up, down)
  → Complete → EnrollmentService.save_face_references()
      → FaceReferenceRepository.save_enrollment() (DELETE + 5 INSERT + UPDATE)
      → CachingFaceReferenceRepository.invalidate()
```

### Data Flow — Admin Settings

```
SettingsWidget user input
  → SettingsService.set(key, value, value_type)
      → SystemSettingRepository.upsert()
  → Timezone change:
      → set_timezone_config(new_name) in time_utils
      → emits timezone_signals.timezone_changed
      → UserModeView + AttendanceHistoryWidget re-render
  → Camera index change:
      → _CameraScanThread probes cv2.VideoCapture with CAP_DSHOW
```

### Cross-Thread Communication

```
Main Thread (GUI)                    Worker Thread(s)
─────────────────                    ────────────────
UserModeView
  └─ CameraThread (CameraThreadBase)
       ├── frame capture (cv2.VideoCapture)
       ├── YuNet face detection
       ├── draw bounding boxes
       ├── emit display QImage (.copy()) ──► UserModeView._update_camera_frame()
       └── AIWorker (AIWorkerBase)
              ├── LivenessChecker (MiniFASNet ONNX)
              ├── FaceRecognizer (SFace ONNX)
              ├── LivenessTracker (EMA + IoU tracking)
              ├── HybridLivenessDecider (majority voting, when enabled)
              └── emit recognition_result ──► UserModeView handler

EnrollmentWidget
  └─ EnrollmentCameraThread
       ├── mirrored frame capture
       ├── face detection
       └── EnrollmentAIWorker (AIWorkerBase)
             ├── HeadPoseEstimator (MobileNetV2 ONNX)
             ├── LivenessChecker (bypassed)
             └── FaceRecognizer embedding
```

### Config Resolution Order

Each tunable follows the same chain: **CLI arg > environment variable > DB setting > default constant** (DB-seedable keys are the exception: DB > `defaults.py`, no env override). `SettingsResolver` in `core/config.py` encapsulates this logic with per-type resolvers (`_resolve_path`, `_resolve_int`, `_resolve_float`, `_resolve_bool`, `_resolve_timezone`). `seed_db_from_defaults()` only writes if the DB key is unset, so Admin UI changes survive restarts.

**DB-seedable settings (9 keys):** timezone, liveness_threshold, similarity_threshold, attendance_freeze_seconds, attendance_freeze_sound_enabled, hybrid_voting_window, hybrid_boost_amount, hybrid_liveness_enabled, recognition_interval. All follow the DB > `defaults.py` resolution order with no env/CLI override — the Admin UI is the single source of truth after first run.

### Model File Layout

| Model | File | Consumed By |
|---|---|---|
| YuNet face detector | `models/face_detection/face_detection_yunet_2023mar.onnx` | `CameraThreadBase` (ui/) |
| SFace recognizer | `models/face_recognition/face_recognition_sface_2021dec.onnx` | `FaceRecognizer` (services/) |
| MiniFASNet anti-spoof | `models/anti_spoof/best_model_quantized.onnx` | `LivenessChecker` (services/) |
| MobileNetV2 head-pose | `models/head_pose/head_pose_mobilenetv2_quantized.onnx` | `HeadPoseEstimator` (services/) |

### Key Design Decisions

- **WAL mode** — Enables concurrent reads while camera threads write recognition events.
- **`check_same_thread=False`** — Required because PyQt camera workers call DB methods from non-main threads.
- **Frozen `SystemConfig`** — Immutable after construction; single injection point for all tunables.
- **Repository pattern** — Each table has a dedicated repository; `BaseRepository` provides shared SQL primitives with query/parameter validation.
- **Caching face references** — `CachingFaceReferenceRepository` wraps `FaceReferenceRepository`; cache auto-invalidates on every write method.
- **ONNX circuit-breaker** — `AIWorkerBase` sets `_MAX_CONSECUTIVE_FAILURES = 30`; one broken model kills both attendance and enrollment (ADR-0001 shared counter).
- **Preprocessing configs** — Per-model `PreprocessingConfig` constants (`LIVENESS_CONFIG`, `HEAD_POSE_CONFIG`) in `services/preprocessing_configs.py`; adding a new model = one new config constant.
- **Liveness bypass during enrollment** — `LivenessChecker(model_path=None)` always passes; multi-pose capture provides implicit anti-spoofing.
- **Idempotent defaults→DB seeding** — `seed_db_from_defaults()` only writes unset DB keys, preserving Admin UI overrides across restarts. All defaults come from `defaults.py`.
- **`database.session()` context manager** — Auto-commit/rollback/close prevents leaked connections.
- **Timezone-change signal bus** — `time_utils.timezone_signals` is a module-level `QObject` singleton; UI widgets re-render in real-time on timezone switch.
- **`onnxruntime` before `PyQt5`** — Windows DLL-ordering requirement enforced at `src/main.py` and `tests/conftest.py`.
- **HybridLivenessDecider replaces hysteresis** — The old hysteresis-based approach (T_HIGH/T_LOW thresholds) has been replaced by `HybridLivenessDecider`, a multi-frame majority-voting decider using a circular buffer of `FrameResult` entries. The decider provides a single temporal authority for liveness decisions, with voting ratio and configurable window/boost parameters — all seeded from `defaults.py` and tunable via Admin UI.
- **Two-path `run_attendance`** — `AIPipeline.run_attendance()` supports two code paths controlled by `hybrid_liveness_enabled`: the **hybrid path** uses `HybridLivenessDecider` majority voting with periodic recognition (every N AI-frames via `recognition_interval`); the **legacy path** falls back to simple EMA-score threshold with frame-by-frame recognition. This preserves backward compatibility while enabling the new voting-based approach.
- **Recognition interval pattern** — In hybrid mode, recognition runs every `recognition_interval` AI-frames (not camera frames). With `_AI_FRAME_SKIP=3` and default `recognition_interval=5`, recognition fires ~every 15 camera frames ≈ 2 Hz at 30 fps. Identity-match provides an additive probability boost (`hybrid_boost_amount`) to the liveness vote, clamped to [0, 1.0].

## File List

```
__init__.py
core/
models/
repositories/
services/
ui/
utils/
```

Each subdirectory contains its own detailed `codemap.md` with module-level documentation, key files, and integration tables linked above.
