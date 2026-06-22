# AGENTS.md

Python 3.10+ offline face-attendance desktop app. PyQt5 UI, SQLite/WAL, ONNX Runtime, bcrypt. Windows primary (Linux/macOS compatible but untested).

Runs on Python 3.10+. `from __future__ import annotations` is used across the codebase to defer type evaluation at runtime.

## Read first

1. `README.md` — bilingual project overview, quick start, known limitations (first thing committee/reviewers see)
2. `pyproject.toml` — deps, entry points, build config
3. `src/main.py` — app bootstrap (import order matters: onnxruntime before PyQt5)
4. `src/attendance_system/core/config.py` — `SettingsResolver` + frozen `SystemConfig` (DB-seedable: DB > defaults.py; non-DB: CLI > env > default)
5. `src/attendance_system/core/db.py` — SQLite connection (WAL, foreign keys, `check_same_thread=False`)
6. `src/attendance_system/core/bootstrap.py` — storage initializer (loads `.env` for admin seeding; uses CLI args for DB path)
7. `.env.example` — non-DB settings only (paths, camera, feature flags)
8. `src/attendance_system/core/defaults.py` — seedable DB defaults as Python constants (9 keys, single source of truth)
9. `codemap.md` + per-module `codemap.md` files — directory map with entrypoints

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
pytest tests/                                 # full suite (unit + integration)
pytest tests/unit/ -v                         # fast unit-only
pytest tests/integration/ -v                  # DB/storage integration
PYTHONPATH=src python src/main.py             # dev run without `pip install -e .`
$env:PYTHONPATH='src'; python src/main.py     # Windows equivalent
```

`pytest` is a dev dependency (not in `pyproject.toml`); install with `pip install pytest`.

## Wiring

- **Entry points:** `attendance-app` → `main:main`; `attendance-storage-init` → `attendance_system.core.bootstrap:main`.
- **Startup order:** `load_dotenv()` → `SettingsResolver.resolve()` (first pass, DB-independent → provisional config) → `initialize_storage()` → `SettingsResolver.seed_db_from_defaults()` (idempotent defaults→DB seeding) → `SettingsResolver.resolve()` (second pass with DB → final `SystemConfig`) → `set_timezone_config(config.timezone)` → validate ONNX models → wire services → launch `MainWindow`.
- **`bootstrap.py`** calls `load_dotenv()` so `ADMIN_USERNAME` / `ADMIN_PASSWORD` can be read from `.env` for admin seeding. Config resolution uses `env={}` (hermetic) to determine `database_path` without pulling in other runtime env values.
- **`db.py`** connections: WAL journal, `synchronous=NORMAL`, `foreign_keys=ON`, `check_same_thread=False`. Path traversal guard in `DatabaseConfig`.
- **Config priority:** CLI arg > env var > DB > default (timezone is the exception — DB > env > default, no CLI flag). Resolved by `SettingsResolver` in `core/config.py`. Seed-once defaults→DB flow: `SettingsResolver.seed_db_from_defaults()` only writes if the DB key is unset, so Admin UI changes survive.

## Related agent files

- `CLAUDE.md` — behavioral layer (think before coding, simplicity, surgical changes, goal-driven execution). Read alongside this file.
- `docs/agents/issue-tracker.md` — issues live on **GitHub Issues** via `gh` CLI; repo inferred from `git remote -v`.
- `docs/agents/triage-labels.md` — five canonical labels: `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`.
- `docs/agents/domain.md` — read relevant `docs/adr/*` before working in an area; use glossary vocabulary in outputs. (`CONTEXT.md` was deleted; `PROJECT_STATUS.md` fills the role.)
- `docs/plans/README.md` — feature plans convention (`active/` → `archive/` with date prefix on Done; standard sections: Status / Context / Goals / Non-Goals / Design Decisions / Implementation / Testing).
- `docs/adr/0001-onnx-circuit-breaker.md` — explains the 30-failure ONNX circuit-breaker pattern.

## Gotchas

- `CAMERA_INDEX=` (empty string) in `.env` counts as missing → defaults to 0.
- `onnxruntime` must be imported **before** `PyQt5` on Windows (DLL conflict). Both `src/main.py` and `tests/conftest.py` do this.
- `QImage` crossing threads must be `.copy()`'d first.
- Create worker `QThread`s in `__init__`, start them in `run()`.
- Both `CameraThreadBase.run()` and `EnrollmentCameraThread` flip frames horizontally (`cv2.flip(frame, 1)`) so users see a mirror reflection. The raw camera feed is NOT shown to users.
- `CachingFaceReferenceRepository` wrapper owns the face-references cache; inner `FaceReferenceRepository` is a pure SQLite adapter. Invalidation is enforced by the wrapper — see `tests/unit/test_caching_face_reference_repository.py` (parametrized over 4 write methods).
- Enrollment tab has a "Hiển thị users đã enroll" checkbox. When checked, `UserRepository.list_active()` returns all users (not just unregistered). Re-enroll uses the same 5-pose flow; `save_enrollment()` atomically replaces old poses. Confirmation dialog prevents accidental re-enroll.
- Enrollment camera preview only shows `_guidance_text` (single line, e.g., "Nghiêng trái", "Giữ yên"). `_status_text`, `_angles_text`, `_hold_text` are not drawn on the camera — they're only used in `_sync_progress` for the widget labels below the camera.
- `_angles_label` ("Góc: -") has been removed from enrollment UI. The angles data still flows through `_angles_text` in the camera thread but is not displayed.
- Distance hint "📏 Ngồi cách camera khoảng 30 cm" appears in the ACTIVE attendance panel (top row, right of title) and in the enrollment widget (below guidance label). Uses `STATUS_INFO` color + bold for visibility.
- `_crop_face` scale: 2.7 for liveness (broad context), 1.5 for head-pose (tight crop).
- `_COOLDOWN_SECONDS = 1.5` in `camera_thread.py` — per-user cooldown before re-recognition. In-memory, resets on thread restart.
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

## Scripts

Standalone diagnostic/maintenance scripts in `scripts/`. Not part of app entry points; run manually.
- `reset_users.py` — wipe users + face references (preserves attendance history). Interactive confirmation required.
- `diagnose_poor_light.py` — single-image liveness diagnostic with preprocessing variants (CLAHE, gamma).
- `test_poor_light_liveness.py` — synthetic brightness sweep across preprocessing methods.
- `hypothesis_test_poor_light.py` — root-cause investigation of poor-light rejection (4 hypotheses).
- `tune_liveness_threshold.py` — data-driven threshold calibration from real + spoof video pairs.

See `scripts/codemap.md` for full details and the investigative pipeline relationship.

## Liveness (Anti-Spoofing)

- MiniFASNet V2 SE quantized. 2D texture classifier — poor lighting rejects ~95% real faces (model limitation).
- Temporal smoothing: EMA (α=0.4) + IoU tracking in `services/liveness_tracker.py`. Liveness decisions now use `HybridLivenessDecider` (5-frame majority voting, configurable threshold). Hysteresis (T_HIGH/T_LOW) has been removed.
- Crop scale: 2.7 for liveness (broad context), 1.5 for head-pose (tight crop). Wrong scale silently rejects real users.

## Camera Workers

- `CameraThreadBase` + `AIWorkerBase` in `ui/camera_worker_base.py`. Attendance/enrollment variants inherit from each.
- Circuit-breaker: 30 consecutive ONNX failures kills the thread (ADR-0001). One broken model kills both attendance and enrollment.

## Timezone

- All DB timestamps are UTC ISO-8601. UI converts via `utc_to_local`; date filters use `local_to_utc` → DB query.
- `set_timezone_config(name)` in `utils/time_utils.py` mutates the module-level `_tz`. Called at startup and again on Settings save.
- Cross-widget signal: `time_utils.timezone_signals.timezone_changed` — `UserModeView` and `AttendanceHistoryWidget` connect to re-render on change.
- Resolution order: DB > defaults.py (no CLI flag, no env override).

## Repository Map

A full codemap is available at `codemap.md` in the project root.

Before working on any task, read `codemap.md` to understand:
- Project architecture and entry points
- Directory responsibilities and design patterns
- Data flow and integration points between modules

For deep work on a specific folder, also read that folder's `codemap.md`.
