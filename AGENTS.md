# AGENTS.md

Python desktop face attendance system with anti-spoofing.

**Stack**: Python 3.11+, SQLite3 (WAL mode), bcrypt, PyQt5, ONNX Runtime
**Package**: `database-storage-core` (`package-dir = {"" = "src"}`)
**AI Models**: YuNet (detection), SFace (recognition), MiniFASNet quantized (liveness), MobileNetV2 (head-pose)
**CI/CD**: None — all verification is local. No formatter, no typechecker.
**Behavioral guidelines**: `CLAUDE.md` (read before coding).

## Setup

```bash
cp .env.example .env
pip install -e .                       # editable install
pip install pytest                     # not in pyproject deps
attendance-storage-init                # bootstrap DB schema
attendance-app                         # launch GUI
```

Models (`models/**/*.onnx`) are gitignored — download separately.

## How to Investigate

High-value sources first:
1. `pyproject.toml` — package name, entry points, dependencies
2. `src/main.py` — entry point, config resolution (CLI > .env > defaults)
3. `src/attendance_system/core/db.py` — `Database` + `session()` ctx mgr
4. `src/attendance_system/core/bootstrap.py` — does NOT call `load_dotenv()`
5. `.env.example` — all config keys with descriptions

If unclear: `camera_thread.py` (AIWorker + AI pipeline wiring), `enrollment_camera_thread.py`, `enrollment_ai_worker.py`, `face_utils.py` (shared `_crop_face` / `_create_face_detector`).

Prefer executable sources over prose. If docs conflict with code, trust the code.

## Commands

```bash
ruff check src/                               # Lint only (no formatter/typechecker)
pytest tests/                                 # All tests
pytest tests/unit/ -v                         # Unit tests (fast, no camera/GUI)
pytest tests/integration/ -v                  # Integration tests (DB/storage/offline)
pytest tests/unit/test_camera_thread.py -v    # Single file
PYTHONPATH=src python src/main.py             # Dev run without install
```

**Order**: `ruff check src/` → `pytest tests/`

## Architecture

Single-package: `src/` → `attendance_system` namespace.
- `src/main.py` — Entry point; parses CLI, loads `.env`, wires services, launches PyQt5
- `attendance_system/core/` — `Database` (with `session()` ctx mgr), schema, bootstrap, storage manager
- `attendance_system/services/` — Business logic (AI pipeline, attendance, authentication, enrollment, head-pose, settings, exceptions)
- `attendance_system/repositories/` — CRUD per entity (inherit `BaseRepository`)
- `attendance_system/models/entities.py` — `@dataclass(slots=True)` data classes
- `attendance_system/ui/` — PyQt5 components (camera threads, AIWorker, enrollment AI worker, login, dashboard, settings)
- `attendance_system/utils/` — `face_utils.py`, logging, time utils

Entry points: `attendance-storage-init` → `bootstrap:main`, `attendance-app` → `main:main`

## DB

- `PRAGMA journal_mode = WAL`, `PRAGMA synchronous = NORMAL`, `PRAGMA foreign_keys = ON`
- `Database.session()` auto-commits on success, rollbacks on exception
- `check_same_thread=False` — intentional for PyQt5 camera thread
- Schema migrations: `ALTER TABLE ... ADD COLUMN` in `schema.py` (try/except on dup column)
- `DatabaseConfig.__post_init__` rejects paths containing `..`

## Testing

- `tests/unit/` — fast, no camera or GUI (11 files)
- `tests/integration/` — DB bootstrap, storage, offline behavior (9 files)
- `conftest.py` provides `database` fixture (tmp_path SQLite, full schema), adds `src/` to `sys.path`, imports `onnxruntime` first (DLL conflict guard)
- Imports use `from attendance_system.*` prefix (not relative)
- Soft dependency: `pytest.importorskip("cryptography.fernet")` + `monkeypatch.setenv`
- No typechecker — `ruff check` only

## Issue Tracker & OpenSpec

Issues: GitHub Issues via `gh` CLI. Labels `needs-triage`/`needs-info`/`ready-for-agent`/`ready-for-human`/`wontfix` (state), `bug`/`enhancement` (category), `p1`-`p4` (priority). Conventions at `docs/agents/issue-tracker.md` and `docs/agents/triage-labels.md`.

OpenSpec workflow: `openspec explore|propose|apply-change|list|archive-change`. Changes in `openspec/changes/<name>/`, archive to `openspec/changes/archive/YYYY-MM-DD-<name>/`.

## Gotchas

- **`onnxruntime` must be imported BEFORE `PyQt5`** (`main.py` lines 17-20, `conftest.py` lines 7-10). On Windows, both load conflicting native DLLs.
- **`cryptography` is a soft dependency** (lazy import in `face_reference_repository.py:_get_fernet`). Only needed when `FACE_EMBEDDING_FERNET_KEY` is set.
- **Initial admin from env**: `storage_manager.py:_seed_admin` reads `ADMIN_USERNAME`/`ADMIN_PASSWORD` with fallback `"admin"`/`"admin"`.
- `CAMERA_INDEX=` (empty string) must be handled as missing — `_resolve_camera_index` in `main.py`.
- **`_crop_face` scale: attendance + enrollment liveness use `scale=2.7`**, head-pose uses `1.5` (default). Wrong scale silently rejects real users. Key locations: `camera_thread.py:_capture_face` (scale=2.7), `enrollment_ai_worker.py` lines 85 (pose, default) and 118 (capture, scale=2.7), `enrollment_camera_thread.py` legacy path line 240 (scale=2.7).
- **Enrollment completion checks `_target_count`**, not `len(_POSE_SEQUENCE)`.
- **Detector isolation**: Each camera thread creates its own `FaceDetectorYN` (YuNet) via `_create_face_detector()`. No shared/centralized instance — avoids `setInputSize()` race conditions. `main.py` passes only the model path (`detector_model_path=...`) to `MainWindow`.
- **AIWorker** (`camera_thread.py`): Liveness + recognition run on a separate `QThread` with a `maxsize=1` queue for backpressure. Numpy arrays MUST be copied before queuing (`frame_bgr.copy()`, `camera_thread.py`) or the frame buffer gets overwritten. Sentinel pattern (`_SENTINEL`) for clean shutdown.
- **EnrollmentAIWorker** (`enrollment_ai_worker.py`): Newer async worker for enrollment pipeline. Has its own `maxsize=1` queue and circuit breaker (30 consecutive failures across pose + liveness). Unlike AIWorker, `submit_task()` does the `.copy()` internally — callers do NOT need to pre-copy. Signals: `pose_estimated`, `capture_complete`, `inference_warning`, `camera_error`.
- **ONNX inference circuit breaker**: AIWorker has its own circuit breaker — after 30 consecutive `LivenessInferenceError`, emits `camera_error` and terminates. EnrollmentAIWorker has a separate circuit breaker (same threshold, covers both pose + liveness errors). ADR at `docs/adr/0001-onnx-circuit-breaker.md`.
- **Enrollment camera frame flipped horizontally** (`cv2.flip(frame, 1)` in `enrollment_camera_thread.py`) — mirror-like UX. Main attendance camera does NOT flip.
- **Head pose model missing → graceful fallback to legacy enrollment** (`_handle_legacy_frame` in `enrollment_camera_thread.py`, called when `head_pose_estimator is None`).
- Thresholds from `.env` seed the DB on first run only; subsequent changes go through settings UI.
- Anti-spoofing is optional — `FACE_ANTISPOOF_ENABLED=false`.
- **`bootstrap.py` does NOT call `load_dotenv()`** — `DATABASE_PATH` from `.env` is unseen when running `attendance-storage-init`. The CLI default or a `--database-path` arg is used instead.
- `main()` accepts optional `argv` list for testability — do not call `sys.argv` directly in tests.
- **Test mock `_make_face()` in `tests/integration/test_head_pose_enrollment.py` uses `confidence=0`** — masks landmark-index bugs; use `confidence=0.99` and realistic landmarks in new tests.
- **Camera read failure retries**: Both `CameraThread` and `EnrollmentCameraThread` retry with exponential backoff (1s, 2s, 4s, max 3). Thread does not exit on single glitch. After 3 failures, `camera_error` is emitted and the thread stops.
