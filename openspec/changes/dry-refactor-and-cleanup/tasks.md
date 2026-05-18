## 1. Consolidate validation in attendance_service.py

- [ ] 1.1 Add `_validate_session_and_user(session_id: int, user_id: int) -> None` private method to `AttendanceService` that runs `require_positive_int` for both IDs, checks session existence (raises `LookupError`), and checks user existence (raises `LookupError`)
- [ ] 1.2 Update `record_success` to call `_validate_session_and_user(session_id, user_id)` instead of inline validation, keeping `require_non_empty_text(event_time, "event_time")` inline
- [ ] 1.3 Update `record_duplicate` to call `_validate_session_and_user(session_id, user_id)` instead of inline validation
- [ ] 1.4 Run `pytest tests/` to verify no regression in attendance recording

## 2. Consolidate export methods in attendance_service.py

- [ ] 2.1 Add `_export_session(session_id: int, file_path: str, format: str) -> None` private method that prepares the DataFrame, applies column selection/rename, and branches on format for `to_csv` vs `to_excel`
- [ ] 2.2 Update `export_session_to_csv` to delegate to `_export_session(session_id, file_path, "csv")`
- [ ] 2.3 Update `export_session_to_excel` to delegate to `_export_session(session_id, file_path, "excel")`
- [ ] 2.4 Run `pytest tests/` to verify no regression in export functionality

## 3. Consolidate cryptography import in face_reference_repository.py

- [ ] 3.1 Add `_get_fernet() -> Fernet | None` private method that returns `None` if no key, otherwise does the try/except import and returns `Fernet(self._fernet_key.encode("utf-8"))`
- [ ] 3.2 Update `_encrypt_embedding` to use `_get_fernet()` instead of inline try/except
- [ ] 3.3 Update `_decrypt_embedding` to use `_get_fernet()` instead of inline try/except
- [ ] 3.4 Run `pytest tests/` to verify no regression in face reference encryption

## 4. Remove dead code and clean up comments

- [ ] 4.1 Remove unused `raw_image_path` parameter from `save_face_reference()` in `enrollment_service.py` (no callers use it)
- [ ] 4.2 Remove "Bug 1 fix" comment in `enrollment_camera_thread.py` line ~249
- [ ] 4.3 Change similarity score from `0.0` to `None` in `camera_thread.py:208` spoof emission
- [ ] 4.4 Run `pytest tests/` to verify no regression

## 5. Final verification

- [ ] 5.1 Run `ruff check src/` to verify no lint errors
- [ ] 5.2 Run full test suite `pytest tests/ -v` and confirm all pass
