# AGENTS.md

Python 3.11+ offline face-attendance desktop app. PyQt5 UI, SQLite/WAL, ONNX Runtime, bcrypt.

## Read first

1. `pyproject.toml` — deps, entry points, build config
2. `src/main.py` — app bootstrap (import order matters: onnxruntime before PyQt5)
3. `src/attendance_system/core/config.py` — `SettingsResolver` + frozen `SystemConfig` (CLI > env > DB > default; `seed_db_from_env` is idempotent)
4. `src/attendance_system/core/db.py` — SQLite connection (WAL, foreign keys, `check_same_thread=False`)
5. `src/attendance_system/core/bootstrap.py` — storage initializer (no `load_dotenv()`, uses CLI args)
6. `.env.example` — all configurable env vars (4 sections: Security & Encryption, Database & Hardware, AI Models, Attendance UX)
6. `codemap.md` + per-module `codemap.md` files — directory map with entrypoints
7. `docs/README.md` — doc index (architecture, ai-pipeline, database, modules, adr, plans, agents)

Prefer executable sources over prose; if docs conflict with code/config/scripts, trust the executable source.

## Commands

```bash
pip install -e .
pip install pytest
attendance-storage-init                      # seed DB + admin account
attendance-storage-init --database-path <p>   # custom path
attendance-app                                # launch GUI
ruff check src/                               # full lint (E501 line-length pre-existing)
ruff check src/ --select F                    # undefined names only (fast pre-commit check)
pytest tests/                                 # full suite (280 tests: 250 unit + 30 integration)
pytest tests/unit/ -v                         # fast unit-only
pytest tests/integration/ -v                  # DB/storage integration
PYTHONPATH=src python src/main.py             # dev run without `pip install -e .`
$env:PYTHONPATH='src'; python src/main.py     # Windows equivalent
```

`pytest` is a dev dependency (not in `pyproject.toml`); install with `pip install pytest`.

## Wiring

- **Entry points:** `attendance-app` → `main:main`; `attendance-storage-init` → `attendance_system.core.bootstrap:main`.
- **Startup order:** `load_dotenv()` → `SettingsResolver.resolve()` (builds frozen `SystemConfig`, CLI > env > DB > default) → `set_timezone_config(config.timezone)` → `initialize_storage()` → `SettingsResolver.seed_db_from_env()` (idempotent env→DB seeding) → validate ONNX models → wire services → launch `MainWindow`.
- **`bootstrap.py`** uses raw CLI args + `DATABASE_PATH` env var, **not** `load_dotenv()`.
- **`db.py`** connections: WAL journal, `synchronous=NORMAL`, `foreign_keys=ON`, `check_same_thread=False`. Path traversal guard in `DatabaseConfig`.
- **Config priority:** CLI arg > env var > DB > default (timezone is the exception — DB > env > default, no CLI flag). Resolved by `SettingsResolver` in `core/config.py`. Seed-once env→DB flow: `SettingsResolver.seed_db_from_env()` only writes if the DB key is unset, so Admin UI changes survive.

## Related agent files

- `CLAUDE.md` — behavioral layer (think before coding, simplicity, surgical changes, goal-driven execution). Read alongside this file.
- `docs/agents/issue-tracker.md` — issues live on **GitHub Issues** via `gh` CLI; repo inferred from `git remote -v`.
- `docs/agents/triage-labels.md` — five canonical labels: `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`.
- `docs/agents/domain.md` — read root `CONTEXT.md` + relevant `docs/adr/*` before working in an area; use glossary vocabulary in outputs.
- `docs/plans/README.md` — feature plans convention (`active/` → `archive/` with date prefix on Done; standard sections: Status / Context / Goals / Non-Goals / Design Decisions / Implementation / Testing).
- `docs/adr/0001-onnx-circuit-breaker.md` — explains the 30-failure ONNX circuit-breaker pattern.

## Gotchas

- `CAMERA_INDEX=` (empty string) in `.env` counts as missing → defaults to 0.
- `onnxruntime` must be imported **before** `PyQt5` on Windows (DLL conflict). Both `src/main.py` and `tests/conftest.py` do this.
- `QImage` crossing threads must be `.copy()`'d first.
- Create worker `QThread`s in `__init__`, start them in `run()`.
- `EnrollmentCameraThread` flips frames (mirror); attendance `CameraThread` does not.
- `CachingFaceReferenceRepository` wrapper owns the face-references cache; inner `FaceReferenceRepository` is a pure SQLite adapter. Invalidation is enforced by the wrapper — see `tests/unit/test_caching_face_reference_repository.py` (parametrized over 4 write methods).
- `_crop_face` scale: 2.7 for liveness (broad context), 1.5 for head-pose (tight crop).
- `_COOLDOWN_SECONDS = 3.0` in `camera_thread.py` — per-user cooldown before re-recognition. In-memory, resets on thread restart.
- `_AI_FRAME_SKIP = 3` — full AI pipeline runs every 3rd frame (~10 Hz at 30 fps).
- `_PAUSE_POLL_INTERVAL_SECONDS = 0.05` — `CameraThreadBase.pause()`/`resume()` poll interval; `AIWorker` idles naturally on its own queue.
- `user_mode_view.py` tracks `_recognized_users` (set of `user_id`) to suppress duplicate sidebar entries + `_stats_success` increment. `_stats_total` always increments (total events).
- `record_success()` catches `IntegrityError` internally on UNIQUE `(session_id, user_id)` — falls back to SELECT-existing, returns normally. Caller never sees a DB exception for duplicates.
- `record_duplicate()` does **not** insert a `recognition_events` row (no audit trail for the second path — caller is expected to have already inserted one).
- `attendance_records.user_id` is nullable, `ON DELETE SET NULL`.
- LEFT JOIN required when joining `attendance_records` → `users`; INNER JOIN silently drops records of deleted users. NULL sort: `ORDER BY u.full_name ASC` puts deleted-user rows first — use `IS NULL, full_name ASC` to push them last.
- Migration errors are now logged explicitly + re-raised (no silent failures). See `schema.py` `except Exception` blocks.
- Session-status validation: `record_success()`, `record_spoof_warning()`, `record_unrecognized()` all raise `SessionClosedError` on closed sessions.

## Tests

- `tests/conftest.py` imports `onnxruntime` before `pytest`, ensures `src/` is on `sys.path`, and provides a `database` fixture (isolated `tmp_path` SQLite, full schema).
- `tests/unit/` — fast, mocked DB; `tests/integration/` — real DB/storage paths.
- `cryptography`, `pandas`, `openpyxl` are soft deps; tests skip related paths if missing.
- `models/**/*.onnx` are gitignored — download separately before running integration tests.

## Liveness (Anti-Spoofing)

- **Model:** MiniFASNet V2 SE quantized (INT8, 600 KB). Best well-lit frontal <30°.
- **Temporal smoothing:** `LivenessTracker` (`src/attendance_system/services/liveness_tracker.py`, relocated from `core/` in Plan 0004) uses EMA (α=0.4) + hysteresis (T_HIGH=0.65, T_LOW=0.45) + IoU tracking.
- **Threshold:** Default 0.3. Configurable via `FACE_ANTISPOOF_CONFIDENCE_THRESHOLD` env var or Admin UI.
- **Preprocessing:** `FacePreprocessor` (`src/attendance_system/services/face_preprocessor.py`) with `LIVENESS_CONFIG` (scale=2.7, 128×128, [0,1], letterbox, RGB) and `HEAD_POSE_CONFIG` (scale=1.5, 224×224, ImageNet, direct resize, BGR). Defined in `preprocessing_configs.py`. CLAHE is OFF by default (`use_clahe=False`) — toggleable per config but not wired to env/UI yet. Adding a new model = define a new `PreprocessingConfig`, not duplicate preprocessing code (plan 0007).
- **Crop scale:** 2.7 for liveness, 1.5 for head-pose (encoded in each model's `PreprocessingConfig.scale`).
- **Known limitation:** 2D texture classifier; poor lighting still rejects ~95% real faces (model limitation).

## AI Pipeline Orchestration

- **AIPipeline** (`src/attendance_system/services/ai_pipeline.py`): Orchestrates per-frame AI inference. Composes `LivenessChecker`, `FaceRecognizer`, `LivenessTracker`, and optionally `HeadPoseEstimator`. Methods: `run_attendance()` → `PipelineResult`, `run_enrollment()` → `PipelineResult`.
- **PipelineResult** (`src/attendance_system/services/pipeline_result.py`): `@dataclass(slots=True)` with `result_type` discriminator and optional fields for liveness, recognition, head-pose, and embedding outputs.
- **Backward compat:** `core/liveness_tracker.py` re-exports from `services/liveness_tracker.py`.

## Camera Worker Base Classes

- **CameraThreadBase** (`src/attendance_system/ui/camera_worker_base.py`): Base `QThread` for camera capture. Provides: camera init, `_retry_read()` (exponential backoff), `pause()`/`resume()`, `_detect_faces()`, `_draw_bboxes()`, `_annotate_frame()`, `_emit_display_frame()`, `stop()`. Concrete `run()` loop calls abstract `_process_frame()`.
- **AIWorkerBase** (`src/attendance_system/ui/camera_worker_base.py`): Base `QThread` for AI inference workers. Provides: `queue.Queue(maxsize=1)` + sentinel shutdown, `submit_task(*args)` (auto-copies numpy arrays), `is_busy()`, `stop()` (drain + sentinel + wait). Concrete `run()` loop with circuit-breaker (`_MAX_CONSECUTIVE_FAILURES = 30`). Calls abstract `_process_frame()`.
- **Inheritance:** `CameraThread` + `EnrollmentCameraThread` inherit `CameraThreadBase`. `AIWorker` + `EnrollmentAIWorker` inherit `AIWorkerBase`.
- **Circuit-breaker:** Shared counter in `AIWorkerBase`. ADR-0001: one broken model kills both attendance and enrollment. Override `_inference_error_types()` to specify caught exceptions per subclass.

## Timezone

- **Storage:** all DB timestamps are UTC ISO-8601 (`utc_now_iso` from `utils/time_utils.py`).
- **Display:** UI converts via `utc_to_local`; date-range filters go from local picker → `local_to_utc` → DB query.
- **Configuration:** `set_timezone_config(name)` in `utils/time_utils.py` mutates the module-level `_tz` (default UTC, falls back on invalid input). Called once at startup (from `main.py`) and again at runtime (from `SettingsWidget._save()`).
- **Cross-widget signal:** `time_utils.timezone_signals` is a module-level `_TimezoneSignals(QObject)` singleton exposing `pyqtSignal(str) timezone_changed`. Safe to construct before `QApplication` exists. `UserModeView` and `AttendanceHistoryWidget` connect in `__init__` and re-render on change.
- **Admin UI:** 13 curated IANA choices in `TIMEZONE_CHOICES` (`Asia/Ho_Chi_Minh` is the default; `UTC` is last). Dropdown labels rendered via `format_tz_label(name)`.
- **Resolution:** `SettingsResolver._resolve_timezone` in `core/config.py` validates IANA names against `zoneinfo.ZoneInfo`; order is DB > env > default (no CLI flag). Catches only `ZoneInfoNotFoundError` (narrowed from bare `Exception` per plan 0008) to surface real bugs.
- **Pre-existing stdlib quirk:** `ZoneInfo(name).utcoffset(None)` returns `None` for fixed-offset zones in Python's stdlib `zoneinfo`, so non-UTC dropdown labels currently render as the raw IANA name — `UTC` is the only entry that shows an offset. Tracked outside plan 0008.

## Repository Map

A full codemap is available at `codemap.md` in the project root.

Before working on any task, read `codemap.md` to understand:
- Project architecture and entry points
- Directory responsibilities and design patterns
- Data flow and integration points between modules

For deep work on a specific folder, also read that folder's `codemap.md`.
