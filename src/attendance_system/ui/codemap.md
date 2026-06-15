# `ui/` — Presentation Layer

**Responsibility:** All PyQt5 UI widgets, camera capture QThread workers, and AI-inference worker threads. This package is the sole user-facing surface of the application. It does not contain business logic — it consumes `services/` and `repositories/`.

---

## Key Files

### Camera & Worker Threads

| File | Role |
|---|---|
| `camera_worker_base.py` | **Base classes** — `CameraThreadBase(QThread)` (camera init, `_retry_read()` exponential backoff, `pause()`/`resume()`, `_detect_faces()` via YuNet, `_draw_bboxes()`, `_annotate_frame()` with QPainter, `_emit_display_frame()`) and `AIWorkerBase(QThread)` (queue+sentinel with maxsize=1 backpressure, `submit_task()` with auto `.copy()` on numpy arrays, `is_busy()`, circuit-breaker with `_MAX_CONSECUTIVE_FAILURES = 30`, `stop()` with drain+wait). Both define abstract `_process_frame()` for subclass override. |
| `camera_thread.py` | **Attendance camera** — `CameraThread(CameraThreadBase)` captures webcam frames, runs YuNet face detection, delegates liveness + recognition to `AIWorker(AIWorkerBase)` (inner QThread, uses `_COOLDOWN_SECONDS = 3.0` per-user cooldown, emits `recognition_result(result_type, user_id, full_name, liveness_score, similarity_score, matched_pose_label)` via arity-6 pyqtSignal). No frame mirroring. |
| `enrollment_camera_thread.py` | **Enrollment camera** — `EnrollmentCameraThread(CameraThreadBase)` captures webcam frames, **flips horizontally** (`cv2.flip(frame, 1)`), guides user through a 5-pose sequence (center, left, right, up, down) with head-pose estimation. Delegates async AI work to `EnrollmentAIWorker`. Full `run()` override with custom rendering pipeline (`_draw_status()`, `_emit_frame()`). |
| `enrollment_ai_worker.py` | **Enrollment AI worker** — `EnrollmentAIWorker(AIWorkerBase)` background QThread that runs head-pose estimation, anti-spoofing (liveness), and face embedding extraction for enrollment. `_inference_error_types()` returns both `PoseInferenceError` and `LivenessInferenceError`. Queue size 1 for backpressure. Emits `pose_estimated(pitch, yaw, roll)` and `capture_complete(success, embedding, liveness_score)`. |

### Widgets

| File | Role |
|---|---|
| `main_window.py` | Root `QMainWindow`. Houses a `QStackedWidget` routing between: `UserModeView` (index 0), `LoginWidget` (index 1), `AdminDashboardView` (index 2). Wires navigation signals; handles global quit (Q key) and `stop_camera` on close. Status bar shows camera index, DB path, and session state. Receives `SystemConfig` + all service dependencies and propagates them to child views. |
| `user_mode_view.py` | IDLE/ACTIVE dual-state widget. IDLE: subject + class input form with admin login shortcut. ACTIVE: camera feed, stats grid (success/spoof/unrecognized/time), attendance sidebar list, end-session button. Creates and controls `CameraThread`, handles its `recognition_result` signal (arity 6). **Freeze overlay** — after first recognition, pauses camera and shows success overlay for configurable seconds with optional sound cue. Connects to `timezone_signals.timezone_changed` to re-render the sidebar mid-session. Clears stale camera pixmap and resets placeholder text on session start AND end (single helper `_reset_camera_preview()`). |
| `login_widget.py` | Admin login card with username/password inputs. Emits `login_requested(username, password)` or `cancel_requested()`. No direct DB access — the parent `MainWindow` authenticates via `AuthenticationService`. |
| `admin_dashboard_view.py` | Dashboard shell with dark sidebar nav + content `QStackedWidget`. Contains sub-pages: welcome/overview (stat cards + recent sessions table), Settings, User Management, Enrollment, Attendance History. Emits `logout_requested`. Receives `face_repo` parameter and passes it to `EnrollmentWidget` and `UserManagementWidget`. |
| `enrollment_widget.py` | Face enrollment UI (UC-08). User dropdown with refresh, camera feed, 5-step progress circles (connected by lines), pose guidance icon (120×120 custom-painted face indicator), progress bar, fade-in notification. Creates/manages `EnrollmentCameraThread`. **Liveness bypassed during enrollment** — creates a `LivenessChecker(model_path=None)` that always passes, since multi-pose capture provides implicit anti-spoofing. Saves face reference via `EnrollmentService`. |
| `settings_widget.py` | Form for camera index (background-thread probe via `_CameraScanThread` using `cv2.CAP_DSHOW`), AI thresholds (liveness, similarity via `QDoubleSpinBox`), timezone (`QComboBox` of 13 curated IANA choices, applies immediately via `set_timezone_config` + signal emission), and attendance-freeze UX (freeze-seconds `QSpinBox` + freeze-sound `QCheckBox`). Persists via `SettingsService`. Imports `format_tz_label` and `set_timezone_config` from `utils.time_utils`. |
| `user_management_widget.py` | CRUD table for users (add via `UserDialog` with auto-generated `STU{N}` student ID, edit with dialog, delete with soft-delete). Uses `UserRepository` + `FaceReferenceRepository`. Inline search/filter by student ID or full name. Receives optional `face_repo` parameter so user-delete invalidates the cache in production. |
| `attendance_history_widget.py` | Session browser with date-range, class, subject filters. Split view: session list (left) → attendance records (right). Export to Excel (.xlsx) or CSV via `AttendanceService` — uses a plain `QPushButton` + manual `QMenu.exec_()` (no `setStyleSheet` override, no custom triangle; clicking anywhere on the button opens the menu). Connects to `timezone_signals.timezone_changed` to re-run the search on timezone change. |
| `constants.py` | Re-exports all style constants from `styles.py` for convenience. Also defines `FONT_TITLE` (= `FONT_H1`) and `FONT_STATUS` (= `FONT_H2`). |
| `styles.py` | Color palette (accents, backgrounds, borders, status colors), font helpers (`_make_font`), named font sizes, and `GLOBAL_QSS` (full Qt stylesheet with push buttons, inputs, tables, lists, group boxes, progress bars, scrollbars, splitter, status bar, etc.). |

---

## Camera Thread Gotchas

1. **`QImage.copy()` before cross-thread emission** — Both `CameraThreadBase._emit_display_frame()` and `EnrollmentCameraThread._emit_frame()` call `.copy()` on the `QImage` before emitting via `pyqtSignal(QImage)`. Without this, Qt's implicit sharing would reference released buffer memory, causing garbage frames or crashes.

2. **`import cv2.data`** — `camera_thread.py` explicitly imports `cv2.data` (`import cv2.data`). This is required because OpenCV's Python bindings do not always expose the `cv2.data` submodule automatically. The enrollment camera thread does not need it because it does not use `cv2.data`.

3. **`onnxruntime` before `PyQt5`** — Per project-wide rule (see `src/main.py` and `tests/conftest.py`), `import onnxruntime` must precede any `PyQt5` import on Windows to avoid DLL-load-order crashes. This is handled at the application entry point, not in individual UI modules.

4. **Frame buffer ownership in AI workers** — Both `AIWorkerBase.submit_task()` and `EnrollmentAIWorker.submit_task()` call `.copy()` on numpy arrays before pushing to the internal queue. This prevents the worker from reading a frame that has already been overwritten by the camera loop.

5. **Frame flip difference** — `EnrollmentCameraThread` mirrors the frame horizontally (`cv2.flip(frame, 1)`) so the user sees a natural mirror reflection. `CameraThread` does **not** flip — the attendance view shows the raw camera feed.

6. **Exponential backoff on read failures** — `CameraThreadBase._retry_read()` provides 3 attempts at 1s/2s/4s delays, recreating the `cv2.VideoCapture` each time. Used by both `CameraThread` and `EnrollmentCameraThread` via inheritance.

7. **Backpressure** — Both AI workers use a `queue.Queue(maxsize=1)` to submit frames. If the queue is full the frame is dropped (non-blocking). This prevents unbounded memory growth when AI inference is slower than the camera framerate.

8. **Circuit-breaker threshold** — `_MAX_CONSECUTIVE_FAILURES = 30` is defined once in `AIWorkerBase`. One broken model kills both attendance and enrollment (shared counter, ADR-0001). Override `_inference_error_types()` in subclass to specify caught exceptions — `AIWorker` catches `LivenessInferenceError`; `EnrollmentAIWorker` catches both `PoseInferenceError` and `LivenessInferenceError`.

9. **`recognition_result` signal arity** — `CameraThread.recognition_result` and the inner `AIWorker.recognition_result` are 6-argument signals: `(result_type: str, user_id: int, full_name: str, liveness_score: float, similarity_score: float | None, matched_pose_label: str)`. This carries the matched pose label from the enrollment data so the sidebar can display which pose angle was matched.

10. **Liveness bypass during enrollment** — `EnrollmentWidget._start_enrollment()` creates a `LivenessChecker(model_path=None)` that always returns `is_real=True`. The multi-pose capture sequence (center/left/right/up/down) provides implicit anti-spoofing — a static photo cannot complete the required head rotations. Additionally, the enrollment crop scale (2.7) differs from MiniFASNet's expected input, causing false rejects on angled faces.

---

## Threading Model

```
Main Thread (GUI)              Worker Thread(s)
─────────────────              ────────────────
UserModeView
  └─ CameraThread(CameraThreadBase) ──┐
       ├─ frame capture        │  AIWorker(AIWorkerBase) (QThread)
       ├─ face detection       │    ├─ anti-spoofing (MiniFASNet ONNX)
       ├─ draw bboxes          │    └─ recognition (SFace ONNX)
       └─ emit QImage ────────→ UserModeView._update_camera_frame()

EnrollmentWidget
  └─ EnrollmentCameraThread(CameraThreadBase) ──┐
       ├─ frame capture        │  EnrollmentAIWorker(AIWorkerBase) (QThread)
       ├─ flip (mirror)        │    ├─ head-pose estimation
       ├─ face detection       │    ├─ anti-spoofing
       └─ emit QImage ────────→ EnrollmentWidget.update_frame()
       │                       │    └─ embedding extraction
       └─ _on_pose_estimated   └─ signals → EnrollmentCameraThread callbacks
       └─ _on_capture_complete

SettingsWidget
  └─ _CameraScanThread ──────── probes camera indices (cv2.VideoCapture + CAP_DSHOW)
```

Key rules:
- Workers are created in `__init__`, started in `run()` (per project convention).
- AI workers use a `queue.Queue(maxsize=1)` with sentinel-based shutdown (managed by `AIWorkerBase`).
- On stop: drain queue, push sentinel, disconnect signals, `wait(3000)` (handled by `AIWorkerBase.stop()`).
- Camera thread `stop()` calls `_cleanup_worker()` to disconnect and stop the AI worker, then waits on itself.
- `CameraThread` and `EnrollmentCameraThread` both handle circuit-breaker errors via `_on_ai_worker_camera_error()` which stops the camera loop.

---

## Integration Points

| Layer | Consumed By |
|---|---|
| `services.ai_pipeline` (`AIPipeline`, `FaceRecognizer`, `LivenessChecker`) | `CameraThread`, `AIWorker`, `EnrollmentCameraThread`, `EnrollmentAIWorker`, `UserModeView`, `EnrollmentWidget`, `MainWindow`, `AdminDashboardView` |
| `services.head_pose` (`HeadPoseEstimator`) | `EnrollmentCameraThread`, `EnrollmentAIWorker`, `MainWindow`, `AdminDashboardView` |
| `services.attendance_service` (`AttendanceService`) | `UserModeView` (session lifecycle, record check-in), `AttendanceHistoryWidget` (query/export) |
| `services.authentication_service` (`AuthenticationService`) | `MainWindow` (login handler) |
| `services.settings_service` (`SettingsService`) | `SettingsWidget` (read/write), `UserModeView` (read freeze/camera settings), `EnrollmentWidget` (read camera index) |
| `services.enrollment_service` (`EnrollmentService`) | `EnrollmentWidget` (save face reference) |
| `repositories.user_repository` (`UserRepository`) | `UserManagementWidget` (CRUD), `EnrollmentWidget` (list unregistered users) |
| `repositories.face_reference_repository` (`FaceReferenceRepository`) | `UserManagementWidget` (delete face on user delete) |
| `repositories.caching_face_reference_repository` (`CachingFaceReferenceRepository`) | `EnrollmentWidget`, `UserManagementWidget`, `MainWindow` (cache invalidation) |
| `core.db` (`Database`) | `MainWindow` (status bar DB path), `AdminDashboardView` (dashboard stats queries), `AttendanceHistoryWidget` (direct queries), `UserManagementWidget` (student ID generation) |
| `utils.face_utils` (`_crop_face`, `_create_face_detector`) | `CameraThreadBase` (direct import via `CameraThreadBase.__init__`), `EnrollmentCameraThread` |
| `utils.time_utils` (`utc_now_iso`, `utc_to_local`, `local_to_utc`, `set_timezone_config`, `format_tz_label`, `timezone_signals`) | `UserModeView` (timestamp conversion, timezone re-render), `AttendanceHistoryWidget` (filter conversion, timezone re-render), `SettingsWidget` — `set_timezone_config` called by `SettingsWidget._save()`; `format_tz_label` imported by `SettingsWidget` for combo labels; `timezone_signals.timezone_changed` connected by `UserModeView.__init__` and `AttendanceHistoryWidget.__init__`. |
| `core.config` (`SystemConfig`, `SettingsResolver`, `resolve_config`) | `MainWindow` (config building, propagation to all views), `UserModeView` (thresholds from frozen config, camera index fallback), `EnrollmentWidget` (camera index, model paths, thresholds) |
| `core.defaults` (default threshold/timezone constants) | `SettingsWidget` (fallback values when DB key is unset) |

---

## File List

```
__init__.py                    # Package docstring
admin_dashboard_view.py        # Admin dashboard shell with sidebar nav + overview stats
attendance_history_widget.py   # Attendance history browser + split-view + export
camera_worker_base.py          # CameraThreadBase + AIWorkerBase (shared infrastructure)
camera_thread.py               # Attendance camera CameraThread + AIWorker
constants.py                   # Re-exported style constants + FONT_TITLE/FONT_STATUS
enrollment_ai_worker.py        # Enrollment AI inference worker EnrollmentAIWorker
enrollment_camera_thread.py    # Enrollment camera EnrollmentCameraThread (mirrored, pose-guided)
enrollment_widget.py           # Face enrollment UI widget (5-pose capture sequence)
login_widget.py                # Admin login form
main_window.py                 # Root QMainWindow + view router + status bar
settings_widget.py             # Camera scan + AI thresholds + timezone + freeze settings
styles.py                      # Qt stylesheet constants + GLOBAL_QSS + font helpers
user_management_widget.py      # User CRUD table with search + dialog-based add/edit
user_mode_view.py              # User attendance check-in view (idle/active, freeze overlay)
```
