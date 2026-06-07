# `src/` — Application Entry Point

## Responsibility

Top-level Python package for the face-attendance desktop application. Contains
the CLI/entry-point logic (`main.py`) and the sub-package
`attendance_system/` which implements all core logic, services, UI, and
storage. This layer owns configuration resolution (CLI > env > defaults),
bootstrap ordering, and wiring of services into the `MainWindow`.

## Key Files

| File | Role |
|---|---|
| `__init__.py` | Package marker — empty docstring only. |
| `main.py` | Application entry point. Defines `main()` (invoked by the `attendance-app` console script). Calls `SettingsResolver` + `set_timezone_config` to wire configuration before launching the UI. |

### Critical gotcha in `main.py`

**`import onnxruntime` must appear before `from PyQt5`**. On Windows, both
libraries load conflicting native DLLs into the process address space. Importing
onnxruntime first ensures its DLLs are resolved correctly. The import is
guarded with `# noqa: F401` since the binding is purely a side-effect.

```python
import onnxruntime  # noqa: F401  # MUST come before PyQt5
from PyQt5.QtWidgets import QApplication, QMessageBox
```

### Bootstrap order in `main()`

1. `load_dotenv()` — load `.env` before any env-read
2. `SettingsResolver(...).resolve(...)` — build the frozen `SystemConfig` (CLI > env > DB > default for paths/thresholds/timezone/UX)
3. `set_timezone_config(config.timezone)` — set module-level `_tz` in `time_utils`
4. `initialize_storage()` — create/upgrade SQLite schema (WAL mode)
5. Create `QApplication`, validate model file existence
6. Build repositories, services (AI pipeline, auth, settings, attendance)
7. Seed first-run values from `.env` into the `system_settings` DB table (idempotent — only if not already set, see `SettingsResolver.seed_db_from_env`)
8. Instantiate and show `MainWindow`, enter Qt event loop

## Subdirectory Map

| Directory | Responsibility |
|---|---|
| `attendance_system/` | Main application package — all domain, service, UI, and persistence code. See its own `codemap.md` for details. |
