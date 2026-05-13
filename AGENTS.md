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

## Commands

```bash
pip install -e .                              # Editable install for dev
ruff check src/                               # Lint (default rules; no formatter/typechecker configured)
pytest tests/                                 # All tests
pytest tests/unit/test_security.py -v         # Single file
pytest tests/unit/test_security.py::test_name -v  # Single test
$env:PYTHONPATH='src'; python src/main.py    # Dev run (no install, PowerShell)
attendance-storage-init                       # Installed: DB bootstrap
attendance-app                                # Installed: GUI app
```

**Order**: `ruff check` → `pytest`

`load_dotenv()` called inside `main()` — must run before any `os.getenv()`.
Standalone scripts (e.g. `bootstrap.py`) do NOT call it themselves.

## Architecture

- `src/main.py` — Entry point; parses CLI, loads `.env`, wires services, launches PyQt5
- `src/attendance_system/core/` — `Database` (with `session()` ctx mgr), schema, bootstrap, storage manager
- `src/attendance_system/services/` — Business logic (enrollment, attendance, security, settings, AI pipeline, head-pose)
- `src/attendance_system/repositories/` — CRUD per entity (inherits `BaseRepository`)
- `src/attendance_system/models/entities.py` — `@dataclass(slots=True)` data classes
- `src/attendance_system/ui/` — PyQt5 components (main window, camera thread, login/dashboard)
- `src/attendance_system/utils/` — Only `time_utils.py`

Installed entry points (from `pyproject.toml`):
- `attendance-storage-init` → `attendance_system.core.bootstrap:main`
- `attendance-app` → `main:main` (resolves to `src/main.py` via `package-dir = {"" = "src"}`)

Other:
- `CLAUDE.md` — Behavioral guidelines at repo root (Karpathy-style: surgical changes, simplicity first)
- `.agents/` — OpenSpec workflow files (`opsx-*.md`)
- `specs/` — Speckit specs (used during development with `.specify/`)
- `openspec/` — OpenSpec specs + archived changes

## DB

- `PRAGMA journal_mode = WAL`, `PRAGMA synchronous = NORMAL`, `PRAGMA foreign_keys = ON`
- `Database.session()` auto-commits on success, rollbacks on exception
- `check_same_thread=False` — intentional for PyQt5 camera thread
- Schema migrations via `ALTER TABLE ... ADD COLUMN` in `schema.py` (try/except on dup column)
- `DatabaseConfig.__post_init__` rejects paths containing `..` (path traversal guard)

## Testing

- `conftest.py` provides `database` fixture (tmp_path SQLite, full schema; auto-adds `src/` to `sys.path`)
- Imports use `from attendance_system.*` prefix (not relative)
- Opt-in soft dependency: `pytest.importorskip("cryptography.fernet")` + `monkeypatch.setenv`
- `conftest.py` imports `onnxruntime` first (same DLL conflict guard as `main.py`)
- No typechecker (mypy/pyright) configured

## Gotchas

- **`onnxruntime` must be imported BEFORE `PyQt5`** (main.py:17-20, conftest.py:7-10). On Windows, both load conflicting native DLLs.
- **`cryptography` is a soft dependency** (lazy import in `face_reference_repository.py:21`). Not in `pyproject.toml`. Only needed when `FACE_EMBEDDING_FERNET_KEY` is set.
- **`ADMIN_USERNAME`/`ADMIN_PASSWORD` in `.env.example` are NOT read.** Initial admin is hardcoded as `admin`/`admin` in `storage_manager.py:22-23`.
- `CAMERA_INDEX=` (empty string) must be handled as missing — `_resolve_camera_index` at `main.py:79`.
- Thresholds from `.env` seed the DB on first run only; subsequent changes go through the settings UI.
- Anti-spoofing is optional — disabled by `FACE_ANTISPOOF_ENABLED=false`.
- `bootstrap.py` does NOT call `load_dotenv()`, so `DATABASE_PATH` from `.env` is unseen when running `attendance-storage-init`.
