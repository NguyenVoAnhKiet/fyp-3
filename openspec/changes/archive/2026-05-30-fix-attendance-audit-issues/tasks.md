## 1. Add Session Status Validation

**Assign to: @fixer** (service layer code changes + UI error handling)

- [x] 1.1 Create `SessionClosedError` exception class in `src/attendance_system/services/exceptions.py`
- [x] 1.2 Add `_validate_session_active(session_id)` method to `AttendanceService` (checks session status = "active")
- [x] 1.3 Modify `record_success()` to call `_validate_session_active()` after `_validate_session_and_user()`
- [x] 1.4 Modify `record_duplicate()` to call `_validate_session_active()` after `_validate_session_and_user()`
- [x] 1.5 Modify `record_spoof_warning()` to call `_validate_session_active()` before inserting event
- [x] 1.6 Modify `record_unrecognized()` to call `_validate_session_active()` before inserting event
- [x] 1.7 Modify `UserModeView._on_recognition_result()` to catch `SessionClosedError` and show QMessageBox warning to user

## 2. Optimize Duplicate Detection Path

**Assign to: @fixer** (service layer optimization + query test)

- [x] 2.1 Refactor `record_success()` to catch `sqlite3.IntegrityError` internally (UNIQUE constraint) and branch to duplicate logic inline
- [x] 2.2 Remove the redundant `_validate_session_and_user()` call from `record_duplicate()` — validation now done once in record_success
- [x] 2.3 Remove the redundant event insertion from `record_duplicate()` — event already inserted in record_success before UNIQUE failure
- [x] 2.4 Simplify `record_duplicate()` to ONLY handle the fallback SELECT (fetch existing record_id) and optional event-linking
- [x] 2.5 Add test in `tests/unit/test_attendance_service.py` to verify duplicate path executes ≤6 SQL queries (use QueryCounter from test_attendance_audit.py)

## 3. Fix Empty Session Export

**Assign to: @fixer** (attendance_service.py export fix + test)

- [x] 3.1 Add empty-session check in `AttendanceService._export_session()` before building pandas DataFrame
- [x] 3.2 If empty (`len(records) == 0`), create an empty DataFrame with explicit column list: `[subject, class, date, name, student_id, status]`
- [x] 3.3 Write the empty DataFrame to CSV anyway (pandas will write headers even with zero rows)
- [x] 3.4 Add unit test `test_export_empty_session_produces_valid_csv` in `tests/unit/test_attendance_history_service.py` to verify CSV has proper headers

## 4. Fix Migration Error Handling

**Assign to: @fixer** (schema.py error handling + test)

- [x] 4.1 Locate `_migrate_attendance_records_cascade_to_setnull()` in `src/attendance_system/core/schema.py`
- [x] 4.2 Replace `except Exception: pass` with explicit error handling: log warning + re-raise
- [x] 4.3 Add `logger.warning(f"[MIGRATION] attendance_records CASCADE→SET_NULL failed: {type(exc).__name__}: {exc}")` with full exception details
- [x] 4.4 Re-raise the exception after logging (do NOT suppress — let app startup fail loudly)
- [x] 4.5 Update `initialize_database()` call site in `src/main.py` to catch and display error: show QMessageBox with migration error details
- [x] 4.6 Add integration test `test_attendance_records_migration_failure_logs_and_raises` in `tests/integration/test_database_init.py` to verify error is logged and re-raised

## 5. Add Callback Unit Tests

**Assign to: @fixer** (test file creation + test writing)

- [x] 5.1 Create new test file `tests/unit/test_attendance_callbacks.py` with pytest fixtures:
  - Mock `AttendanceService` using `unittest.mock.Mock`
  - Mock `CameraThread` or `UserModeView` as needed
  - Create helper to call `_on_recognition_result(...)` directly
- [x] 5.2 Add test `test_on_recognition_result_success_calls_record_success()` — emit "success" signal, verify `record_success()` was called with correct args
- [x] 5.3 Add test `test_on_recognition_result_duplicate_calls_record_duplicate()` — emit "duplicate" signal, verify `record_duplicate()` called
- [x] 5.4 Add test `test_on_recognition_result_spoof_calls_record_spoof_warning()` — emit "spoof" signal (user_id=None), verify `record_spoof_warning()` called
- [x] 5.5 Add test `test_on_recognition_result_unrecognized_calls_record_unrecognized()` — emit "unrecognized" signal, verify `record_unrecognized()` called
- [x] 5.6 Add test `test_on_recognition_result_catches_service_exception()` — mock service to raise exception, verify callback logs warning and does not crash
- [x] 5.7 Add test `test_on_recognition_result_catches_session_closed_error()` — mock service to raise `SessionClosedError`, verify callback shows error message (or logs)

## 6. Integration Testing

**Assign to: myself (orchestrator)** (run tests, verification, manual testing coordination)

- [x] 6.1 Run full test suite: `pytest tests/ -v` — all tests must pass
- [x] 6.2 Verify all 5 original audit feedback-loop tests now pass:
  - `tests/unit/test_attendance_audit.py::test_record_success_rejects_closed_session` ✓
  - `tests/unit/test_attendance_audit.py::test_camera_thread_on_recognition_result_creates_record` ✓
  - `tests/unit/test_attendance_audit.py::test_attendance_records_migration_silent_failure` ✓
  - `tests/unit/test_attendance_audit.py::test_export_empty_session_produces_valid_csv` ✓
  - `tests/unit/test_attendance_audit.py::test_duplicate_path_query_count` ✓
- [x] 6.3 Run linter: `ruff check src/` — no errors
- [x] 6.4 Manual test (UI): start session → recognize same user twice → verify only 1 attendance record created (no exception thrown to user) ✅ Fixed
- [x] 6.5 Manual test (UI): start session → close session → attempt to recognize user → verify SessionClosedError is caught and user sees warning dialog ✅ No popup (camera stops first) + no crash
- [x] 6.6 Manual test (UI): create and close empty session (no attendees) → export → verify CSV file has headers even though no data rows ✅ Fixed

## 7. Cleanup & Documentation

**Assign to: myself (orchestrator)** (review, finalize, commit)

- [x] 7.1 Search codebase for debug logs/prints added during implementation: `grep -r "\[DEBUG" src/ tests/` — remove all tagged debug lines
- [x] 7.2 Update docstrings in `AttendanceService` class and public methods to document that `SessionClosedError` can be raised
- [x] 7.3 Update `AGENTS.md` in "Gotchas" or "Known Issues" section: "Migration errors are now logged explicitly (no silent failures)"
- [x] 7.4 Commit with message:
  ```
  fix: attendance audit issues A-E (status guard, migration, callbacks, export, duplicate)
  
  - Add session-status validation: reject records in closed sessions (SessionClosedError)
  - Improve migration error handling: log and re-raise instead of silent suppression
  - Add callback unit tests: isolated test seams for _on_recognition_result() flow
  - Fix empty-session export: produce valid CSV with headers even for zero records
  - Optimize duplicate path: reduce query count from 9 to ≤6 by moving check earlier
  ```
