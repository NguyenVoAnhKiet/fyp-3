## Context

The codebase has two remaining DRY violations in camera-related modules:
1. **`_crop_face` function duplication**: Both `camera_thread.py` and `enrollment_camera_thread.py` contain identical `_crop_face` implementations
2. **Detector initialization repeated**: `cv2.FaceDetectorYN.create` is called in multiple places without centralization

Additionally, minor cleanup items from the refactoring plan remain:
- Inconsistent `__init__.py` docstrings across packages
- Hardcoded font name without fallback
- Missing explanation for bootstrap.py not calling load_dotenv()

## Goals / Non-Goals

**Goals:**
- Extract `_crop_face` to `src/attendance_system/utils/face_utils.py` for reuse
- Create detector factory method in `utils/` to centralize FaceDetectorYN initialization
- Add consistent docstrings to all `__init__.py` files
- Implement font fallback chain in `constants.py`
- Add explanatory comment to `bootstrap.py`

**Non-Goals:**
- Do NOT change any business logic or public APIs
- Do NOT add new features or capabilities
- Do NOT modify any existing test behavior

## Decisions

1. **`_crop_face` location**: Place in `utils/face_utils.py` - existing utility file for face-related helpers
2. **Detector factory**: Create `_create_face_detector()` function in `utils/face_utils.py` that accepts config parameters, import and call from `main.py`, pass to camera threads via constructor
3. **Font fallback**: Use QFont fallback chain: "JetBrains Mono" → "Consolas" → "Courier New" → system default
4. **`__init__.py` docstrings**: Use format "Package for <purpose>" - e.g., "Core storage utilities."

## Risks / Trade-offs

- **Risk**: Changing camera thread constructor signature could break existing code - **Mitigation**: Keep backward compatible, add detector as optional parameter with default creation
- **Risk**: Font change could affect UI appearance - **Mitigation**: Fallback chain is conservative, only adds more options
- **Trade-off**: Slight increase in coupling via shared utility - **Benefit**: Single source of truth for face processing logic

All changes are safe, non-breaking refactoring.
