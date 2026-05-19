# AGENTS.md

## Project

Python desktop face attendance system with anti-spoofing.

**Stack**: Python 3.11+, SQLite3 (WAL mode), bcrypt, PyQt5, ONNX Runtime
**Package**: `database-storage-core` (`package-dir = {"" = "src"}`)
**AI Models**: YuNet (detection), SFace (recognition), MiniFASNet quantized (liveness), MobileNetV2 (head-pose)

## Setup

```bash
cp .env.example .env
# Fernet key (only needed if FACE_EMBEDDING_FERNET_KEY is set):
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Models (`models/**/*.onnx`) are gitignored — download separately.

## How to Investigate

Read the highest-value sources first:
1. `pyproject.toml` — package name, entry points, dependencies, pytest config
2. `src/main.py` — entry point, config resolution order (CLI > .env > defaults), AI pipeline wiring
3. `src/attendance_system/core/db.py` — `Database` class, `DatabaseConfig` with path validation, `check_same_thread=False`
4. `src/attendance_system/core/bootstrap.py` — does NOT call `load_dotenv()` (see Gotchas)
5. `.env.example` — all config keys with descriptions and seed behavior

If architecture is unclear after reading the above, inspect:
- `src/attendance_system/ui/camera_thread.py` + `enrollment_camera_thread.py` — how camera + AI pipeline is wired
- `src/attendance_system/utils/face_utils.py` — shared `_crop_face` and `_create_face_detector`

Prefer executable sources of truth (`.py` config, entry points) over prose.

## Commands

```bash
pip install -e .                              # Editable install (first time + after deps change)
ruff check src/                               # Lint only (no formatter/typechecker)
pytest tests/                                 # All tests
pytest tests/unit/ -v                         # Unit tests only
pytest tests/integration/ -v                  # Integration tests only
pytest tests/unit/test_attendance_service.py -v  # Single test file
pytest tests/unit/test_*.py -v               # Single file via glob
$env:PYTHONPATH='src'; python src/main.py    # Dev run without install (PowerShell)
attendance-storage-init                       # Installed: DB bootstrap
attendance-app                                # Installed: GUI app
```

**Pre-commit order (no hooks)**: `ruff check` → `pytest`

**Config priority**: CLI args > `.env` > code defaults (resolved in `main.py` after `load_dotenv()`).

## Architecture

- `src/main.py` — Entry point; parses CLI, loads `.env`, wires services, launches PyQt5
- `src/attendance_system/core/` — `Database` (with `session()` ctx mgr), schema, bootstrap, storage manager
- `src/attendance_system/services/` — Business logic (enrollment, attendance, settings, AI pipeline, head-pose)
- `src/attendance_system/repositories/` — CRUD per entity (inherits `BaseRepository`)
- `src/attendance_system/models/entities.py` — `@dataclass(slots=True)` data classes
- `src/attendance_system/ui/` — PyQt5 components (main window, camera threads, login/dashboard)
- `src/attendance_system/utils/face_utils.py` — Shared `_crop_face` and `_create_face_detector`

Installed entry points (from `pyproject.toml`):
- `attendance-storage-init` → `attendance_system.core.bootstrap:main`
- `attendance-app` → `main:main`

Other instruction files:
- `CLAUDE.md` — Karpathy-style behavioral guidelines (simplicity, surgical changes)
- `.agents/` — OpenSpec workflow files (propose, explore, apply-change, archive-change, etc.)

## OpenSpec Workflow

```bash
openspec explore                    # Think through a problem before making changes
openspec propose <name>             # Create a new change with full proposal
openspec apply-change <name>        # Implement tasks from a change
openspec list                       # List active changes
openspec status --change <name>     # Check change completion
openspec archive-change <name>      # Archive a completed change
```

Changes live in `openspec/changes/<name>/`. Archive completed changes to `openspec/changes/archive/YYYY-MM-DD-<name>/`.

## DB

- `PRAGMA journal_mode = WAL`, `PRAGMA synchronous = NORMAL`, `PRAGMA foreign_keys = ON`
- `Database.session()` auto-commits on success, rollbacks on exception
- `check_same_thread=False` — intentional for PyQt5 camera thread
- Schema migrations via `ALTER TABLE ... ADD COLUMN` in `schema.py` (try/except on dup column)
- `DatabaseConfig.__post_init__` rejects paths containing `..`

## Testing

- `tests/unit/` — fast, no camera or GUI (12 files)
- `tests/integration/` — DB bootstrap, storage, offline behavior (7 files)
- `conftest.py` provides `database` fixture (tmp_path SQLite, full schema; auto-adds `src/` to `sys.path`)
- Imports use `from attendance_system.*` prefix (not relative)
- Opt-in soft dependency: `pytest.importorskip("cryptography.fernet")` + `monkeypatch.setenv`
- `conftest.py` imports `onnxruntime` first (same DLL conflict guard as `main.py`)
- No typechecker (mypy/pyright) configured

## Gotchas

- **`onnxruntime` must be imported BEFORE `PyQt5`** (main.py:17-20, conftest.py:7-10). On Windows, both load conflicting native DLLs.
- **`cryptography` is a soft dependency** (lazy import in `face_reference_repository.py:21`, not in `pyproject.toml`). Only needed when `FACE_EMBEDDING_FERNET_KEY` is set.
- **Initial admin from env**: `storage_manager.py:23-24` reads `ADMIN_USERNAME`/`ADMIN_PASSWORD` with fallback `"admin"`/`"admin"`.
- `CAMERA_INDEX=` (empty string) must be handled as missing — `_resolve_camera_index` at `main.py:79`.
- **`_crop_face` scale varies by use case** — enrollment uses `scale=2.7` (liveness), head-pose uses `scale=1.5` (default). Wrong scale silently rejects real users.
- **Enrollment completion checks `_target_count`**, not `len(_POSE_SEQUENCE)` — controls how many embeddings to capture before enrollment completes.
- Thresholds from `.env` seed the DB on first run only; subsequent changes go through the settings UI.
- Anti-spoofing is optional — disabled by `FACE_ANTISPOOF_ENABLED=false`.
- **`bootstrap.py` does NOT call `load_dotenv()`**, so `DATABASE_PATH` from `.env` is unseen when running `attendance-storage-init`. The CLI default is used instead.
- Camera frame flipped horizontally (`cv2.flip(frame, 1)`) — mirror-like UX for natural head turns.
- Head pose model missing → graceful fallback to legacy enrollment. `main.py:188-201`.
- `main()` accepts optional `argv` list for testability — do not call `sys.argv` directly in tests.
- **Test mock `_make_face()` in `test_head_pose_enrollment.py` uses `confidence=0`** — masks landmark-index bugs; use `confidence=0.99` and realistic landmarks in new tests.
