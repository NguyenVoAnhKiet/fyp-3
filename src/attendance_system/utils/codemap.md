# src/attendance_system/utils/

## Responsibility

General-purpose utility/helper functions shared across the application. Contains two
independent modules — one for face-image manipulation (cropping, detector setup) and
one for timezone-aware datetime formatting with a Qt signal bus for cross-widget
timezone-change notifications.

## Design

### `face_utils.py`

Exposes two low-level helpers consumed by camera threads, AI workers, and services:

- **`_crop_face(frame, bbox, scale=1.5)`** — Squares and pads a face bounding box by
  a multiplier so downstream models see consistent regions. The default `scale=1.5` is
  used by head-pose estimation; callers override to **`2.7`** for the liveness
  sub-pipeline in both attendance and enrollment paths.
- **`_create_face_detector(model_path, input_size, score_threshold, nms_threshold)`** —
  Factory wrapper around `cv2.FaceDetectorYN.create` (YuNet ONNX model). Returns a
  ready-to-use detector; all parameters are caller-supplied (no defaults live here
  except reasonable YuNet defaults).

Both functions are prefixed with `_` (module-private by convention) but are imported
directly by four callers across the ui/ and services/ packages:

| Function | Direct importers |
|---|---|
| `_crop_face` | `services/ai_pipeline.py`, `services/face_preprocessor.py`, `ui/enrollment_camera_thread.py` |
| `_create_face_detector` | `ui/camera_worker_base.py` |

### `time_utils.py`

Timezone-aware datetime formatting built on Python's `zoneinfo` (stdlib ≥ 3.9) with a UTC
fallback, plus a Qt signal bus for cross-widget timezone-change notifications.

- **Module-level `_tz`** — The currently configured timezone. Defaults to
  `datetime.timezone.utc`. Initialised at startup by `set_timezone_config(tz_name)` called
  from `main.py`; re-initialised at runtime by the Admin Settings UI when the user changes
  timezone.
- **`_TimezoneSignals(QObject)`** — Private QObject class (underscore-prefixed,
  module-internal). Exposes a single `timezone_changed = pyqtSignal(str)` carrying the new
  IANA name. Wrapped by the module-level `timezone_signals` singleton; safe to construct
  before `QApplication` exists (only widgets need it).
- **`timezone_signals`** — The single public singleton (no intermediate `_signals`
  variable). UI consumers (`UserModeView`, `AttendanceHistoryWidget`) connect to
  `timezone_signals.timezone_changed` to re-render their displays immediately when the
  user switches timezone — no restart required.
- **`set_timezone_config(tz_name: str | None) -> None`** — Configure the local timezone.
  Falls back to UTC when *tz_name* is empty or invalid (logs a warning). Emits
  `timezone_signals.timezone_changed(new_name)` iff the resolved timezone differs from the
  previous value. Uses the lazy `_load_zoneinfo()` helper to remain import-safe on Python
  < 3.9 (even though the project requires 3.11+). Catches `(KeyError, OSError, TypeError)`
  from `ZoneInfo(name)` on invalid names.
- **`get_timezone_name() -> str`** / **`get_timezone_config()`** — Getters for the current
  IANA name and the `zoneinfo.ZoneInfo` object respectively.
- **`format_tz_label(name: str) -> str`** — Format an IANA name as e.g.
  `"Asia/Ho_Chi_Minh (UTC+07:00)"`. Used by the Settings UI to render the timezone
  dropdown. Reuses `_load_zoneinfo()`. NOTE (pre-existing stdlib quirk):
  `ZoneInfo(name).utcoffset(None)` returns `None` for fixed-offset zones in stdlib
  `zoneinfo`, so the function currently returns the raw IANA name as the safe fallback;
  the UTC entry is the only one that renders an offset.
- **`_load_zoneinfo() -> type | None`** — Lazy helper that imports and returns
  `zoneinfo.ZoneInfo` if available, else `None`. Used by `set_timezone_config()` and
  `format_tz_label()`.
- **Storage convention** — All DB timestamps are stored as UTC ISO-8601 strings produced
  by `utc_now_iso()`.
- **Presentation helpers** — `utc_to_local()` and `local_now_iso()` convert to the
  configured local timezone for UI display. `local_to_utc()` does the reverse
  (e.g. for date-range filtering from a local-time picker).
- **Fail-safe** — Parse errors log a warning and return the input unchanged.

### `__init__.py`

Package docstring only (`"Utility functions for the attendance system."`); no
re-exports.

## Flow

```
main.py  ──set_timezone_config──▶  time_utils._tz
                                       │
             ┌─────────────────────────┼─────────────────────────┐
             ▼                         ▼                         ▼
     repositories/*.py          services/*.py               ui/*.py
     (utc_now_iso)              (utc_to_local)              (utc_to_local,
                                                              local_to_utc,
                                                              local_now_iso)

settings_widget.py ──set_timezone_config (on save)──▶  time_utils
                                                           │
                                                  emit timezone_changed
                                                           │
                                          ┌────────────────┴────────────────┐
                                          ▼                                 ▼
                                   user_mode_view.py            attendance_history_widget.py
                                   (re-render)                   (re-render)

camera_worker_base.py ──▶  _create_face_detector ──▶ face detection (YuNet)

ai_pipeline.py ──▶  _crop_face(scale=2.7) ──▶ liveness model
                    _crop_face(scale=1.5) ──▶ head-pose model  (enrollment only)

face_preprocessor.py ──▶  _crop_face(scale=config.scale) ──▶ model input tensor

enrollment_camera_thread.py ──▶  _crop_face(scale=2.7) ──▶ liveness model
```

## Integration

| Caller | What it uses |
|---|---|
| `core/storage_manager.py` | `utc_now_iso` for storage timestamps |
| `repositories/` (5 repos) | `utc_now_iso` for record timestamps |
| `services/attendance_service.py` | `utc_to_local` for display conversion |
| `services/ai_pipeline.py` | `_crop_face` (scale 2.7 for liveness, scale 1.5 default for head-pose) |
| `services/face_preprocessor.py` | `_crop_face` (scale from config) |
| `main.py` | `set_timezone_config` at startup (init) and at runtime (re-init via Admin UI save) |
| `ui/settings_widget.py` | `set_timezone_config` (on save), `format_tz_label` (dropdown display) |
| `ui/camera_worker_base.py` | `_create_face_detector` (face detection on every frame) |
| `ui/enrollment_camera_thread.py` | `_crop_face` (scale 2.7 for liveness), `_create_face_detector` (inherited from base) |
| `ui/user_mode_view.py` | `utc_now_iso`, `utc_to_local`; connects to `timezone_signals.timezone_changed` |
| `ui/attendance_history_widget.py` | `local_to_utc`, `utc_to_local`; connects to `timezone_signals.timezone_changed` |

## Key constants

- **`_crop_face` scale = 2.7** — used by attendance/enrollment liveness pipeline
- **`_crop_face` scale = 1.5 (default)** — used by head-pose estimation
