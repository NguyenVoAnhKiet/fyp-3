# fyp-3/

**Python 3.11+ offline face-attendance desktop application.** Single-process
PyQt5 GUI backed by SQLite with WAL mode. The AI pipeline (detection →
recognition → anti-spoofing → head-pose) runs on ONNX Runtime with OpenCV
preprocessing. Authentication uses bcrypt; face embeddings are encrypted at rest
via Fernet symmetric encryption. All configuration is local (`.env` + `system_settings`
DB table) with CLI overrides for storage initialization.

---

## System Entry Points

| Entry point | Command | Module | Purpose |
|---|---|---|---|
| GUI application | `attendance-app` | `src/main.py:main()` | Launches the main window (camera, attendance tracking, enrollment, admin UI) |
| Storage initializer | `attendance-storage-init` | `attendance_system.core.bootstrap:main()` | Seeds the database schema and creates the admin account (idempotent) |

`attendance-storage-init` must be run at least once before the GUI can operate.
The bootstrap entry point uses raw CLI args + `DATABASE_PATH` env var (no
`load_dotenv()`). The GUI entry point calls `load_dotenv()`, resolves
configuration (CLI > env > DB > default), initializes storage, wires services,
then enters the Qt event loop.

---

## Root-Level Files

| File | Role |
|---|---|
| `pyproject.toml` | Project metadata, `requires-python >=3.11`, dependencies (PyQt5, onnxruntime, opencv-python, bcrypt, numpy, python-dotenv), CLI entry points (`attendance-app`, `attendance-storage-init`), setuptools package find under `src/`. |
| `.env.example` | Template for `.env`. Organised into 4 sections: **Security & Encryption** (Fernet key, admin credentials), **Database & Hardware** (DB path, camera index), **AI Models** (paths to YuNet, SFace, MiniFASNet, MobileNetV2 ONNX models + thresholds), **Attendance UX** (cooldown, frame-skip, timezone). |
| `AGENTS.md` | Primary orientation file for LLM agents. Contains: read-first file list, CLI commands, startup wiring details, per-module gotchas (threading, ONNX/PyQt5 import order, cooldowns, frame-skip constants, NULL-sort rules), and test layout. |
| `CLAUDE.md` | Behavioral guidelines for LLM agents: think-before-coding, simplicity-first, surgical changes, goal-driven execution. |
| `CONTEXT.md` | Domain context and glossary for the project. Referenced by `docs/agents/domain.md`. |
| `PROJECT_STATUS.md` | Current project status, known issues, and roadmap. |
| `UPDATE_SUMMARY.md` | Changelog / summary of recent updates. |
| `README.md` | *(Does not exist yet — the `docs/README.md` serves as the documentation index.)* |

---

## Repository Directory Map

| Directory | Responsibility | Detailed Map |
|---|---|---|
| `src/` | Application source code. Entry point (`main.py`) + the `attendance_system` namespace package containing all domain logic, services, UI widgets, persistence, and utilities. | [View Map](src/codemap.md) |
| `scripts/` | Standalone utility scripts for maintenance, diagnostics, and AI-model analysis. Includes `reset_users.py`, `diagnose_poor_light.py`, `test_poor_light_liveness.py`, `hypothesis_test_poor_light.py`, and `tune_liveness_threshold.py`. | [View Map](scripts/codemap.md) |
| `tests/` | Pytest test suite. `tests/unit/` — fast, mocked DB; `tests/integration/` — real DB/storage paths; `tests/contract/` — contract/invariant tests. `conftest.py` handles ONNX-before-PyQt5 import order and provides an isolated `database` fixture. | — |
| `docs/` | Project documentation: `docs/README.md` (doc index), `architecture.md`, `ai-pipeline.md`, `database.md`, `modules.md`, plus subdirectories for `adr/` (architecture decision records), `agents/` (agent workflow docs), `plans/` (feature plans), `srs/` (software requirements specification). Managed in Obsidian. | — |
| `models/` | ONNX model files (`.gitignore`d — must download separately before running integration tests or the app). Expected: YuNet detector, SFace recognizer, MiniFASNet anti-spoof, MobileNetV2 head-pose. | — |
| `data/` | Runtime data storage — exports, logs, and other generated artifacts. | — |
| `.agents/` | Agent tooling configuration and workspace files. | — |
| `.slim/` | Slim tooling workspace (used by the agent orchestration layer). | — |

---

## Subdirectory: `src/attendance_system/`

The main application package is structured as follows. Each sub-package has its
own `codemap.md` with detailed file-level maps.

| Sub-package | Responsibility |
|---|---|
| `core/` | Database bootstrap, schema definitions/upgrades, connection management, configuration resolution (SettingsResolver + frozen SystemConfig). |
| `models/` | Dataclass entities (student, attendance record, user, system settings, face reference, session, etc.). |
| `repositories/` | CRUD data-access layer with SQLite read/write, cache invalidation (`CachingFaceReferenceRepository` wrapper), and query builders. |
| `services/` | Business logic: AI pipeline orchestration (AIPipeline), face recognition, liveness checking/tracking, head-pose estimation, attendance record management, authentication, enrollment, settings admin. |
| `ui/` | PyQt5 widgets (MainWindow, UserModeView, AdminModeView, SettingsWidget, AttendanceHistoryWidget, dialogs), camera QThread workers (CameraThreadBase, AIWorkerBase and their concrete subclasses), and session-management components. |
| `utils/` | Shared utilities: face preprocessing (FacePreprocessor, PreprocessingConfig), timezone handling (utc_now_iso, utc_to_local, set_timezone_config, timezone_signals), and general helpers. |

