# AGENTS.md

Python desktop face attendance system with anti-spoofing. 100% offline, single-process PyQt5 app.

**Stack**: Python 3.11+, SQLite3 (WAL mode), bcrypt, PyQt5, ONNX Runtime
**Package**: `database-storage-core` (`package-dir = {"" = "src"}`)
**AI Models**: YuNet (detection), SFace (recognition), MiniFASNet quantized (liveness), MobileNetV2 (head-pose)
**CI/CD**: None — all verification is local. No formatter, no typechecker.
**Behavioral guidelines**: `CLAUDE.md` (read before coding).
**Build system**: setuptools (`pip install -e .`). `uv.lock` exists but is unused by the build.

## Setup

```bash
cp .env.example .env
pip install -e .                       # editable install
pip install pytest                     # not in pyproject.toml deps
attendance-storage-init                # bootstrap DB schema
attendance-app                         # launch GUI
```

Models (`models/**/*.onnx`) are gitignored — download separately.

## How to Investigate

Read high-value sources first:
1. `pyproject.toml` — entry points (`attendance-storage-init`, `attendance-app`), dependencies, package layout
2. `src/main.py` — entry point, config resolution (CLI > `.env` > defaults), import order (onnxruntime before PyQt5)
3. `src/attendance_system/core/db.py` — `Database` + `session()` ctx mgr, WAL pragmas, `check_same_thread=False`
4. `src/attendance_system/core/bootstrap.py` — **does NOT call `load_dotenv()`** — standalone CLI tool
5. `.env.example` — all config keys with descriptions

If architecture is still unclear: `camera_thread.py` (AIWorker + pipeline wiring), `enrollment_camera_thread.py`, `enrollment_ai_worker.py`, `face_utils.py` (shared `_crop_face` / `_create_face_detector`).

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
- `src/main.py` — Entry point; parses CLI, loads `.env`, wires services, launches PyQt5; accepts optional `argv` for testability
- `attendance_system/core/` — `Database` (with `session()` ctx mgr), schema, bootstrap, storage manager
- `attendance_system/services/` — Business logic: AI pipeline (liveness + recognition), attendance, authentication, enrollment, head-pose, settings, exceptions
- `attendance_system/repositories/` — CRUD per entity (inherit `BaseRepository`). `FaceReferenceRepository` has a class-level `_cache_all` (keyed by DB path) — must call `_invalidate_cache()` on write
- `attendance_system/models/entities.py` — `@dataclass(slots=True)` data classes
- `attendance_system/ui/` — PyQt5 components: camera threads, AIWorker, EnrollmentAIWorker, login, dashboard, settings (13 widgets)
- `attendance_system/utils/` — `face_utils.py`, logging, time utils

Entry points: `attendance-storage-init` → `bootstrap:main`, `attendance-app` → `main:main`

### Threading

AI pipeline runs on background `QThreads`:
- **CameraThread**: frame-skip `_AI_FRAME_SKIP=3` (~10 Hz inference). AIWorker has own `QThread` with `maxsize=1` queue for backpressure + `is_busy()` check. Numpy arrays MUST be `.copy()`'d before queuing (except `EnrollmentAIWorker.submit_task()` does it internally).
- **EnrollmentCameraThread**: horizontally mirrored (`cv2.flip(frame, 1)`). Pose-guided sequence (5 targets, 5 holds) or legacy landmark fallback.
- **Detector isolation**: each camera thread creates its own `FaceDetectorYN` via `_create_face_detector()` — avoids `setInputSize()` race conditions.

## DB

- `PRAGMA journal_mode = WAL`, `PRAGMA synchronous = NORMAL`, `PRAGMA foreign_keys = ON`
- `Database.session()` auto-commits on success, rollbacks on exception
- `check_same_thread=False` — intentional for PyQt5 camera thread access
- Schema migrations: `ALTER TABLE ... ADD COLUMN` in `schema.py` (try/except on dup column)
- `DatabaseConfig.__post_init__` rejects paths containing `..`

## Testing

- `tests/unit/` (11 files) — fast, no camera or GUI
- `tests/integration/` (9 files) — DB bootstrap, storage, offline behavior
- `tests/contract/` — empty directory, reserved for future contract tests
- `conftest.py` provides `database` fixture (`tmp_path` SQLite, full schema), adds `src/` to `sys.path`, imports `onnxruntime` first (DLL conflict guard)
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
- **`_crop_face` scale**: attendance + enrollment liveness use `scale=2.7`, head-pose uses `1.5` (default). Wrong scale silently rejects real users. Key locations: `camera_thread.py:_capture_face` (scale=2.7), `enrollment_ai_worker.py` lines 85 (pose, default) and 118 (capture, scale=2.7), `enrollment_camera_thread.py` legacy path line 240 (scale=2.7).
- **Enrollment completion checks `_target_count`** (5 embeddings), not `len(_POSE_SEQUENCE)`.
- **AIWorker** (`camera_thread.py`): Liveness + recognition on separate `QThread` with `maxsize=1` queue. Call `is_busy()` to check if queue is full before submitting. `submit_task()` copies arrays internally. Sentinel pattern (`_SENTINEL`) for clean shutdown.
- **EnrollmentAIWorker** (`enrollment_ai_worker.py`): `submit_task()` does `.copy()` internally — callers do NOT need to pre-copy. Has its own circuit breaker (30 consecutive failures across pose + liveness). Signals: `pose_estimated`, `capture_complete`, `inference_warning`, `camera_error`.
- **Circuit breaker** (both workers): after 30 consecutive ONNX failures, emits `camera_error` and terminates. Counter resets on success. ADR at `docs/adr/0001-onnx-circuit-breaker.md`.
- **Enrollment frame is flipped horizontally** (`cv2.flip(frame, 1)` in `enrollment_camera_thread.py`) — mirror-like UX. Main attendance camera does NOT flip.
- **Head pose model missing → graceful fallback to legacy enrollment** (`_handle_legacy_frame` in `enrollment_camera_thread.py`, called when `head_pose_estimator is None`).
- Thresholds from `.env` seed the DB on first run only; subsequent changes go through settings UI.
- Anti-spoofing is optional — `FACE_ANTISPOOF_ENABLED=false`.
- **`bootstrap.py` does NOT call `load_dotenv()`** — `DATABASE_PATH` from `.env` is unseen when running `attendance-storage-init`. CLI default or `--database-path` is used instead.
- **Test mock `_make_face()` in `tests/integration/test_head_pose_enrollment.py` uses `confidence=0`** (index 4 of the 15-element row) — masks landmark-index bugs; use `confidence=0.99` and realistic landmarks in new tests.
- **Camera read failure retries**: Both `CameraThread` and `EnrollmentCameraThread` retry with exponential backoff (1s, 2s, 4s, max 3). After 3 failures, `camera_error` is emitted and the thread stops.
- **FaceReferenceRepository cache**: class-level `_cache_all: ClassVar[dict[str, list[dict]]]` keyed by database path. `get_all()` uses cache; `upsert()` and `delete_by_user_id()` call `_invalidate_cache()`. Any new write path must invalidate too, or the cache returns stale rows.
- **`cv2.data` submodule must be explicitly imported** (`import cv2.data` in `camera_thread.py` line 11) — OpenCV's `cv2.data` is not guaranteed to be importable via lazy loading on all platforms.
