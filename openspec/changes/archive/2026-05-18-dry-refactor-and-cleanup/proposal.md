## Why

The codebase contains repeated validation logic in `attendance_service.py`, duplicated export methods (CSV vs Excel), and redundant cryptography import handling in `face_reference_repository.py`. These violations of DRY increase maintenance burden and risk of inconsistent behavior. Additionally, stale bug-fix comments and ambiguous similarity scores reduce code clarity.

## What Changes

- **Consolidate validation**: Extract shared session/user validation from `record_success` and `record_duplicate` into a private `_validate_session_and_user()` helper in `attendance_service.py`
- **Consolidate export**: Merge `export_session_to_csv` and `export_session_to_excel` into a single `_export_session(session_id, file_path, format)` method in `attendance_service.py`
- **Consolidate encryption imports**: Extract repeated `cryptography.fernet` import logic into a `_get_fernet()` helper in `face_reference_repository.py`
- **Remove unused parameter**: Delete dead `raw_image_path` parameter from `save_face_reference()` in `enrollment_service.py`
- **Clean stale comments**: Remove "Bug 1 fix" comment in `enrollment_camera_thread.py`
- **Clarify spoof score**: Change similarity score from `0.0` to `None` when spoof detected in `camera_thread.py`

## Capabilities

### New Capabilities
<!-- No new capabilities - this is internal refactoring only -->

### Modified Capabilities
<!-- No requirement changes - behavior remains identical -->

## Impact

- `src/attendance_system/services/attendance_service.py` — validation and export refactoring
- `src/attendance_system/services/enrollment_service.py` — remove dead parameter
- `src/attendance_system/repositories/face_reference_repository.py` — encryption import consolidation
- `src/attendance_system/services/enrollment_camera_thread.py` — comment cleanup
- `src/attendance_system/services/camera_thread.py` — similarity score clarification

No public API changes. No breaking changes. All behavior preserved.
