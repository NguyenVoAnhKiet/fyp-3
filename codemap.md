# fyp-3/

**Python 3.11+ desktop face-attendance application.** Offline-only, single-process PyQt5 GUI backed by SQLite with WAL mode. The AI pipeline (detection → recognition → anti-spoofing → head-pose) runs on ONNX Runtime with OpenCV preprocessing. Authentication uses bcrypt; face embeddings are encrypted at rest via Fernet symmetric encryption. All configuration is local (`.env` + settings table).

## System Entry Points

| Entry point | Command | Module |
|---|---|---|
| GUI application | `attendance-app` | `src/main.py:main()` |
| Storage initializer | `attendance-storage-init` | `attendance_system.core.bootstrap:main()` |

`attendance-storage-init` seeds the database schema and admin credentials; `attendance-app` launches the main window.

## Key Config Files

- **`pyproject.toml`** — Project metadata, Python >=3.11 requirement, dependencies (PyQt5, onnxruntime, opencv-python, bcrypt, deepface-cv2, numpy, python-dotenv), and CLI entry points.
- **`.env.example`** — Template for `.env`. Controls: camera index, DB path, timezone, AI model paths (YuNet detector, SFace recognizer, MiniFASNet anti-spoof, MobileNetV2 head-pose), threshold seeding (anti-spoof confidence, similarity score), admin credentials, and Fernet encryption key.

## Directory Map

| Directory | Responsibility | Detailed Map |
|---|---|---|
| `src/` | Application entry point (`main.py`) + `attendance_system` namespace | [View Map](src/codemap.md) |
| `src/attendance_system/` | Root package — delegates to sub-packages below | [View Map](src/attendance_system/codemap.md) |
| `src/attendance_system/core/` | Database bootstrap, schema definitions, connection management | [View Map](src/attendance_system/core/codemap.md) |
| `src/attendance_system/models/` | Dataclass entities (student, attendance record, user, settings, etc.) | [View Map](src/attendance_system/models/codemap.md) |
| `src/attendance_system/repositories/` | CRUD data-access layer with SQLite read/write and cache invalidation | [View Map](src/attendance_system/repositories/codemap.md) |
| `src/attendance_system/services/` | Business logic: AI pipeline orchestration, attendance tracking, auth, enrollment, settings | [View Map](src/attendance_system/services/codemap.md) |
| `src/attendance_system/ui/` | PyQt5 widgets, main window, dialog screens, camera QThread workers | [View Map](src/attendance_system/ui/codemap.md) |
| `src/attendance_system/utils/` | Shared utility functions (face preprocessing, helpers) | [View Map](src/attendance_system/utils/codemap.md) |
| `models/` | ONNX model files (`.gitignore`d — download separately) | — |
| `tests/` | Pytest suite: `tests/unit/` + `tests/integration/` | — |
| `data/` | Runtime data storage (exports, logs, etc.) | — |
| `docs/` | Documentation assets | — |
| `scripts/` | Helper scripts | [View Map](scripts/codemap.md) |
| `.agents/` | Agent tooling config | — |
| `.slim/` | Slim tooling workspace | — |
