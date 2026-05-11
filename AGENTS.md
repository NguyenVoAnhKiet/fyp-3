# AGENTS.md

**Gitignored** (`.gitignore` lists this + `CLAUDE.md`). Changes are local-only.
See `CLAUDE.md` for behavioral guidelines used by this session.

## Project

Python desktop face attendance system with anti-spoofing.

**Stack**: Python 3.11+, SQLite3 (WAL mode), bcrypt, PyQt5, ONNX Runtime
**Package**: `database-storage-core` (pyproject.toml), `attendance_system` under `src/`

## Setup

```bash
cp .env.example .env
# Fernet key for face embedding encryption (only needed if FACE_EMBEDDING_FERNET_KEY is set):
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Models (`models/**/*.onnx`) are gitignored — download separately.

## Commands

```bash
ruff check src/          # Lint + format check (no project-specific config — runs defaults)
pytest tests/            # All tests (conftest auto-adds src/ to PYTHONPATH)
pytest tests/unit/test_security.py::test_name -v   # Single test
PYTHONPATH=src python src/main.py                  # Dev run (no install)
attendance-storage-init  # Installed entry: DB bootstrap
attendance-app           # Installed entry: Main GUI app
```

**Recommended order**: `ruff check` → `pytest`

`load_dotenv()` at `src/main.py:123` — must run before any `os.getenv()` call.
Standalone scripts must call it themselves.

## Architecture

- `src/attendance_system/core/` — DB connection (`Database` with `session()` context manager, in `db.py`), schema, bootstrap
- `src/attendance_system/services/` — Business logic (enrollment, attendance, security, settings, AI pipeline)
- `src/attendance_system/repositories/` — CRUD per entity
- `src/attendance_system/models/entities.py` — `@dataclass(slots=True)` data classes
- `src/attendance_system/ui/` — PyQt5 components (main window, camera thread, login/dashboard)
- `src/attendance_system/utils/` — Utilities (only `time_utils.py`)
- `src/main.py` — Application entry point
- AI models: YuNet (detection), SFace (recognition), MiniFASNet quantized (liveness)

## DB

- `PRAGMA journal_mode = WAL`, `PRAGMA synchronous = NORMAL`, `PRAGMA foreign_keys = ON`
- `Database.session()` auto-commits on success, rollbacks on exception
- `check_same_thread=False` — intentional for PyQt5 camera thread

## Testing

- `conftest.py` provides `database` fixture (tmp_path SQLite DB with schema; auto-adds `src/` to `sys.path`)
- Suites: `tests/unit/` (8 files), `tests/integration/` (8 files), `tests/contract/` (empty)
- Imports use `from attendance_system.*` prefix (not relative)
- Tests create service/repository instances directly from `database` fixture
- Optional dependency pattern: `pytest.importorskip("cryptography.fernet")` + `monkeypatch.setenv`

## Gotchas

- **onnxruntime must be imported BEFORE PyQt5** (`src/main.py:20`). On Windows, both import conflicting native DLLs.
- `CAMERA_INDEX=` (empty string in `.env`) must be handled as missing — `_resolve_camera_index` in `main.py:79`.
- Thresholds from `.env` are seeded into DB on first run only; subsequent changes go through the settings UI.
- Anti-spoofing is optional — disabled by `FACE_ANTISPOOF_ENABLED=false`.
- **`cryptography` is a soft dependency** (lazy import in `face_reference_repository.py:21`). Not in `pyproject.toml`. Only needed when `FACE_EMBEDDING_FERNET_KEY` is set.
- **`ADMIN_USERNAME`/`ADMIN_PASSWORD` in `.env.example` are NOT read.** Initial admin is hardcoded as `admin`/`admin` in `storage_manager.py:22-23`.

## Anti-spoofing Model

Quantized MiniFASNet ONNX at `models/anti_spoof/best_model_quantized.onnx`
Output: `[1, 2]` logits — index 0 = real, index 1 = spoof

## Agent skills

### Issue tracker

Local markdown issues tracked under `.scratch/`. See `docs/agents/issue-tracker.md`.

### Triage labels

Canonical labels mapped to their names. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context layout at the repo root. See `docs/agents/domain.md`.
