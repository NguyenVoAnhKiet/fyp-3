## 1. Remove dead code — `security.py`

- [ ] 1.1 Delete `src/attendance_system/services/security.py`
- [ ] 1.2 Run `ruff check src/` to confirm no broken imports
- [ ] 1.3 Run `pytest tests/` to confirm no test failures

## 2. Remove dead code — `raw_image_path` parameter

- [ ] 2.1 Remove `raw_image_path` parameter from `save_face_reference()` in `src/attendance_system/services/enrollment_service.py`
- [ ] 2.2 Remove the `if raw_image_path is not None` block in the same method
- [ ] 2.3 Update the caller in `src/attendance_system/ui/enrollment_widget.py:235` to remove the unused argument (already not passed, verify no change needed)
- [ ] 2.4 Run `ruff check src/` to confirm no issues

## 3. Remove dead code — unused `import sqlite3`

- [ ] 3.1 Remove `import sqlite3` from `src/attendance_system/repositories/admin_repository.py:2`
- [ ] 3.2 Run `ruff check src/` to confirm type hints still valid with `from __future__ import annotations`

## 4. Remove stale comment

- [ ] 4.1 Remove `# Bug 1 fix: Reset counter khi capture thất bại` from `src/attendance_system/ui/enrollment_camera_thread.py:249`

## 5. Fix hardcoded admin credentials

- [ ] 5.1 Update `_seed_admin()` in `src/attendance_system/core/storage_manager.py` to read `ADMIN_USERNAME` and `ADMIN_PASSWORD` from `os.getenv()` with fallback to `"admin"` / `"admin"`
- [ ] 5.2 Add `import os` to `storage_manager.py`
- [ ] 5.3 Run `ruff check src/` to confirm no issues
- [ ] 5.4 Run `pytest tests/` to confirm no test failures
