# src/attendance_system/utils/

## Responsibility

General-purpose utility/helper functions shared across the application. Contains two
independent modules — one for face-image manipulation (cropping, detection setup) and
one for timezone-aware datetime formatting.

## Design

### `face_utils.py`

Exposes two low-level helpers consumed exclusively by camera and AI worker threads:

- **`_crop_face(frame, bbox, scale=1.5)`** — Squares and pads a face bounding box by
  a multiplier so downstream models see consistent regions. The default `scale=1.5` is
  used by head-pose estimation; callers override to **`2.7`** for the liveness
  sub-pipeline in both attendance and enrollment paths.
- **`_create_face_detector(model_path, input_size, score_threshold, nms_threshold)`** —
  Factory wrapper around `cv2.FaceDetectorYN.create` (YuNet ONNX model). Returns a
  ready-to-use detector; all parameters are caller-supplied (no defaults live here
  except reasonable YuNet defaults).

Both functions are prefixed with `_` (module-private by convention) but are imported
directly by three ui/ workers and one service, so they are effectively package-internal
APIs.

### `time_utils.py`

A thin timezone layer built on Python's `zoneinfo` (stdlib ≥ 3.9) with a UTC fallback.

- **Module-level `_tz`** — Defaults to `timezone.utc`. Initialised once at startup by
  `set_timezone_config(tz_name)` called from `main.py`.
- **Storage convention** — All DB timestamps are stored as UTC ISO-8601 strings
  produced by `utc_now_iso()`.
- **Presentation helpers** — `utc_to_local()` and `local_now_iso()` convert to the
  configured local timezone for UI display. `local_to_utc()` does the reverse
  (e.g. for date-range filtering from a local-time picker).
- **Fail-safe** — Parse errors log a warning and return the input unchanged.

### `__init__.py`

Empty — this package does not re-export anything.

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

camera_thread.py ──▶  _crop_face(scale=2.7)  ──▶ liveness model
enrollment_camera   ──▶  _crop_face(scale=2.7)  ──▶ liveness model
enrollment_ai_worker──▶  _crop_face(scale=2.7)  ──▶ liveness model
head_pose_worker    ──▶  _crop_face(scale=1.5)  ──▶ head-pose model
```

## Integration

| Caller | What it uses |
|---|---|
| `core/storage_manager.py` | `utc_now_iso` for storage timestamps |
| `repositories/` (6 repos) | `utc_now_iso` for record timestamps |
| `services/attendance_service.py` | `utc_to_local` for display conversion |
| `main.py` | `set_timezone_config` once at startup |
| `ui/camera_thread.py` | `_crop_face` (scale 2.7 for liveness), `_create_face_detector` |
| `ui/enrollment_camera_thread.py` | `_crop_face` (scale 2.7), `_create_face_detector` |
| `ui/enrollment_ai_worker.py` | `_crop_face` (scale 2.7) |
| `ui/user_mode_view.py` | `utc_now_iso`, `utc_to_local` |
| `ui/attendance_history_widget.py` | `local_to_utc`, `utc_to_local` |

## Key constants

- **`_crop_face` scale = 2.7** — used by attendance/enrollment liveness pipeline
- **`_crop_face` scale = 1.5 (default)** — used by head-pose estimation
