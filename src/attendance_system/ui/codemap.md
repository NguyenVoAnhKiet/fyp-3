# `ui/` — Presentation Layer

**Responsibility:** All PyQt5 UI widgets, camera capture QThread workers, and AI-inference worker threads. This package is the sole user-facing surface of the application. It does not contain business logic — it consumes `services/` and `repositories/`.

---

## Key Files

### Camera & Worker Threads

| File | Role |
|---|---|
| `camera_worker_base.py` | **Base classes** — `CameraThreadBase(QThread)` (camera init, `_retry_read()`, pause/resume, bbox drawing, display emission) and `AIWorkerBase(QThread)` (queue+sentinel, `submit_task()`, circuit-breaker, stop). Both define abstract `_process_frame()` for subclass override. |
| `camera_thread.py` | **Attendance camera** — `CameraThread(CameraThreadBase)` captures webcam frames, runs YuNet face detection, delegates liveness + recognition to `AIWorker(AIWorkerBase)` (inner QThread), emits annotated `QImage` frames. No frame mirroring. |
| `enrollment_camera_thread.py` | **Enrollment camera** — `EnrollmentCameraThread(CameraThreadBase)` captures webcam frames, **flips horizontally** (`cv2.flip(frame, 1)`), guides user through a 5-pose sequence (center, left, right, up, down) with head-pose estimation. Delegates async AI work to `EnrollmentAIWorker`. |
| `enrollment_ai_worker.py` | **Enrollment AI worker** — `EnrollmentAIWorker(AIWorkerBase)` background QThread that runs head-pose estimation, anti-spoofing (liveness), and face embedding extraction for enrollment. Queue size 1 for backpressure. |

### Widgets

| File | Role |
|---|---|
| `main_window.py` | Root `QMainWindow`. Houses a `QStackedWidget` routing between: `UserModeView` (index 0), `LoginWidget` (index 1), `AdminDashboardView` (index 2). Wires navigation signals; handles global quit (Q key). |
| `user_mode_view.py` | IDLE/ACTIVE dual-state widget. IDLE: subject + class input form. ACTIVE: camera feed, stats grid, attendance sidebar list, end-session button. Creates and controls `CameraThread`. Emits `login_requested`. |
| `login_widget.py` | Admin login card with username/password inputs. Emits `login_requested(username, password)` or `cancel_requested()`. No direct DB access — the parent `MainWindow` authenticates via `AuthenticationService`. |
| `admin_dashboard_view.py` | Dashboard shell with dark sidebar nav + content `QStackedWidget`. Contains sub-pages: welcome/overview, Settings, User Management, Enrollment, Attendance History. Emits `logout_requested`. |
| `enrollment_widget.py` | Face enrollment UI. User dropdown, camera feed, 5-step progress circles, pose guidance icon, progress bar. Creates/manages `EnrollmentCameraThread`. Saves face reference via `EnrollmentService`. |
| `settings_widget.py` | Form for camera index (background-thread scan) and AI thresholds (liveness, similarity). Persists via `SettingsService`. |
| `user_management_widget.py` | CRUD table for users (add/edit/delete with soft-delete). Uses `UserRepository` + `FaceReferenceRepository`. Inline search/filter. |
| `attendance_history_widget.py` | Session browser with date-range, class, subject filters. Split view: session list (left) → attendance records (right). Export to Excel (.xlsx) or CSV via `AttendanceService`. |
| `constants.py` | Re-exports all style constants from `styles.py` for convenience. Also defines `FONT_TITLE`, `FONT_STATUS`. |
| `styles.py` | Color palette, font helpers (`_make_font`), and `GLOBAL_QSS` (full Qt stylesheet with push buttons, inputs, tables, lists, scrollbars, etc.). |

---

## Camera Thread Gotchas

1. **`QImage.copy()` before cross-thread emission** — Both `CameraThreadBase._emit_display_frame()` and `EnrollmentCameraThread._emit_frame()` call `.copy()` on the `QImage` before emitting via `pyqtSignal(QImage)`. Without this, Qt's implicit sharing would reference released buffer memory, causing garbage frames or crashes.

2. **`import cv2.data`** — `camera_thread.py` explicitly imports `cv2.data` (`import cv2.data`). This is required because OpenCV's Python bindings do not always expose the `cv2.data` submodule automatically. The enrollment camera thread does not need it because it does not use `cv2.data`.

3. **`onnxruntime` before `PyQt5`** — Per project-wide rule (see `src/main.py` and `tests/conftest.py`), `import onnxruntime` must precede any `PyQt5` import on Windows to avoid DLL-load-order crashes. This is handled at the application entry point, not in individual UI modules.

4. **Frame buffer ownership in AI workers** — Both `AIWorkerBase.submit_task()` and `EnrollmentAIWorker.submit_task()` call `.copy()` on numpy arrays before pushing to the internal queue. This prevents the worker from reading a frame that has already been overwritten by the camera loop.

5. **Frame flip difference** — `EnrollmentCameraThread` mirrors the frame horizontally (`cv2.flip(frame, 1)`) so the user sees a natural mirror reflection. `CameraThread` does **not** flip — the attendance view shows the raw camera feed.

6. **Exponential backoff on read failures** — `CameraThreadBase._retry_read()` provides 3 attempts at 1s/2s/4s delays, recreating the `cv2.VideoCapture` each time. Used by both `CameraThread` and `EnrollmentCameraThread` via inheritance.

7. **Backpressure** — Both AI workers use a `queue.Queue(maxsize=1)` to submit frames. If the queue is full the frame is dropped (non-blocking). This prevents unbounded memory growth when AI inference is slower than the camera framerate.

8. **Circuit-breaker threshold** — `_MAX_CONSECUTIVE_FAILURES = 30` is defined once in `AIWorkerBase`. One broken model kills both attendance and enrollment (shared counter, ADR-0001). Override `_inference_error_types()` in subclass to specify caught exceptions.

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
                               │    └─ embedding extraction
                               └─ signals → EnrollmentCameraThread callbacks

SettingsWidget
  └─ _CameraScanThread ─────── probes camera indices (cv2.VideoCapture)
```

Key rules:
- Workers are created in `__init__`, started in `run()` (per project convention).
- AI workers use a `queue.Queue(maxsize=1)` with sentinel-based shutdown (managed by `AIWorkerBase`).
- On stop: drain queue, push sentinel, disconnect signals, `wait(3000)` (handled by `AIWorkerBase.stop()`).
- Camera thread `stop()` propagates to its AI worker via `_cleanup_worker()`, then waits on itself.

---

## Integration Points

| Layer | Consumed By |
|---|---|
| `services.ai_pipeline` (`FaceRecognizer`, `LivenessChecker`) | `CameraThread`, `AIWorker`, `EnrollmentCameraThread`, `EnrollmentAIWorker`, `UserModeView`, `EnrollmentWidget` |
| `services.head_pose` (`HeadPoseEstimator`) | `EnrollmentCameraThread`, `EnrollmentAIWorker` |
| `services.attendance_service` (`AttendanceService`) | `UserModeView` (session lifecycle, record check-in), `AttendanceHistoryWidget` (query/export) |
| `services.authentication_service` (`AuthenticationService`) | `MainWindow` (login handler) |
| `services.settings_service` (`SettingsService`) | `SettingsWidget` (read/write), `UserModeView` (read thresholds), `EnrollmentWidget` (read camera index) |
| `services.enrollment_service` (`EnrollmentService`) | `EnrollmentWidget` (save face reference) |
| `repositories.user_repository` (`UserRepository`) | `UserManagementWidget` (CRUD), `EnrollmentWidget` (list unregistered users) |
| `repositories.face_reference_repository` (`FaceReferenceRepository`) | `UserManagementWidget` (delete face on user delete) |
| `core.db` (`Database`) | `MainWindow` (status bar DB path), `AdminDashboardView` (dashboard stats queries), `AttendanceHistoryWidget` (direct queries) |
| `utils.face_utils` (`_crop_face`, `_create_face_detector`) | `CameraThreadBase`, `EnrollmentCameraThread` |
| `utils.time_utils` (`utc_now_iso`, `utc_to_local`, `local_to_utc`) | `UserModeView`, `AttendanceHistoryWidget` |

---

## File List

```
__init__.py                    # Package docstring
admin_dashboard_view.py        # Admin dashboard shell with sidebar nav
attendance_history_widget.py   # Attendance history browser + export
camera_worker_base.py          # CameraThreadBase + AIWorkerBase (shared infrastructure)
camera_thread.py               # Attendance camera CameraThread + AIWorker
constants.py                   # Re-exported style constants
enrollment_ai_worker.py        # Enrollment AI inference worker EnrollmentAIWorker
enrollment_camera_thread.py    # Enrollment camera EnrollmentCameraThread (mirrored)
enrollment_widget.py           # Face enrollment UI widget
login_widget.py                # Admin login form
main_window.py                 # Root QMainWindow + view router
settings_widget.py             # Camera + AI threshold settings form
styles.py                      # Qt stylesheet constants + GLOBAL_QSS
user_management_widget.py      # User CRUD table
user_mode_view.py              # User attendance check-in view
```
