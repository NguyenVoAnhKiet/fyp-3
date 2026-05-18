## Why

The codebase contains dead/zombie code that increases maintenance burden and a hardcoded admin password (`admin`/`admin`) that bypasses the `.env.example` configuration already provided. These are P0 issues: dead code creates confusion during onboarding and code navigation, while the hardcoded credential is a security risk even for a desktop app.

## What Changes

- **Remove** `src/attendance_system/services/security.py` — zero imports across the project (entirely unreferenced)
- **Remove** unused `raw_image_path` parameter from `save_face_reference()` in `enrollment_service.py` and its caller in `enrollment_widget.py`
- **Remove** unused `import sqlite3` from `admin_repository.py`
- **Fix** hardcoded admin credentials in `storage_manager.py` to read from `ADMIN_USERNAME`/`ADMIN_PASSWORD` environment variables (already defined in `.env.example` but never used)
- **Remove** "Bug 1 fix" stale comment from `enrollment_camera_thread.py`

## Capabilities

### New Capabilities
- `admin-credential-config`: Admin username/password loaded from environment variables instead of hardcoded values, with fallback to safe defaults

### Modified Capabilities
<!-- No existing specs to modify -->

## Impact

- `src/attendance_system/services/security.py` — deleted
- `src/attendance_system/services/enrollment_service.py` — signature change on `save_face_reference()` (removes `raw_image_path` param)
- `src/attendance_system/ui/enrollment_widget.py` — caller updated to match new signature
- `src/attendance_system/repositories/admin_repository.py` — unused import removed
- `src/attendance_system/core/storage_manager.py` — admin bootstrap reads from env vars
- `src/attendance_system/ui/enrollment_camera_thread.py` — comment removed
