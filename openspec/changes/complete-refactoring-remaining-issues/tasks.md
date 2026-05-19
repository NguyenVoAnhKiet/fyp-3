## 1. Camera DRY - Extract _crop_face

- [ ] 1.1 Create `src/attendance_system/utils/face_utils.py` with `_crop_face` function copied from `camera_thread.py`
- [ ] 1.2 Update `camera_thread.py` to import and use `_crop_face` from `face_utils.py`
- [ ] 1.3 Update `enrollment_camera_thread.py` to import and use `_crop_face` from `face_utils.py`
- [ ] 1.4 Remove duplicate `_crop_face` implementation from `camera_thread.py`
- [ ] 1.5 Remove duplicate `_crop_face` implementation from `enrollment_camera_thread.py`
- [ ] 1.6 Run `ruff check src/` to verify no import errors

## 2. Camera DRY - Detector Factory

- [ ] 2.1 Add `_create_face_detector()` function to `face_utils.py`
- [ ] 2.2 Update `main.py` to call detector factory and pass to components
- [ ] 2.3 Update camera thread classes to accept detector as parameter (keep backward compatible with default creation)
- [ ] 2.4 Run tests to verify camera functionality works

## 3. Minor Cleanup - __init__.py Docstrings

- [ ] 3.1 Add docstring to `src/attendance_system/models/__init__.py`: "Data models for attendance system entities."
- [ ] 3.2 Add docstring to `src/attendance_system/ui/__init__.py`: "PyQt5 UI components for the attendance application."
- [ ] 3.3 Add docstring to `src/attendance_system/utils/__init__.py`: "Utility functions for the attendance system."

## 4. Minor Cleanup - Font Fallback

- [ ] 4.1 Update `src/attendance_system/ui/constants.py` to use font fallback chain: "JetBrains Mono", "Consolas", "Courier New"
- [ ] 4.2 Verify UI still renders correctly

## 5. Minor Cleanup - Bootstrap Comment

- [ ] 5.1 Add comment to `bootstrap.py` explaining why `load_dotenv()` is not called (see AGENTS.md)

## 6. Verification

- [ ] 6.1 Run `ruff check src/` to verify no lint errors
- [ ] 6.2 Run `pytest tests/unit/ -v` to verify all tests pass
- [ ] 6.3 Run `pytest tests/integration/ -v` to verify integration tests pass
