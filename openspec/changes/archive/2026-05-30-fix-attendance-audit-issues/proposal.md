## Why

The attendance feature has 5 issues (found via systematic audit) that threaten data integrity, user experience, and code maintainability:

1. **Data integrity**: Records can be written to closed sessions (no status guard)
2. **Silent failures**: Migration errors are swallowed, risking data loss
3. **Untested callback**: The UI-to-service bridge (`_on_recognition_result`) has no test coverage
4. **UX degradation**: Empty session exports produce invalid CSV files
5. **Performance waste**: Duplicate recognition triggers 9 SQL queries instead of 6

These issues compound when the system scales (100+ users, 1000+ attendance records per session).

## What Changes

- Add **session-status validation**: `record_success()` and `record_duplicate()` now reject operations on closed sessions with `SessionClosedError`
- Add **migration error logging**: Replace silent `except Exception: pass` with explicit error logging and re-raise
- Add **callback unit tests**: Create test seams for `_on_recognition_result()` flow to prevent regressions
- Fix **empty session export**: Add validation to produce proper CSV headers even when zero records
- Optimize **duplicate path**: Reduce query count from 9 to 6 by moving duplicate-detection earlier in the flow

Breaking changes: `SessionClosedError` exception now raised (handlers must catch it).

## Capabilities

### New Capabilities
- `session-status-guard`: Session-status validation in record methods (reject closed sessions)
- `migration-error-handling`: Explicit error logging for migration failures
- `callback-test-seams`: Unit test infrastructure for `_on_recognition_result()` callback

### Modified Capabilities
- `attendance-records`: Now validates session status before writing; raises `SessionClosedError`
- `attendance-export`: Empty sessions now produce valid CSV structure
- `duplicate-detection`: Optimized to reduce query overhead

## Impact

**Code**:
- `src/attendance_system/services/attendance_service.py`: Add `_validate_session_active()`, modify `record_success()` / `record_duplicate()`
- `src/attendance_system/core/schema.py`: Improve migration error handling (add logging)
- `src/attendance_system/ui/camera_thread.py`: Add test seams (mocking helpers)
- `tests/unit/test_attendance_service.py`: Add new tests for status validation
- `tests/unit/test_attendance_callbacks.py`: New test file for `_on_recognition_result()` flow

**APIs**:
- `AttendanceService.record_success()`: Now raises `SessionClosedError` if session is closed

**Tests**:
- 5 new unit tests (session status, duplicate optimization, empty export, callback, migration)

**Data**:
- No schema changes; behavior change only
