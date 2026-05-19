## Why

The codebase still has duplicate code patterns (DRY violations) in the camera modules and minor cleanup items that were planned but not yet implemented. These remaining refactoring tasks improve maintainability without changing any business logic.

## What Changes

### Camera DRY (Nhóm 2.3, 2.4)
- **Extract `_crop_face` to shared utility**: Move identical `_crop_face` function from `camera_thread.py` and `enrollment_camera_thread.py` into `src/attendance_system/utils/face_utils.py`
- **Create detector factory**: Centralize `cv2.FaceDetectorYN.create` initialization via factory method or dependency injection from `main.py`

### Minor Cleanup (Nhóm 6)
- **Unify `__init__.py` docstrings**: Add consistent docstrings to all package `__init__.py` files
- **Add font fallback**: Add system font fallback chain in `constants.py` for JetBrains Mono
- **Document bootstrap.py**: Add comment explaining why `load_dotenv()` is not called in `bootstrap.py`

## Capabilities

### New Capabilities
<!-- No new capabilities - these are refactoring/internal improvements only -->
*(None - this is a pure refactoring change with no new features)*

### Modified Capabilities
<!-- No existing capability requirements changing -->
*(None)*

## Impact

- Refactored code in: `src/attendance_system/ui/camera_thread.py`, `src/attendance_system/ui/enrollment_camera_thread.py`, `src/attendance_system/utils/`, `src/attendance_system/core/`, `src/attendance_system/models/`, `src/attendance_system/services/`, `src/attendance_system/repositories/`, `bootstrap.py`
- No breaking changes - all refactoring preserves existing behavior
- No new dependencies
