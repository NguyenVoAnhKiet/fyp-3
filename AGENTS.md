# AGENTS.md

Python desktop face attendance system with anti-spoofing. 100% offline, single-process PyQt5 app.

**Stack**: Python 3.11+, SQLite3 (WAL), bcrypt, PyQt5, ONNX Runtime
**Build**: `pip install -e .` (setuptools). `uv.lock` exists but unused.
**Verification**: `ruff check src/` → `pytest tests/`. No formatter/typechecker.

## Setup

```bash
cp .env.example .env
pip install -e .
pip install pytest                 # not in pyproject.toml deps
attendance-storage-init            # bootstrap DB schema
attendance-app
```

Models (`models/**/*.onnx`) are gitignored — download separately.

## How to Investigate

High-value sources (read in order):
1. `pyproject.toml` — entry points, deps, package layout
2. `src/main.py` — config resolution (CLI > `.env` > defaults), import order
3. `src/attendance_system/core/db.py` — `Database` + `session()` ctx mgr, WAL, `check_same_thread=False`
4. `src/attendance_system/core/bootstrap.py` — standalone CLI, does **NOT** call `load_dotenv()`
5. `.env.example` — all config keys

If architecture still unclear: `camera_thread.py` (AIWorker + pipeline), `enrollment_camera_thread.py`, `enrollment_ai_worker.py`, `face_utils.py`.

Prefer executable sources over prose. If docs conflict with code, trust the code.

## Commands

```bash
ruff check src/
pytest tests/unit/ -v              # fast, no camera/GUI (11 files)
pytest tests/integration/ -v       # DB/storage/offline (9 files)
pytest tests/unit/test_camera_thread.py -v
PYTHONPATH=src python src/main.py  # dev run without install
```

## Architecture

Single package: `src/` → `attendance_system`.
- `services/` — AI pipeline (liveness + recognition), attendance, auth, enrollment, settings
- `repositories/` — CRUD per entity, inherit `BaseRepository`. `FaceReferenceRepository` has class-level `_cache_all` keyed by DB path — **must call `_invalidate_cache()` on write**.
- `ui/` — PyQt5 QThread-based camera threads, AIWorker, login, dashboard, settings
- `core/` — DB connection, schema migrations, storage bootstrap
- `models/entities.py` — `@dataclass(slots=True)`
- `utils/` — face processing helpers (`face_utils.py`), time utilities

Entry points: `attendance-storage-init` → `attendance_system.core.bootstrap:main`, `attendance-app` → `main:main`

All AI inference runs on background `QThreads`:
- **CameraThread**: frame-skip 3 (~10 Hz). AIWorker on separate `QThread` with `maxsize=1` queue + `is_busy()` guard. Numpy arrays MUST be `.copy()`'d before queuing.
- **EnrollmentCameraThread**: horizontally mirrored (`cv2.flip(frame, 1)`). Pose-guided sequence (5 targets, 5 holds) or legacy fallback.
- **Detector isolation**: each camera thread creates own `FaceDetectorYN` via `_create_face_detector()` — avoids `setInputSize()` races.

## DB

- `PRAGMA journal_mode = WAL`, `synchronous = NORMAL`, `foreign_keys = ON`
- `Database.session()` auto-commits on success, rollbacks on exception
- `check_same_thread=False` — intentional for PyQt5 camera thread access
- Schema migrations: `ALTER TABLE ... ADD COLUMN` in `schema.py` (try/except on dup column)
- `DatabaseConfig.__post_init__` rejects paths containing `..`

## Testing

- Unit tests (`tests/unit/`, 11 files) — fast, no camera/GUI
- Integration tests (`tests/integration/`, 9 files) — DB, storage, offline
- `tests/contract/` — empty, reserved
- `conftest.py`: tmp_path SQLite + full schema; adds `src/` to `sys.path`; imports onnxruntime first (DLL guard)
- Imports use `from attendance_system.*` (not relative)
- Soft dep: `pytest.importorskip("cryptography.fernet")` + `monkeypatch.setenv`

## Gotchas

**Critical (agent will miss these):**
- **onnxruntime must be imported BEFORE PyQt5**: both `main.py` and `conftest.py` order this first. On Windows both load conflicting native DLLs.
- **`cv2.data` must be explicitly imported**: `import cv2.data` in `camera_thread.py:11` — not auto-loaded on all platforms.
- **`bootstrap.py` does NOT call `load_dotenv()`**: `DATABASE_PATH` from `.env` is invisible. Use `--database-path` CLI arg or `os.getenv("DATABASE_PATH")` fallback in `bootstrap.py:25` instead.
- **`CAMERA_INDEX=` empty string** must be treated as missing — `_resolve_camera_index` in `main.py`.
- **FaceReferenceRepository._cache_all**: class-level `dict[str, list[dict]]` keyed by DB path. `get_all()` reads cache; `upsert()` and `delete_by_user_id()` call `_invalidate_cache()`. Any new write path must invalidate or cache returns stale rows.
- **`_crop_face` scale**: attendance/enrollment liveness uses `scale=2.7`, head-pose uses `1.5` (default). Wrong scale silently rejects real users.

**Threading & data safety:**
- **QImage cross-thread emit needs `.copy()`**: `QImage` from external buffer is non-owning. Qt queued connections use shallow copy (implicit sharing). Always `.copy()` before emitting across threads.
- **submit_task() array ownership differs**: `AIWorker.submit_task()` expects pre-copied arrays. `EnrollmentAIWorker.submit_task()` copies arrays internally.
- **Enrollment frame is flipped** (`cv2.flip`), attendance frame is not.
- **Circuit breaker**: 30 consecutive ONNX failures → `camera_error` signal → thread terminates. Counter resets on success. ADR at `docs/adr/0001-onnx-circuit-breaker.md`.
- **Camera retries**: exponential backoff (1s, 2s, 4s, max 3). After 3 failures, `camera_error` emitted and thread stops.

**Enrollment-specific:**
- **Head pose model missing** → graceful fallback to legacy enrollment (`_handle_legacy_frame` in `enrollment_camera_thread.py`).
- **Enrollment completion** checks `_target_count` (5 embeddings), not `len(_POSE_SEQUENCE)`.
- **Test mock `_make_face()`** in `test_head_pose_enrollment.py` uses `confidence=0` (index 4 of 15-element row) — masks landmark-index bugs. Use `confidence=0.99` + realistic landmarks in new tests.

**Other:**
- `cryptography` is soft-dep: lazy import in `face_reference_repository.py:_get_fernet`. Only needed when `FACE_EMBEDDING_FERNET_KEY` is set.
- Initial admin from env: `ADMIN_USERNAME` / `ADMIN_PASSWORD`, fallback `"admin"`/`"admin"`.
- Thresholds from `.env` seed DB on first run only; subsequent changes go through settings UI.
- Anti-spoofing is optional (`FACE_ANTISPOOF_ENABLED=false`).
