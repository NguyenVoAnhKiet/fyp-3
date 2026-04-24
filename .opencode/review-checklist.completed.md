# Review Checklist - Prioritized Fixes (Filtered)

## HIGH Priority (Fix Now)

- [x] **ISSUE-1**: Add session existence validation before recording attendance
  - Location: `src/services/attendance_service.py:44-46`
  - Fix: Check session exists before allowing attendance record creation

- [x] **ISSUE-2**: Add user existence validation before recording attendance
  - Location: `src/services/attendance_service.py:44-46`
  - Fix: Check user exists before allowing attendance record creation

- [x] **ISSUE-3**: Add `end_session()` or `finalize_session()` function
  - Location: `src/services/attendance_service.py`
  - Fix: Wrapper to close session and set end_time

## MEDIUM Priority

- [x] **ISSUE-4**: FaceReferenceRepository returns modified dict instead of sqlite3.Row
  - Location: `src/repositories/face_reference_repository.py:64-70`
  - Fix: Simplified conversion, added return type hint
  - Status: FIXED

- [x] **ISSUE-5**: Non-atomic `correct()` method - uses separate connections
  - Location: `src/repositories/attendance_repository.py:54-72`
  - Fix: Use single transaction for both read and update

---

## Previously Completed (Reference Only)

- [x] **S-1**: Add input validation on SQL parameters in all repositories
- [x] **S-2**: Sanitize database path (prevent `..` in path)
- [x] **B-1**: Fix race condition in duplicate attendance check
- [x] **BUG**: Add transaction wrapping in `AttendanceService.record_success()`
- [x] **S-3**: Add password strength validation
- [x] **S-4**: Add rate limiting for admin credential creation
- [x] **S-5**: Consider database encryption for face embeddings
- [x] **CODE**: Extract duplicate `_utc_now()` to shared utility
- [x] **BUG**: Update `created_at` on face_reference upsert
- [x] **TEST**: Add negative test cases
- [x] **TEST**: Add security tests for SQL injection