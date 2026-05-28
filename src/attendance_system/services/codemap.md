# src/attendance_system/services/

## Responsibility

Business logic layer that encapsulates all domain operations. Acts as the intermediary between the UI (presentation) and repositories (data access). Services compose repository calls, enforce business rules, and run ONNX-based AI inference. No direct database access outside repositories.

## Key Services

### `ai_pipeline.py` — AI inference orchestration

- **`LivenessChecker`** — Wraps the quantized MiniFASNet ONNX model (`models/anti_spoof/best_model_quantized.onnx`). Performs letterbox-resize preprocessing (128×128, [0,1] range), runs ONNX inference, and classifies real vs. spoof via logit-diff thresholding. Can be disabled entirely by passing `model_path=None` (or setting `FACE_ANTISPOOF_ENABLED=false`) — all faces treated as real.
- **`FaceRecognizer`** — Wraps the SFace ONNX model (`models/face_recognition/face_recognition_sface_2021dec.onnx`) via OpenCV's `cv2.FaceRecognizerSF`. Extracts 128-dim float32 embeddings using `alignCrop` + `feature`. Identification uses cosine similarity against all cached face references from `FaceReferenceRepository.get_all()`. Resolution of matched user details via `UserRepository`.
- **`LivenessResult` / `RecognitionResult`** — NamedTuple data carriers across threads.

### `attendance_service.py` — Attendance session lifecycle

- **Session management**: `start_session()`, `end_session()`, `get_sessions()`, `get_session_details()`.
- **Recognition event recording**: `record_success()`, `record_duplicate()`, `record_spoof_warning()`, `record_unrecognized()`. Each writes to both `recognition_events` and (where applicable) `attendance_records` tables. `record_duplicate` handles `sqlite3.IntegrityError` gracefully by fetching the existing record ID.
- **Export**: `export_session_to_csv()` / `export_session_to_excel()` via optional `pandas` and `openpyxl`. Converts UTC timestamps to local timezone for human-readable output.
- **Lookups**: `get_unique_classes()`, `get_unique_subjects()` for filter dropdowns.
- Internally validates session and user existence before recording.

### `authentication_service.py` — Admin credentials

- `authenticate(username, password)` — bcrypt hash comparison. Returns `bool` only (no session tokens — offline desktop app). `hash_password()` helper used during admin creation/seeding.
- Defensive: early return `False` on empty input or `bcrypt` exceptions.

### `enrollment_service.py` — Face registration

- `save_face_reference()` — Upserts a face embedding into `face_references` (via `FaceReferenceRepository.upsert()`), then updates the user record's `face_registered` flag to `True`.
- Coarse-grained: one call handles both DB writes.

### `exceptions.py` — ONNX inference error hierarchy

```
ONNXInferenceError
├── PoseInferenceError      # head pose estimation failure
└── LivenessInferenceError  # liveness detection failure
```

Each carries optional `input_shape` and `model_path` context for logging. Used in `ai_pipeline.py` and `head_pose.py`.

### `head_pose.py` — Head pose estimation

- **`HeadPoseEstimator`** — ONNX model that outputs a 3×3 rotation matrix from a 224×224 RGB face crop. Preprocessing uses ImageNet normalization (mean/std). Converts rotation matrix to pitch/yaw/roll (degrees) via Euler angle decomposition.
- Raises `PoseInferenceError` on inference failure.

### `settings_service.py` — System settings CRUD

- Thin wrapper over `SystemSettingRepository`: `get(key)` returns value or `None`; `set(key, value, value_type)` upserts.

## Data Flow

```
User action (click, camera frame)
        │
        ▼
  UI Widget (Qt signal / slot)
        │
        ▼
  Service  ──► Repository  ──► Database (SQLite via sqlite3.Row)
        │                           │
        │                           ▼
        │                     onnxruntime / OpenCV  (ai_pipeline, head_pose)
        │
        ▼
  Result returned (NamedTuple / int / None)
        │
        ▼
  UI state update, QPixmap/QImage display
```

**Typical attendance flow** (in `CameraThread` / `user_mode_view.py`):

1. Camera frame captured → face detection (YuNet in camera thread).
2. `LivenessChecker.check(face_rgb)` → anti-spoof inference.
3. `FaceRecognizer.identify(frame, face_row)` → embedding extraction + cosine similarity vs. DB references.
4. `AttendanceService.record_success(...)` → writes recognition event + attendance record.
5. UI emits signal to update overlay/lists.

**Typical enrollment flow**:

1. `EnrollmentCameraThread` → face detection + liveness + head pose validation per frame.
2. Quality checks pass → `EnrollmentService.save_face_reference()` → upserts embedding + marks user registered.

## Integration

### Consumed by (`attendance_system.ui`)

| UI component | Services used |
|---|---|
| `main_window.py` | `FaceRecognizer`, `LivenessChecker`, `HeadPoseEstimator`, `AttendanceService`, `AuthenticationService`, `SettingsService` |
| `camera_thread.py` | `FaceRecognizer`, `LivenessChecker` |
| `user_mode_view.py` | `FaceRecognizer`, `LivenessChecker`, `AttendanceService`, `SettingsService` |
| `enrollment_widget.py` | `EnrollmentService`, `LivenessChecker`, (optionally) `FaceRecognizer`, `HeadPoseEstimator`, `SettingsService` |
| `enrollment_camera_thread.py` | `FaceRecognizer`, `LivenessChecker`, `HeadPoseEstimator` |
| `enrollment_ai_worker.py` | `FaceRecognizer`, `LivenessChecker`, `HeadPoseEstimator` |
| `admin_dashboard_view.py` | `SettingsService`, `FaceRecognizer`, `LivenessChecker`, `HeadPoseEstimator` |
| `attendance_history_widget.py` | `AttendanceService` |
| `settings_widget.py` | `SettingsService` |
| `login_widget.py` | `AuthenticationService` |

### Consumes (`attendance_system.repositories`)

| Service | Repository |
|---|---|
| `FaceRecognizer` | `FaceReferenceRepository`, `UserRepository` |
| `AttendanceService` | `SessionRepository`, `AttendanceRepository`, `RecognitionEventRepository`, `UserRepository` |
| `AuthenticationService` | `AdminRepository` |
| `EnrollmentService` | `FaceReferenceRepository`, `UserRepository` |
| `SettingsService` | `SystemSettingRepository` |

### External dependencies

- **`onnxruntime`** — Used directly by `LivenessChecker` and `HeadPoseEstimator` for model inference.
- **`cv2.FaceRecognizerSF`** (OpenCV) — Used by `FaceRecognizer` for embedding extraction (alignCrop + feature).
- **`bcrypt`** — Used by `AuthenticationService` for password hashing/verification.
- **`pandas` / `openpyxl`** — Optional soft dependencies for export; raises `RuntimeError` with install hint if missing.
- **`cryptography.fernet`** — Optional; used by `FaceReferenceRepository` (not a service directly) for embedding-at-rest encryption.
