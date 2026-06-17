# `src/` — Application Source Package

**Top-level Python package for the face-attendance desktop application.**
Contains the CLI/entry-point logic (`main.py`) and the sub-package
`attendance_system/` which implements all core logic, services, UI, and
storage. This layer owns configuration resolution (CLI > env > DB > default),
bootstrap ordering, and wiring of services into the `MainWindow`.

## Key Files

| File | Role |
|---|---|
| `__init__.py` | Package marker — docstring: `Application source package.` |
| `main.py` | System entry point — see below. |

---

## `main.py` — System Entry Point

Defines `main()` (invoked by the `attendance-app` console script). Orchestrates
the full startup sequence: loads `.env`, resolves configuration via
`SettingsResolver`, bootstraps the SQLite schema, seeds first-run DB values,
validates ONNX model files, wires repositories and services, and launches the
PyQt5 `MainWindow`.

### Critical import ordering

**`import onnxruntime` must appear before `from PyQt5`.** On Windows, both
libraries load conflicting native DLLs into the process address space. Importing
onnxruntime first ensures its DLLs are resolved correctly. The import is
guarded with `# noqa: F401` since the binding is purely a side-effect.

```python
import onnxruntime  # noqa: F401  # MUST come before PyQt5
from PyQt5.QtWidgets import QApplication, QMessageBox
```

### Bootstrap order

1. **`load_dotenv()`** — load `.env` before any env-read
2. **`SettingsResolver.resolve()` (provisional)** — build partial `SystemConfig` (CLI > env > default); no DB reader yet since the schema does not exist
3. **`initialize_storage()`** — create/upgrade SQLite schema (WAL mode)
4. **Create `QApplication`**
5. **Create Database & SettingsService, then `seed_db_from_defaults()`** — instantiate `Database` with the provisional path and `SettingsService`, then idempotently write `defaults.py` values into `system_settings` (only if key is unset, so Admin UI changes survive)
6. **`resolve_config()` (final)** — re-resolve `SystemConfig` via `SettingsResolver.resolve()` passing `settings_service` as the DB reader (DB > JSON defaults > defaults.py for settings; timezone is DB > defaults.py)
7. **`set_timezone_config()`** — apply resolved timezone to `time_utils` module-level `_tz`
8. **Validate model files** — check existence of required ONNX paths; optional head-pose model falls back to legacy mode on error
9. **Build services** — `AttendanceService`, `AuthenticationService` (backed by `AdminRepository`), `LivenessChecker`, `CachingFaceReferenceRepository` wrapping `FaceReferenceRepository`, `FaceRecognizer` (receives the caching repo), and optionally `HeadPoseEstimator`. Note: `AIPipeline` is no longer constructed here; it is created inside `CameraThread.__init__` and receives `liveness_checker` + `face_recognizer` at that point.
10. **Instantiate and show `MainWindow`** — imported from `attendance_system.ui.main_window`, receives nine dependencies: `attendance_service`, `settings_service`, `authentication_service`, `liveness_checker`, `face_recognizer`, `head_pose_estimator`, `database`, `config`, and `face_repo`. Enter Qt event loop via `app.exec_()`.

---

## Subdirectory Map

| Directory | Responsibility | Detailed Map |
|---|---|---|
| `attendance_system/` | Root package of the face-attendance application — all domain, service, UI, and persistence code lives here. Delegates to sub-packages for core, models, repositories, services, ui, and utils. | [View Map](attendance_system/codemap.md) |
