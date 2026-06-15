# src/attendance_system/services/

## Responsibility

Business logic layer that encapsulates all domain operations. Acts as the intermediary between the UI (presentation) and repositories (data access). Services compose repository calls, enforce business rules, and run ONNX-based AI inference. No direct database access outside repositories.

## Key Services

### `preprocessing_configs.py` — Per-model config constants (plan 0007)

- **`LIVENESS_CONFIG`** — `scale=2.7, target_size=(128, 128), normalize=zero_one, use_clahe=False, input_color=rgb, resize_mode=letterbox`. Matches the MiniFASNet training pipeline.
- **`HEAD_POSE_CONFIG`** — `scale=1.5, target_size=(224, 224), normalize=imagenet, use_clahe=False, input_color=bgr, resize_mode=direct`. Matches the MobileNetV2 training pipeline.
- Adding a new model = one new `PreprocessingConfig` constant here.

### `face_preprocessor.py` — Composable preprocessing pipeline (plan 0007)

- **`FacePreprocessor`** — Stateless pipeline: `crop → color → optional CLAHE → resize (letterbox|direct) → normalize (zero_one|imagenet) → to_tensor (HWC→CHW float32)`. Composed by a frozen `PreprocessingConfig` (scale, target_size, normalize, use_clahe, input_color, resize_mode). No ONNX dependency, so each step is unit-testable in isolation.
- **`PreprocessingConfig`** — Frozen dataclass; per-model recipe.
- **Constants:** `Normalize.{ZERO_ONE, IMAGENET}`, `ResizeMode.{LETTERBOX, DIRECT}`, `InputColor.{RGB, BGR}`.
- `__call__(face_crop, bbox=None)` — When `bbox` is supplied, the crop step is applied first using `config.scale`. When `None`, the input is treated as already-cropped (backward-compat with existing callers).

### `pipeline_result.py` — Structured pipeline output

- **`PipelineResult`** — `@dataclass(slots=True)` with `result_type` discriminator string. Encapsulates all possible outputs from the `AIPipeline` orchestrator.
- **Attendance mode** (`run_attendance`): `result_type` is `"success"`, `"spoof"`, or `"unrecognized"`. Always sets `liveness_score`. `"success"` also sets `user_id`, `full_name`, `student_id`, `similarity`, `matched_pose_label`.
- **Enrollment mode** (`run_enrollment`): `result_type` is `"pose_only"`, `"capture_success"`, or `"capture_fail"`. Always sets `pitch`, `yaw`, `roll`. `"capture_success"` also sets `liveness_score` and `embedding`.

### `exceptions.py` — Error hierarchy

```
ONNXInferenceError              # base ONNX failure (input_shape, model_path)
├── PoseInferenceError          # head pose estimation failure
└── LivenessInferenceError      # liveness detection failure

SessionClosedError              # recording attendance in a closed session
```

- `ONNXInferenceError` carries optional `input_shape` and `model_path` context for logging.
- `SessionClosedError` is raised by `AttendanceService` when a write method is called on a closed session.

### `liveness_tracker.py` — Temporal smoothing (plan 0004)

- **`LivenessTracker`** — Frame-to-frame tracking of detected faces with exponential moving average (EMA) smoothing of liveness scores. Pure IoU tracking with EMA — no temporal decisions (those moved to `HybridLivenessDecider`).
- **Algorithm per frame:**
  1. Greedy IoU match each detection → existing track.
  2. Matched tracks: update bbox, apply EMA (`α=0.4`).
  3. Unmatched detections → create new tracks.
  4. Unmatched existing tracks → increment miss counter.
  5. Prune tracks with misses > `MAX_MISSES` (default 3).
- **EMA:** `α=0.4` — exponential moving average of liveness probability scores.
- **Hysteresis:** Removed in plan 0009. Temporal decisions moved to `HybridLivenessDecider` (5-frame majority voting, configurable threshold).
- **`TrackedFace`** — Internal dataclass (slots) holding bbox, ema_score, state, misses.
- **`compute_iou(bbox1, bbox2)`** — IoU in (x, y, w, h) format.
- Relocated from `core/liveness_tracker.py` (plan 0004). The `core/liveness_tracker.py` now re-exports all public names for backward compatibility.

### `ai_pipeline.py` — AI inference orchestration

- **`LivenessChecker`** — Wraps the quantized MiniFASNet ONNX model (`models/anti_spoof/best_model_quantized.onnx`). Preprocessing delegated to `FacePreprocessor(LIVENESS_CONFIG)` (letterbox-resize 128×128, [0,1] range, RGB). Runs ONNX inference and classifies real vs. spoof via logit-diff thresholding. Can be disabled entirely by passing `model_path=None` — all faces treated as real.
- **`FaceRecognizer`** — Wraps the SFace ONNX model (`models/face_recognition/face_recognition_sface_2021dec.onnx`) via OpenCV's `cv2.FaceRecognizerSF`. Extracts 128-dim float32 embeddings using `alignCrop` + `feature`. Identification uses cosine similarity against all cached face references from `CachingFaceReferenceRepository`. Resolution of matched user details via `UserRepository`.
- **`AIPipeline`** — Orchestrator that composes `LivenessChecker`, `FaceRecognizer`, `LivenessTracker`, and optionally `HeadPoseEstimator` as injected dependencies. Owns one `LivenessTracker` instance per pipeline instance (one tracker per worker thread).
  - `run_attendance(frame_bgr, frame_rgb, face_row, frame_counter)` → `PipelineResult` with `result_type` `"success"`, `"spoof"`, or `"unrecognized"`. Flow: crop face (scale=2.7) → liveness check → temporal smoothing (LivenessTracker) → if REAL: face recognition.
  - `run_enrollment(frame_bgr, face_row, frame_counter, do_capture)` → `PipelineResult` for enrollment. Flow: head-pose estimation (scale=1.5) → if do_capture: liveness check → embedding extraction.
  - `reset_tracker()` — Clear LivenessTracker state; called when starting a new session.
- **`LivenessResult` / `RecognitionResult`** — NamedTuple data carriers (still used by the individual checker/recognizer, but `AIPipeline` returns `PipelineResult`).

### `head_pose.py` — Head pose estimation

- **`HeadPoseEstimator`** — ONNX model that outputs a 3×3 rotation matrix from a 224×224 BGR face crop. Preprocessing delegated to `FacePreprocessor(HEAD_POSE_CONFIG)` (direct resize, ImageNet normalization, BGR). Converts rotation matrix to pitch/yaw/roll (degrees) via Euler angle decomposition.
- **`PoseAngles`** — NamedTuple `(pitch, yaw, roll)`.
- Raises `PoseInferenceError` on inference failure.

### `attendance_service.py` — Attendance session lifecycle

- **Session management**: `start_session()`, `end_session()`, `get_sessions()`, `get_session_details()`, `get_session_records()`.
- **Recognition event recording**: `record_success()`, `record_duplicate()`, `record_spoof_warning()`, `record_unrecognized()`. Each writes to both `recognition_events` and (where applicable) `attendance_records` tables. `record_duplicate` handles `sqlite3.IntegrityError` gracefully by fetching the existing record ID. All four methods validate session status and raise `SessionClosedError` on closed sessions.
- **Export**: `export_session_to_csv()` / `export_session_to_excel()` via optional `pandas` and `openpyxl`. Converts UTC timestamps to local timezone for human-readable output.
- **Lookups**: `get_unique_classes()`, `get_unique_subjects()` for filter dropdowns.

### `authentication_service.py` — Admin credentials

- `authenticate(username, password)` — bcrypt hash comparison. Returns `bool` only (no session tokens — offline desktop app). `hash_password()` helper used during admin creation/seeding.
- Defensive: early return `False` on empty input or `bcrypt` exceptions.

### `enrollment_service.py` — Face registration

- `save_face_references(user_id, pose_embeddings, model_name, vector_length)` — Delegates to `FaceReferenceRepository.save_enrollment()` which atomically deletes old face references, inserts 5 pose-specific rows, and updates `users.face_registered` in one transaction.
- Thin service kept as a seam for future pre/post hooks (audit log, broadcast events, etc.).
- Accepts either bare `FaceReferenceRepository` or `CachingFaceReferenceRepository` wrapper (production wires the caching wrapper for automatic cache invalidation).

### `settings_service.py` — System settings CRUD

- Thin wrapper over `SystemSettingRepository`: `get(key)` returns value or `None`; `set(key, value, value_type)` upserts.
- Separate concern from `attendance_system.core.config.SystemConfig`: this is the admin's runtime-mutable state (Admin UI writes), while `SystemConfig` holds immutable startup-resolved values (CLI > env > DB > default).

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
  Result returned (NamedTuple / PipelineResult / int / None)
        │
        ▼
  UI state update, QPixmap/QImage display
```

**Typical attendance flow** (in `CameraThread` / `user_mode_view.py`):

1. Camera frame captured → face detection (YuNet in camera thread).
2. `AIPipeline.run_attendance(frame_bgr, frame_rgb, face_row, frame_counter)`:
   a. Crop face for liveness (scale=2.7).
   b. `LivenessChecker.check(face_crop, threshold)` → liveness score.
   c. `LivenessTracker.update([bbox], [score])` → EMA-smoothed score (no state decision).
   d. If REAL: `FaceRecognizer.identify(frame_bgr, face_row, threshold)` → embedding extraction + cosine similarity vs. DB references.
   e. Return `PipelineResult` with `result_type` → `"success"`, `"spoof"`, or `"unrecognized"`.
3. `AttendanceService.record_success(...)` → writes recognition event + attendance record.
4. UI emits signal to update overlay/lists.

**Typical enrollment flow**:

1. `EnrollmentCameraThread` → face detection per frame.
2. `AIPipeline.run_enrollment(frame_bgr, face_row, frame_counter, do_capture)`:
   a. `HeadPoseEstimator.estimate(face_crop)` → pitch/yaw/roll.
   b. If `do_capture`: `LivenessChecker.check(...)` → anti-spoof, `FaceRecognizer.get_embedding(...)` → embedding.
   c. Return `PipelineResult` with `result_type` → `"pose_only"`, `"capture_success"`, or `"capture_fail"`.
3. Quality checks pass → `EnrollmentService.save_face_references()` → upserts embeddings + marks user registered.

## Integration

### Consumed by (`attendance_system.ui`)

| UI component | Services used |
|---|---|
| `main_window.py` | `FaceRecognizer`, `LivenessChecker`, `HeadPoseEstimator`, `AttendanceService`, `AuthenticationService`, `SettingsService` |
| `camera_thread.py` | `AIPipeline`, `FaceRecognizer`, `LivenessChecker`, `LivenessInferenceError` |
| `user_mode_view.py` | `FaceRecognizer`, `LivenessChecker`, `AttendanceService`, `SettingsService`, `SessionClosedError` |
| `enrollment_widget.py` | `EnrollmentService`, `LivenessChecker`, (optionally) `FaceRecognizer`, `HeadPoseEstimator`, `SettingsService` |
| `enrollment_camera_thread.py` | `AIPipeline`, `FaceRecognizer`, `LivenessChecker`, `HeadPoseEstimator`, `LivenessInferenceError` |
| `enrollment_ai_worker.py` | `AIPipeline`, `LivenessInferenceError`, `PoseInferenceError` |
| `admin_dashboard_view.py` | `SettingsService`, `FaceRecognizer`, `LivenessChecker`, `HeadPoseEstimator` |
| `attendance_history_widget.py` | `AttendanceService` |
| `settings_widget.py` | `SettingsService` |
| `login_widget.py` | `AuthenticationService` |

### Consumes (`attendance_system.repositories`)

| Service | Repository |
|---|---|
| `FaceRecognizer` | `CachingFaceReferenceRepository`, `FaceReferenceRepository`, `UserRepository` |
| `AttendanceService` | `SessionRepository`, `AttendanceRepository`, `RecognitionEventRepository`, `UserRepository` |
| `AuthenticationService` | `AdminRepository` |
| `EnrollmentService` | `CachingFaceReferenceRepository`, `FaceReferenceRepository`, `UserRepository` |
| `SettingsService` | `SystemSettingRepository` |

### External dependencies

- **`onnxruntime`** — Used directly by `LivenessChecker` and `HeadPoseEstimator` for model inference.
- **`cv2.FaceRecognizerSF`** (OpenCV) — Used by `FaceRecognizer` for embedding extraction (alignCrop + feature).
- **`bcrypt`** — Used by `AuthenticationService` for password hashing/verification.
- **`pandas` / `openpyxl`** — Optional soft dependencies for export; raises `RuntimeError` with install hint if missing.
- **`cryptography.fernet`** — Optional; used by `FaceReferenceRepository` (not a service directly) for embedding-at-rest encryption.
