# Plan 0006: Enforce Cache Invalidation (`CachingFaceReferenceRepository`)

**Parent plan:** [0002 — Architecture Deepening Checklist](0002-architecture-deepening.md) (candidate #4).

## Status

**Draft** — design pending grilling. Surfaced by `improve-codebase-architecture` skill; see friction recap in parent plan.

## Context

`FaceReferenceRepository._cache_all: ClassVar[dict[str, list[dict]]]` is invalidated on every write path, but **by convention only**. `AGENTS.md` explicitly warns "every write path must invalidate cache" — no enforcement.

The convention is broken by `services/enrollment_service.py:50-81`, which:
- bypasses the repository's own `replace_all()` method
- duplicates the transaction logic
- reaches into `self.references._encrypt_embedding()` (a private method)
- calls `self.references._invalidate_cache()` manually after duplicating logic

**Cache-invalidation knowledge leaks out of the repository.** A new developer adding a `bulk_import()` method could easily forget to call `_invalidate_cache()`, silently serving stale face embeddings. No test verifies the invalidation invariant.

**4 write paths** that must invalidate:

1. `FaceReferenceRepository.upsert()` — invalidates ✅
2. `FaceReferenceRepository.replace_all()` — invalidates ✅
3. `FaceReferenceRepository.delete_by_user_id()` — invalidates ✅
4. `EnrollmentService.save_face_references()` — calls `_invalidate_cache()` manually ✅ (but duplicates `replace_all` logic)

## Goals

1. Cache invalidation is **enforced by invariant**, not by convention. Forgetting to invalidate is impossible.
2. `EnrollmentService` no longer reaches into private repository methods. The service layer and repository layer have a clean seam.
3. Cache becomes an **explicit pattern** (a `CachingFaceReferenceRepository` wrapper) rather than a class-level global on the base repository.
4. A contract test catches future "forgot to invalidate" regressions: for every write method, after the call, the cache returns fresh data.
5. Decision made on whether the cache earns its keep at all (Design Q5) — if not, delete it.

## Non-Goals

- No changes to the face embedding encryption format (Fernet).
- No changes to the `face_references` table schema.
- No migration of cached data.
- No new caching layers (e.g., recognition result caching) — scope is the face-references cache only.
- No changes to the AI pipeline that consumes the cache (`FaceRecognizer.identify` calling `get_all()`).

## Design Decisions

_To be filled by grilling session. Five design questions in scope:_

| # | Question | Constraints |
|---|----------|-------------|
| 1 | `CachingFaceReferenceRepository` wrapper vs `@invalidate_cache` decorator vs proxy class? | Wrapper is explicit and testable; decorator is implicit and harder to test; proxy is over-engineered. |
| 2 | Should the cache be moved to a port (`FaceReferenceCache` interface) with two adapters (caching, no-op)? | Per `LANGUAGE.md`: "one adapter = hypothetical seam, two adapters = real seam." Is the no-op adapter justified? |
| 3 | Does `EnrollmentService.save_face_references()` decompose into `replace_all()` + `users.face_registered = 1` in one transaction, or two? | Transaction boundaries matter. Partial-failure mode must be defined. |
| 4 | Should we add a contract test that catches future "forgot to invalidate" regressions? | Test: "for every write method, after the call, cache is empty for that user_id." |
| 5 | Does the cache belong at all? | `get_all()` could just hit the DB. Is the performance gain worth the invalidation risk? Empirical: how often does `identify()` call `get_all()`? |

## Implementation

### Files to change

| File | Change |
|------|--------|
| `src/attendance_system/repositories/face_reference_repository.py` | Remove class-level `_cache_all`. Keep all read/write methods pure (no caching). The repository is now a pure adapter to SQLite. |
| `src/attendance_system/repositories/caching_face_reference_repository.py` *(new)* | `CachingFaceReferenceRepository` wraps a `FaceReferenceRepository`. Intercepts writes and invalidates the cache for the affected `user_id` (or for all, conservatively). Reads consult cache first. |
| `src/attendance_system/services/enrollment_service.py` | `save_face_references()` calls `self.references.replace_all(...)` and updates `users.face_registered = 1` in a single transaction. No more private method access. The injected repository is the `CachingFaceReferenceRepository` wrapper. |
| `src/main.py` or service container | Construct the `CachingFaceReferenceRepository` wrapper and inject it into `FaceRecognizer` + `EnrollmentService` (and any other consumer of `get_all()`). |
| `tests/unit/test_caching_face_reference_repository.py` *(new)* | Test: `upsert()` invalidates; `replace_all()` invalidates; `delete_by_user_id()` invalidates. Read after write returns fresh data. |
| `tests/integration/test_face_reference_cache_invalidation.py` *(new)* | Contract test: for every write method, after the call, `get_all()` returns the new state. Runs against real SQLite (uses the `database` fixture). |
| `tests/unit/test_enrollment_service.py` *(new or extended)* | Test: `save_face_references()` calls `replace_all()` once, updates `users.face_registered` once, no direct `_encrypt_embedding` or `_invalidate_cache` calls. |

### Touch points by line (reference)

- `repositories/face_reference_repository.py:17-21` — class-level `_cache_all` definition
- `repositories/face_reference_repository.py:60-86` — `upsert` (currently invalidates)
- `repositories/face_reference_repository.py:119-151` — `replace_all` (currently invalidates)
- `repositories/face_reference_repository.py:181-184` — `delete_by_user_id` (currently invalidates)
- `services/enrollment_service.py:50-81` — `save_face_references` (currently bypasses `replace_all`, calls private methods)

## Testing

### Unit tests to add (in `test_caching_face_reference_repository.py`)

- `test_upsert_invalidates_cache_for_user` — populate cache, call `upsert`, cache empty.
- `test_replace_all_invalidates_cache_globally` — populate cache, call `replace_all`, cache empty.
- `test_delete_by_user_id_invalidates_cache_for_user` — populate cache, call `delete_by_user_id`, cache empty.
- `test_get_all_returns_cached_data_when_fresh` — first `get_all()` hits DB; second returns from cache (verify via mock or call count).
- `test_get_all_returns_fresh_data_after_write` — `get_all()`, write, `get_all()` reflects the write.
- `test_wrapper_passes_through_to_underlying_repository_for_other_methods` — non-cached methods delegate correctly.

### Integration tests to add (in `test_face_reference_cache_invalidation.py`)

- `test_contract_invariant_every_write_invalidates` — parametrized over all write methods. For each, populate cache, call the method, assert cache is empty.
- `test_real_db_invalidation_end_to_end` — populate cache with a real DB, modify the DB bypassing the wrapper, assert wrapper still serves stale data (this is intentional — the wrapper can only know about writes it sees; documents the limit).
- `test_enrollment_flow_does_not_stale_cache` — full enrollment flow (save_face_references), then identify via FaceRecognizer using the wrapper, assert new user is recognized.

### Unit tests to add or update (in `test_enrollment_service.py`)

- `test_save_face_references_calls_replace_all` — mock `repository.replace_all`, assert called once.
- `test_save_face_references_updates_face_registered_flag` — assert `users.face_registered = 1` after the call.
- `test_save_face_references_does_not_access_private_methods` — assert no calls to `repository._encrypt_embedding` or `repository._invalidate_cache` (use `mock.patch` with `assert_not_called`).
- `test_save_face_references_runs_in_single_transaction` — assert DB has the right state if a step in the middle fails (rollback).

### Manual smoke checklist

1. Enroll user A. Start attendance session. Verify: user A is recognized (cache populated).
2. Re-enroll user A with new face samples. Verify: user A is still recognized but with new embeddings (cache invalidated).
3. Delete user A from admin UI. Verify: user A is no longer recognized (cache invalidated).
4. With DB modified externally (sqlite3 CLI), restart the app. Verify: stale cache is gone after restart (cache is in-memory, keyed by DB path).
5. Manually corrupt the cache (set a wrong entry), call `get_all()`. Verify: wrapper detects the corruption or rebuilds (depending on Design Q1 decision).

### Verification commands

```bash
pytest tests/unit/test_caching_face_reference_repository.py -v
pytest tests/integration/test_face_reference_cache_invalidation.py -v
pytest tests/unit/test_enrollment_service.py -v
ruff check src/attendance_system/repositories/
```

## Related

- Parent plan: [0002 — Architecture Deepening Checklist](0002-architecture-deepening.md)
- Independent of [0003 — CameraWorkerBase](0003-camera-worker-base.md), [0005 — SystemConfig](0005-system-config-resolver.md).
- `AGENTS.md` "Gotchas" — `FaceReferenceRepository._cache_all` keyed by DB path; **every write path must invalidate cache**. (This gotcha may be removable after this plan.)
- `AGENTS.md` "Wiring" — `attendance_records.user_id` is nullable, `ON DELETE SET NULL`. LEFT JOIN required when joining `attendance_records` → `users`. (Indirectly relevant if cache miss leads to wrong user lookup.)
- Branch: `refactor/source-code`.
