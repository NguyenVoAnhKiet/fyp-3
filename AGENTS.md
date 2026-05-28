# AGENTS.md

Python 3.11+ offline face-attendance desktop app. PyQt5 UI, SQLite/WAL, ONNX Runtime, bcrypt.

## Read first

1. `pyproject.toml`
2. `src/main.py`
3. `src/attendance_system/core/db.py`
4. `src/attendance_system/core/bootstrap.py`
5. `.env.example`
6. `codemap.md`

If still unclear, inspect `src/attendance_system/ui/camera_thread.py`, `enrollment_camera_thread.py`, `enrollment_ai_worker.py`, and `face_utils.py`.

Prefer executable sources over prose; if docs conflict with code/config/scripts, trust the executable source.

## Commands

```bash
pip install -e .
pip install pytest
attendance-storage-init
attendance-storage-init --database-path <path>
attendance-app
ruff check src/
pytest tests/
pytest tests/unit/ -v
pytest tests/integration/ -v
pytest tests/unit/test_camera_thread.py -v
PYTHONPATH=src python src/main.py
$env:PYTHONPATH='src'; python src/main.py
```

## Wiring

- Only CLI entrypoints are `attendance-app` → `main:main` and `attendance-storage-init` → `attendance_system.core.bootstrap:main`.
- `src/main.py` imports `onnxruntime` before `PyQt5` on Windows, then loads `.env`, resolves config, initializes storage, validates models, and launches the UI.
- `src/attendance_system/core/bootstrap.py` does not call `load_dotenv()`; it uses CLI args and `DATABASE_PATH`.
- `src/attendance_system/core/db.py` creates SQLite connections with WAL, foreign keys on, `check_same_thread=False`, and a DB-path guard.

## Gotchas

- `CAMERA_INDEX=` (empty string) counts as missing.
- `QImage` crossing threads must be `.copy()`'d first.
- Create worker `QThread`s in `__init__`, start them in `run()`.
- `EnrollmentCameraThread` flips frames; attendance camera does not.
- `FaceReferenceRepository._cache_all` is keyed by DB path; every write path must invalidate cache.
- `attendance_records.user_id` is nullable and uses `ON DELETE SET NULL`.
- `_crop_face` scales: attendance/enrollment liveness `2.7`, head-pose default `1.5`.

## Tests / assets

- `tests/conftest.py` imports `onnxruntime` first and builds an isolated tmp SQLite DB with full schema.
- `tests/unit/` is the fast suite; `tests/integration/` hits DB/storage paths.
- `cryptography`, `pandas`, and `openpyxl` are soft dependencies; tests may skip related paths.
- `models/**/*.onnx` are gitignored; download them separately.
- First-run threshold values come from `.env`; later changes come from the settings UI.
- `FACE_ANTISPOOF_ENABLED=false` disables anti-spoofing.
