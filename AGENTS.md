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
- Migration errors are now logged explicitly (no silent failures) — `_migrate_attendance_records_cascade_to_setnull()` re-raises exceptions after logging.
- Session-status validation — `record_success()`, `record_duplicate()`, `record_spoof_warning()`, `record_unrecognized()` all raise `SessionClosedError` for closed sessions.

## Tests / assets

- `tests/conftest.py` imports `onnxruntime` first and builds an isolated tmp SQLite DB with full schema.
- `tests/unit/` is the fast suite; `tests/integration/` hits DB/storage paths.
- `cryptography`, `pandas`, and `openpyxl` are soft dependencies; tests may skip related paths.
- `models/**/*.onnx` are gitignored; download them separately.
- First-run threshold values come from `.env`; later changes come from the settings UI.
- `FACE_ANTISPOOF_ENABLED=false` disables anti-spoofing.

## Liveness Detection (Anti-Spoofing)

- **Model:** MiniFASNet V2 SE quantized (INT8, 600 KB). Trained on CelebA-Spoof, works best well-lit frontal < 30°.
- **Temporal Smoothing:** `LivenessTracker` in `src/attendance_system/core/liveness_tracker.py` uses EMA (α=0.4) + hysteresis (T_HIGH=0.65, T_LOW=0.45) + IoU face tracking to reduce flicker.
- **Threshold:** Default 0.3 (reduced from 0.5 for poor-light tolerance). Set via `FACE_ANTISPOOF_CONFIDENCE_THRESHOLD` in `.env` or Admin UI.
- **Preprocessing:** CLAHE + resize + reflect-pad. CLAHE not in training pipeline but removal worsens poor-light performance.
- **Crop Scale:** 2.7 for liveness (large context), 1.5 for head-pose (tight crop).
- **Tuning Script:** `scripts/tune_liveness_threshold.py` collects real/fake videos, extracts frames, runs ONNX inference, plots histogram, recommends optimal threshold (target: FAR < 1%, FRR < 5%).
- **Known Limitation:** 2D texture classifier; poor lighting still rejects ~95% real faces (model limitation, not preprocessing).
