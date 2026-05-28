# AGENTS.md

Python 3.11+ desktop face-attendance app. Single-process PyQt5 UI, SQLite/WAL, ONNX Runtime, bcrypt. Offline only.

## Start here

Read in this order when orienting:
1. `pyproject.toml`
2. `src/main.py`
3. `src/attendance_system/core/db.py`
4. `src/attendance_system/core/bootstrap.py`
5. `.env.example`

If still unclear, inspect `src/attendance_system/ui/camera_thread.py`, `enrollment_camera_thread.py`, `enrollment_ai_worker.py`, and `face_utils.py`.

Prefer executable sources over prose; if docs conflict with code/config/scripts, trust the executable source.

## Commands

```bash
pip install -e .
pip install pytest
attendance-storage-init
attendance-app

ruff check src/
pytest tests/unit/ -v
pytest tests/integration/ -v
pytest tests/unit/test_camera_thread.py -v
PYTHONPATH=src python src/main.py
$env:PYTHONPATH='src'; python src/main.py
```

No formatter or typechecker is configured.

## Repo layout

- `src/attendance_system/services/` — AI pipeline, attendance, auth, enrollment, settings
- `src/attendance_system/repositories/` — CRUD repositories
- `src/attendance_system/ui/` — PyQt5 widgets and camera/QThread workers
- `src/attendance_system/core/` — DB, schema, bootstrap
- `src/attendance_system/models/` — dataclass entities

Entry points:
- `attendance-app` → `main:main`
- `attendance-storage-init` → `attendance_system.core.bootstrap:main`

## Hard gotchas

- Import `onnxruntime` before `PyQt5` on Windows in `src/main.py` and `tests/conftest.py`.
- `src/attendance_system/core/bootstrap.py` does not call `load_dotenv()`.
- `CAMERA_INDEX=` (empty string) must be treated as missing.
- `import cv2.data` is required in `camera_thread.py`.
- `QImage` emitted across threads must be `.copy()`'d first.
- Create worker `QThread`s in `__init__`, start them in `run()`.
- `EnrollmentCameraThread` flips frames; attendance camera does not.
- `FaceReferenceRepository._cache_all` is keyed by DB path; every write path must invalidate cache.
- `attendance_records.user_id` is nullable and uses `ON DELETE SET NULL`.
- `_crop_face` scales: attendance/enrollment liveness `2.7`, head-pose default `1.5`.
- `attendance-storage-init` is the only bootstrap CLI; `attendance-app` is the GUI.

## Tests and fixtures

- `tests/conftest.py` imports `onnxruntime` first and builds an isolated tmp-path SQLite DB with full schema.
- `tests/unit/` is the fast suite; `tests/integration/` hits DB/storage paths.
- `cryptography` is a soft dependency; tests may skip encryption paths with `pytest.importorskip("cryptography.fernet")`.
- `pandas` and `openpyxl` are soft dependencies for Excel export.

## Environment / assets

- `.venv\` is the expected local venv and is gitignored.
- `models/**/*.onnx` are gitignored; download them separately.
- First-run threshold values are seeded from `.env`; later changes come from the settings UI.
- Anti-spoofing can be disabled with `FACE_ANTISPOOF_ENABLED=false`.

## Repository Map

A full codemap is available at `codemap.md` in the project root.

Before working on any task, read `codemap.md` to understand:
- Project architecture and entry points
- Directory responsibilities and design patterns
- Data flow and integration points between modules

For deep work on a specific folder, also read that folder's `codemap.md`.
