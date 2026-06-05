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

### Q1. Wrapper vs `@invalidate_cache` decorator vs proxy class?

- **Decision:** Use an explicit **wrapper class** `CachingFaceReferenceRepository` that holds a `FaceReferenceRepository` and intercepts reads/writes.
- **Rationale:** The codebase has no existing decorator convention in the repository layer, and decorators on a 184-line class would split the invalidation contract across two places (the decorator definition and the method it wraps). A wrapper is the only option that makes the seam **grep-able** — `grep -r FaceReferenceRepository src/` shows every consumer, and switching from `FaceReferenceRepository` to `CachingFaceReferenceRepository` is a one-line composition-root change. The wrapper also has a natural home for the new public `invalidate(user_id=None)` method that tests can call directly.
- **Trade-offs:** Slightly more code than a decorator (a thin class with ~10 delegating methods), and one extra object on the hot path (negligible — the wrapper holds a reference, not a copy).

### Q2. Port interface + two adapters, or just the wrapper?

- **Decision:** **No port interface.** The wrapper itself is the seam; the inner `FaceReferenceRepository` and the outer `CachingFaceReferenceRepository` already give us "two adapters" in the LANGUAGE.md sense (pure DB adapter vs. cached adapter).
- **Rationale:** A `FaceReferenceCache` protocol would only be justified by a *second* non-caching consumer that needs to be substituted in tests. The codebase has none — tests use the real DB via the `database` fixture, and the wrapper can already be bypassed by injecting `FaceReferenceRepository` directly. Per `LANGUAGE.md` "one adapter means a hypothetical seam" we skip the protocol. If a second no-op adapter ever appears (e.g. async caching), it can be extracted then.
- **Trade-offs:** Slightly less testability for the wrapper in isolation (must stub the inner repo via a fake subclass rather than a protocol). Mitigated by writing the wrapper against a thin `Protocol` in the test file, not a project-wide interface.

### Q3. Transaction boundary for `save_face_references`?

- **Decision:** **One transaction.** Add a new repository method `save_enrollment(user_id, pose_embeddings, model_name, vector_length)` on `FaceReferenceRepository` that atomically performs DELETE + 5 INSERTs into `face_references` + UPDATE `users.face_registered`. `EnrollmentService.save_face_references` becomes a one-liner that delegates to it. The wrapper intercepts this method too and invalidates the cache after the call returns.
- **Rationale:** The existing `test_enrollment_atomic_rollback_on_failure` (in `tests/unit/test_enrollment_and_settings_unit.py`) monkeypatches `enrollment.references._encrypt_embedding` and asserts rollback — a hard contract. Keeping the SQL inside the repo (where `_encrypt_embedding` lives) preserves the seam, and folding the `users.face_registered` UPDATE into the same `with self.connection() as conn:` block as the `replace_all` body keeps the existing atomicity guarantee with no behaviour change. A single repository method is preferable to exposing a `transaction()` context manager + cross-repo orchestration, which would re-leak SQL to the service.
- **Trade-offs:** `FaceReferenceRepository` gains a method that touches the `users` table, which is a slight scope-creep from "face references" into "users". Mitigated by naming (`save_enrollment`, not `replace_all`) and by the test pinning the contract.

### Q4. Contract test for invalidation invariant?

- **Decision:** **Yes, two layers.** (1) Unit test `tests/unit/test_caching_face_reference_repository.py` with a **stub inner repo** that proves the wrapper invalidates after every write method (parametrized over `upsert`, `replace_all`, `delete_by_user_id`, `save_enrollment`) and serves fresh data on the next read. (2) Integration test `tests/integration/test_face_reference_cache_invalidation.py` with a real DB that proves end-to-end freshness (enroll → identify → re-enroll → identify returns new embedding).
- **Rationale:** The unit test pins the wrapper's *own* discipline without coupling to the real repo. The integration test pins the full seam (wrapper + inner repo + SQL + Fernet). Together they catch both "wrapper forgot to invalidate" and "inner repo's SQL produced unexpected state". The unit test uses a stub (not a mock) so it also documents the expected call sequence.
- **Trade-offs:** ~2 new test files, ~150 lines total. Justified because the invariant we're enforcing is the whole point of the plan.

### Q5. Does the cache earn its keep at all?

- **Decision:** **Yes, keep the cache.** Promote it from a class-level hack to the explicit wrapper.
- **Rationale:** `FaceRecognizer.identify` calls `self._face_refs.get_all()` **once per face per AI frame** with `_AI_FRAME_SKIP = 3` (≈10 Hz). At 100 enrolled users × 5 poses = 500 rows, each call does 500 Fernet decryptions (when `FACE_EMBEDDING_FERNET_KEY` is set) plus a `SELECT * FROM face_references`. That's ~5 000 decryptions/sec on a single thread — a measurable hot path. Removing the cache would be a perf regression; the plan's Non-Goals ("No changes to the AI pipeline that consumes the cache") already presupposes it stays. The wrapper turns the cache from a *risk* (forget-to-invalidate) into a *property of one class* (the wrapper's responsibility alone).
- **Trade-offs:** We carry the wrapper's complexity. Worth it because the alternative (no cache, or a buggy cache) is worse than the cost of one ~80-line file.

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

## Task Breakdown

The plan divides into 9 tasks, sequenced for parallelism. Sub-agent routing follows the project `AGENTS.md` orchestrator rules: discovery → `@explorer`; bounded implementation → `@fixer`; final review → `@oracle`. No UI work (`@designer`) and no external library research (`@librarian`) needed.

### Task 1: Discovery — all consumers of `FaceReferenceRepository` and `get_all()` — @explorer
- **File(s):** (read-only) `src/`, `tests/`
- **Depends on:** none
- **Spec:**
  - Produce a list of every site that constructs `FaceReferenceRepository(...)` and every site that calls `.get_all()` / `.upsert()` / `.replace_all()` / `.delete_by_user_id()`.
  - Flag any consumer that opens its own transaction against `face_references` (would race with the wrapper's invalidation).
  - Flag any consumer whose constructor signature must change (FaceRecognizer, EnrollmentService, UserManagementWidget).
- **Verification:** Markdown table grouped by file:line, with method name and a one-line risk note. No code changes.
- **Parallel-safe:** yes

### Task 2: Strip caching from the base repository — @fixer
- **File(s):** `src/attendance_system/repositories/face_reference_repository.py`
- **Depends on:** Task 1
- **Spec:**
  - Remove the `_cache_all: ClassVar[...]` attribute (lines 17-21).
  - Remove the `_invalidate_cache` classmethod (lines 177-179).
  - Remove the `_invalidate_cache(...)` calls inside `upsert` (line 85), `replace_all` (line 151), and `delete_by_user_id` (line 184).
  - Make `get_all()` (lines 153-175) a pure DB read (no cache lookup or populate).
  - The repo is now a pure adapter: encrypt/decrypt + SQL + validation.
- **Verification:** `ruff check src/attendance_system/repositories/` passes; existing test suite still passes (cache is the only thing removed; behaviour unchanged when nothing caches).
- **Parallel-safe:** yes (with Tasks 3 and 4)

### Task 3: Create `CachingFaceReferenceRepository` wrapper — @fixer
- **File(s):** `src/attendance_system/repositories/caching_face_reference_repository.py` *(new)*
- **Depends on:** Task 2
- **Spec:**
  - Class `CachingFaceReferenceRepository` with constructor `(inner: FaceReferenceRepository)`.
  - Instance attribute `_cache: dict[str, list[dict[str, Any]] | None]` keyed by database path (replaces the class-level dict).
  - Wrap read methods (`get_all`, `get_by_user_id`, `get_by_user_id_and_pose`): consult cache, fall through to `inner`, populate cache.
  - Wrap write methods (`upsert`, `replace_all`, `delete_by_user_id`, `save_enrollment`): delegate to `inner`, then call `self._invalidate(str(self.database.config.path))` on success. Never invalidate on exception.
  - Public `invalidate(user_id: int | None = None) -> None` method for tests.
  - Pass-through for any other attribute via `__getattr__` to `inner` (or delegate explicitly — pick one and document it).
- **Verification:** New unit test file from Task 7 passes; existing tests pass (wrapper not yet wired in, no behaviour change at call sites).
- **Parallel-safe:** yes (with Task 4)

### Task 4: Add `save_enrollment` atomic method to the base repo — @fixer
- **File(s):** `src/attendance_system/repositories/face_reference_repository.py`
- **Depends on:** Task 2
- **Spec:**
  - New method `save_enrollment(self, user_id, pose_embeddings, model_name, vector_length)` that, in a single `with self.connection() as conn:` block, executes: DELETE from `face_references` WHERE user_id, 5 INSERTs (encrypted), UPDATE `users` SET `face_registered=1`, `updated_at=...` WHERE id=user_id. Validates inputs identically to current `save_face_references` (positive ints, non-empty embeddings, all 5 pose labels present).
  - Uses `self._encrypt_embedding` (now safe — it's the repo's own method).
  - `replace_all` stays as-is (still used by the wrapper for direct pose-only writes if any caller needs it; deprecate later if unused).
- **Verification:** Existing `test_enrollment_atomic_rollback_on_failure` still passes after Task 5 updates the service to call the new method. The test must be updated to monkeypatch the new location (e.g. `enrollment.references._encrypt_embedding` still works because the new method calls it internally).
- **Parallel-safe:** yes (with Task 3)

### Task 5: Refactor `EnrollmentService` to delegate — @fixer
- **File(s):** `src/attendance_system/services/enrollment_service.py`, `tests/unit/test_enrollment_and_settings_unit.py`
- **Depends on:** Task 4
- **Spec:**
  - Constructor: `__init__(self, database, references: FaceReferenceRepository | None = None)`. Default to `FaceReferenceRepository(database)` for backward-compat with tests that don't pass a repo.
  - `save_face_references` body shrinks to: validate inputs, call `self.references.save_enrollment(user_id, pose_embeddings, model_name, vector_length)`.
  - Delete the duplicated SQL block (lines 49-79) and the manual `_invalidate_cache` call (line 81).
  - Update the rollback test: instead of monkeypatching `_encrypt_embedding` on the service's `references`, monkeypatch the inner repo's `_encrypt_embedding` (still works because the service now calls the repo's method, which calls `_encrypt_embedding`).
  - Add a new assertion: `enrollment.references._encrypt_embedding` was called 5 times (one per pose) before the simulated failure.
- **Verification:** `pytest tests/unit/test_enrollment_and_settings_unit.py -v` and `pytest tests/integration/test_settings_and_enrollment_integration.py -v` both pass.
- **Parallel-safe:** yes (with Task 6)

### Task 6: Wire wrapper into the composition root — @fixer
- **File(s):** `src/main.py`, `src/attendance_system/services/ai_pipeline.py`, `src/attendance_system/ui/user_management_widget.py`
- **Depends on:** Task 3
- **Spec:**
  - In `main.py` (around line 173), construct the wrapper once: `face_refs = CachingFaceReferenceRepository(FaceReferenceRepository(db))`.
  - Pass it into `FaceRecognizer` via a new optional kwarg `face_refs=face_refs`.
  - Pass it into `EnrollmentService` via the new optional kwarg in Task 5.
  - Pass it into `UserManagementWidget` — the widget currently constructs its own `FaceReferenceRepository(database)` for user removal (`delete_by_user_id`). Inject the wrapper so user-delete from the admin UI also invalidates the cache. Without this, the recognizer could still match a deleted user until the next app restart — the exact stale-cache bug this plan exists to prevent.
  - In `ai_pipeline.py`, change `FaceRecognizer.__init__` to `def __init__(self, database, model_path=None, face_refs=None)`. If `face_refs is None`, default-construct `FaceReferenceRepository(database)` so existing tests stay green.
  - `self._face_refs = face_refs` (replaces the current internal construction).
- **Verification:** `python -c "from attendance_system.main import build_parser"` imports cleanly; `pytest tests/unit/test_ai_pipeline.py -v` passes (uses default repo, no wrapper); manual smoke (run the app, enroll a user, identify, re-enroll with new samples, identify again, delete the user, identify returns no match).
- **Parallel-safe:** yes (with Task 5)

### Task 7: Unit tests for the wrapper — @fixer
- **File(s):** `tests/unit/test_caching_face_reference_repository.py` *(new)*
- **Depends on:** Tasks 3, 5, 6
- **Spec:**
  - Parametrized contract test `test_every_write_invalidates_cache` over the 4 write methods (`upsert`, `replace_all`, `delete_by_user_id`, `save_enrollment`). For each: populate cache via a stub inner repo, invoke the wrapper method, assert the next read goes back to the inner.
  - `test_get_all_caches_after_first_call` — first call hits inner, second call does not.
  - `test_read_after_write_returns_fresh_data` — populate cache, call a write method, call `get_all`, assert it calls inner again.
  - `test_invalidate_public_method_works` — for tests that need to clear the cache without going through a write.
  - `test_wrapper_passes_through_to_inner_for_unwrapped_methods` — at minimum, verify `get_by_user_id` and `get_by_user_id_and_pose` delegate.
  - Use a `StubFaceReferenceRepository` (lightweight fake, not a MagicMock) that records call counts — easier to read on failure.
- **Verification:** `pytest tests/unit/test_caching_face_reference_repository.py -v` passes; `ruff check tests/unit/test_caching_face_reference_repository.py` passes.
- **Parallel-safe:** yes (with Task 8)

### Task 8: Integration test for end-to-end invalidation — @fixer
- **File(s):** `tests/integration/test_face_reference_cache_invalidation.py` *(new)*
- **Depends on:** Tasks 5, 6
- **Spec:**
  - `test_enrollment_then_identify_recognizes_user` — enroll user A with embedding bytes X, build wrapper + `FaceRecognizer`, call `identify` returns user A.
  - `test_reenrollment_invalidates_cache` — same as above, then re-enroll user A with embedding bytes Y (different), call `identify` returns user A with the new embedding bytes (proves stale cache was dropped).
  - `test_delete_user_invalidates_cache` — enroll two users, delete one via `delete_by_user_id` on the wrapper, call `identify` only matches the remaining user.
  - Uses the real `database` fixture (no mocks). May need to seed a user with `UserRepository` first.
- **Verification:** `pytest tests/integration/test_face_reference_cache_invalidation.py -v` passes; `pytest tests/integration/ -v` (full integration suite) still passes.
- **Parallel-safe:** yes (with Task 7)

### Task 9: Final architecture review — @oracle
- **File(s):** (read-only review of the full diff on branch `refactor/source-code`)
- **Depends on:** Tasks 7, 8
- **Spec:**
  - Verify the wrapper is the **only** code that touches the cache (grep for `_cache_all` and `_invalidate_cache` — should appear in one file only).
  - Verify no consumer of `FaceReferenceRepository` still constructs the inner class for hot-path use (they should accept the wrapper or a repo protocol).
  - Verify the `AGENTS.md` "Gotcha" line about "every write path must invalidate cache" is now **removable** (and propose the edit in the review).
  - Verify transaction boundaries: `save_enrollment` is the only multi-table writer, and it's atomic.
  - Check that `test_enrollment_atomic_rollback_on_failure` still expresses the original intent (mid-transaction failure → no commit).
  - Flag any seam that could be removed (YAGNI pass).
- **Verification:** Review summary document; approve or request changes.
- **Parallel-safe:** no (terminal review)

### Execution order

```
T1 (explorer) ──┬──► T2 (strip base) ──┬──► T3 (wrapper) ──────────────────────┐
                │                       │                                       │
                │                       └──► T4 (save_enrollment) ──► T5 (service) ┤
                │                                                                  ├─► T7 (unit tests) ──► T9 (review)
                │                                                                  └─► T8 (integration) ──┘
                │                       T6 (composition root) ─────────────────────┘
                │                       (needs T3; pairs with T5)
```

Parallel fans:
- **Wave 1:** T1 alone (~5 min, fast discovery).
- **Wave 2 (after T1):** T2 and T4 both edit `face_reference_repository.py` — run them **sequentially** (T2 first, then T4 on the stripped file). T3 can run **in parallel with T4** (different files).
- **Wave 3 (after T2 + T3):** T5 needs T4; T6 needs T3. T5 and T6 can run **in parallel** (different files).
- **Wave 4 (after T5 + T6):** T7 and T8 run **in parallel** (different test files, independent fixtures).
- **Wave 5:** T9 runs alone after T7 + T8.

Total critical path: T1 → T2 → T4 → T5 → T7 → T9 (≈ 6 task-slots deep). Parallelism cuts ~2-3 task-slots off a fully-sequential run.

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
