## Context

The attendance system records when students check in during a session. The audit (Phase 1-2) identified 5 bugs ranging from data integrity to performance.

**Current state:**
- Sessions can be closed, but `record_success()` and `record_duplicate()` don't check session status
- Duplicate recognition (same user in same session twice) triggers 9 SQL queries due to redundant validation
- Empty session exports produce invalid CSV (missing headers)
- Migration error handling is silent (`except Exception: pass`)
- The callback flow (`_on_recognition_result`) is untested, risking regressions

**Constraints:**
- SQLite with WAL mode — transactions are cheaper than in other DB systems
- Qt threading model — UI callbacks run on main thread; no true parallelism
- Backward compatibility — no schema changes allowed
- Test seams already exist (service layer, repository layer, fixtures)

## Goals / Non-Goals

**Goals:**
- Add session-status validation to `record_success()` and `record_duplicate()` — reject closed sessions early
- Reduce duplicate-path query count from 9 to 6 by moving duplicate-check earlier
- Fix empty-session export to produce valid CSV structure (or no output with proper logging)
- Replace silent migration error suppression with explicit logging
- Add unit test coverage for `_on_recognition_result()` callback

**Non-Goals:**
- Refactor the callback architecture (too risky; test seams are sufficient)
- Add database indices (separate performance task)
- Change export to use background threads (low-priority UI improvement)
- Implement session reopening (not a requirement)

## Decisions

### Decision 1: Session-status validation location
**Choice:** Validate in `record_success()` and `record_duplicate()`, after `_validate_session_and_user()` but before DB operations.

**Rationale:** 
- Fail fast — prevents wasted computation and DB queries
- Centralized validation — both success and duplicate paths checked uniformly
- Matches existing pattern (`_validate_session_and_user()` guards FK constraints)

**Alternative considered:**
- Validate in repository layer — finer granularity but scatters logic; not adopted

**Implementation:** Add `_validate_session_active(session_id)` method in `AttendanceService`.

---

### Decision 2: Duplicate-path optimization
**Choice:** Move duplicate-check into `record_success()` by catching `IntegrityError` locally; branch to `record_duplicate()` inline.

**Rationale:**
- Avoids re-validating (saves 2 SELECTs)
- Avoids redundant event insertion (both methods were inserting the event)
- Reduces from 9 queries to ~6 (4 for success path + 1 UNIQUE error + 1 fallback SELECT)

**Current flow:**
```
record_success() → INSERT event → INSERT attendance (fails) → throw → record_duplicate()
record_duplicate() → validate again → INSERT event → INSERT attendance (fails) → fallback SELECT
```

**New flow:**
```
record_success() → validate once → INSERT event → INSERT attendance (fails on UNIQUE) → catch → fallback SELECT
(no call to record_duplicate; branch handled inline)
```

**Alternative considered:**
- Leave as-is (two separate methods) — simpler but wasteful; not adopted

---

### Decision 3: Empty session export handling
**Choice:** Check `len(records) == 0` before processing; if empty, create an empty DataFrame with the expected columns (subject, class, date, name, student_id, status).

**Rationale:**
- Produces valid CSV structure (always has headers)
- Matches user expectation ("export this session" → valid file, even if empty)
- Minimal code change

**Alternative considered:**
- Return `None` and skip file write — confusing UX (user clicks export, nothing happens)
- Not adopted

---

### Decision 4: Migration error handling
**Choice:** Replace `except Exception: pass` with explicit error logging; then re-raise to fail loudly.

**Rationale:**
- Prevents silent data loss — if migration fails, app should not proceed
- Allows admins to diagnose (logs capture error details)
- Fails safely (app won't start with corrupted schema)

**Alternative considered:**
- Try migration, silently continue if fail (current) — dangerous; not adopted
- Log but don't re-raise — hides problem; not adopted

---

### Decision 5: Callback test seam strategy
**Choice:** Create unit tests for `_on_recognition_result()` by:
1. Mocking `AttendanceService` and `CameraThread`
2. Calling `_on_recognition_result(...)` directly with various inputs
3. Asserting service methods were called with correct args

**Rationale:**
- No need to refactor code (only add tests)
- Catches regressions in callback logic
- Fast (no real camera, DB calls are mocked)

**Alternative considered:**
- Integration test (spin up real camera + service) — too slow and fragile
- Not adopted

---

## Risks / Trade-offs

| Risk | Mitigation |
|------|-----------|
| **Breaking change: `SessionClosedError`** — code calling `record_success()` may not catch this exception. | Document clearly. Catch the exception in `_on_recognition_result()` and show UI error. Test it. |
| **Duplicate-path refactor could introduce subtle bugs** (e.g., transaction boundaries change). | Carefully test with 2 simultaneous duplicate recognitions (stress test). Verify query counts with test harness. |
| **Empty DataFrame column order** — if column names diverge from expected, export header mismatch. | Hardcode column order in code; document it. |
| **Migration error logging reveals internal schema** — could be security concern if logs are exposed. | Sanitize error messages; log only essential details. |
| **Callback tests use mocks** — may not catch issues that appear only with real Qt signals. | Add one integration test of full `CameraThread → UserModeView` flow (separate, lower priority). |

---

## Deployment

1. **Backward compatibility**: No schema changes; only behavior changes. Existing data unaffected.
2. **Rollback**: If `SessionClosedError` causes issues, wrap service calls in try-catch to log warnings instead of failing.
3. **Testing**: Run full test suite before deploying. Verify duplicate path with stress test (100 duplicate recognitions in 1 session).

## Open Questions

- Should `SessionClosedError` be user-facing (show dialog) or internal (just log)? → Decide in callback handler.
- Empty export: return empty DataFrame or skip file write? → Current choice: create valid CSV with zero data rows.
- Migration logging level: ERROR, WARNING, or INFO? → Recommend WARNING (schema migration is critical but not fatal yet).
