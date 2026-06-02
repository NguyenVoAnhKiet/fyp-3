# Plan 0002: Architecture Deepening — Grilling 5 Candidates

## Status

**Draft** — design exploration in progress on branch `refactor/source-code`. Created after the `improve-codebase-architecture` skill's exploration phase surfaced 5 deepening opportunities (see `CONTEXT.md` for domain glossary and `.agents/skills/improve-codebase-architecture/LANGUAGE.md` for the architecture vocabulary — **module**, **interface**, **seam**, **adapter**, **leverage**, **locality**).

## Context

The codebase has reached the point where several modules are **shallow** (interface nearly as complex as the implementation) or **leaky across their seams** (services reach into repository privates, defaults hardcoded in N places, AI pipeline logic distributed across 6 files). A `Explore` sub-agent walked the codebase and produced a ranked friction report; the 5 top opportunities are tracked here in the order the user requested.

This plan is a **meta-plan**: it drives the `improve-codebase-architecture` skill's grilling loop through each candidate until we have a resolved design (and, where appropriate, a follow-up implementation plan). It is **not** itself the implementation plan for any refactor — each candidate, once grilled, may produce its own implementation plan (or an ADR that forecloses the refactor).

### Deletion test reminder

For every candidate we ask: *if I deleted this module, would complexity vanish (pass-through) or reappear across N callers (earning its keep)?* A "yes, vanishes" is the signal to either delete or merge. A "no, reappears" is the signal to **deepen**.

### The interface is the test surface

For every candidate we ask: *can the deepened module be tested through its public interface alone, or do tests reach into internals?* If the latter, the seam is in the wrong place.

## Goals

1. For each of the 5 candidates (#1 → #5), complete one grilling session that ends in a **resolved design** (or an explicit decision to skip / record an ADR / split into a follow-up plan).
2. Resolve the ADR-0001 circuit-breaker replication inconsistency surfaced during exploration (under #1).
3. Update `CONTEXT.md` inline whenever a new domain term is named (e.g., a new deepened module). Update `docs/adr/` whenever a decision is load-bearing enough that a future explorer would re-suggest the same refactor.
4. At the end, produce 0–5 implementation plans (one per resolved candidate) and 0–N ADRs.

## Non-Goals

- **Implementation is not this plan.** Each candidate, once grilled, spawns a separate plan in `docs/plans/active/` with its own file change list and tests.
- **No new feature work.** These are refactors — they preserve behavior, they don't add capability.
- **No docs rewrites outside of inline `CONTEXT.md` / `docs/adr/` updates** required by the decisions.
- **No revisiting settled decisions** in ADRs unless the friction is real enough to warrant reopening (per the skill's `ADR conflicts` rule).
- **No UI/UX changes.** All 5 candidates are below the presentation layer.

## Candidates in Order

### #1 🔴 Extract `CameraWorkerBase` — camera infrastructure duplicated 3 places

**Modules involved:** `ui/camera_thread.py`, `ui/enrollment_camera_thread.py`, `ui/enrollment_ai_worker.py`.

**Friction recap:** 7 infrastructure patterns copy-pasted verbatim (`_retry_read()`, circuit-breaker counter, sentinel queue, `submit_task()` numpy-copy, stop/drain, `_READ_RETRY_DELAYS`, `_PAUSE_POLL_INTERVAL_SECONDS`). Changing the circuit-breaker threshold (ADR-0001: 30) requires touching 3 files. Adding a camera feature costs ~120 LOC instead of ~40.

**ADR-0001 conflict (worth surfacing):** The ADR says "the counter is shared between liveness and head-pose in the enrollment thread." In `EnrollmentAIWorker`, head-pose and liveness have **independent** consecutive-failure counters — they share `self._consecutive_failures` only by variable reuse, not by design. If head-pose fails 29 times then succeeds, the counter resets even if liveness has been silently failing. The ADR's "one broken model kills both" is only partially implemented. **Worth reopening the ADR if the new base class fixes this — otherwise the new base is encoding the same bug.**

**Design questions to grill:**

| # | Question | Why it matters |
|---|----------|----------------|
| 1 | Base class vs mixin vs composition? | Inheritance tightens coupling; composition is more flexible. Both camera threads use the same camera; both AI workers use the same queue/sentinel — is there a shared concept or two? |
| 2 | Should the circuit-breaker counter be **per-model** (separate liveness + head-pose) or **shared** (any failure increments)? | ADR-0001 said "shared between liveness and head-pose." We should either preserve that intent in the new base or reopen the ADR. |
| 3 | Is `EnrollmentCameraThread` (legacy path) actually used, or has `EnrollmentAIWorker` replaced it? | If legacy path is dead code, only 2 consumers need refactoring. |
| 4 | Where does the base class live? `ui/camera_thread_base.py`? `core/camera_worker.py`? | Camera threads are UI-threaded; base should be in `ui/` or a new `infrastructure/` package. |
| 5 | What goes behind the seam vs in the interface? `run()` is `abstract`; `submit_task()` is concrete shared; `pause()`/`resume()` (currently in `CameraThread` only) is per-thread. | Establish which methods are part of the contract. |

**Expected output:** One implementation plan (e.g., `0003-camera-worker-base.md`) + possibly an ADR update to 0001.

**Effort estimate:** M (2-3 days).

---

### #2 🔴 Introduce `AIPipeline` orchestrator — per-frame logic distributed across 6 files

**Modules involved:** `services/ai_pipeline.py`, `services/head_pose.py`, `core/liveness_tracker.py`, `ui/camera_thread.py`, `ui/enrollment_ai_worker.py`, `utils/face_utils.py`.

**Friction recap:** Understanding "how does a single frame get processed" requires reading 6 files across 4 layers. `AIWorker.run()` manually sequences crop → liveness → tracking → recognition. No `AIPipeline.run(frame) -> PipelineResult` exists. `LivenessTracker` lives in `core/` but is only used by `AIWorker` (seam placement smell).

**Design questions to grill:**

| # | Question | Why it matters |
|---|----------|----------------|
| 1 | One `AIPipeline` for both attendance and enrollment, or two specialized pipelines? | Attendance uses liveness + recognition; enrollment uses head-pose + liveness + embedding extraction. Different crops (2.7 vs 1.5), different output types. Is the overlap worth one class? |
| 2 | What is the `PipelineResult` shape? Dataclass with `liveness`, `recognition`, `head_pose` fields (each optional)? | A clean result type means callers don't have to peek at internals. |
| 3 | Does `AIPipeline` own the frame-skip counter (`_AI_FRAME_SKIP = 3`)? | Currently `CameraThread.run()` owns it. Moving it to the pipeline makes the pipeline self-paced. |
| 4 | Where does `LivenessTracker` belong? Move from `core/` to `services/ai_pipeline.py`, or keep in `core/` as a shared utility? | Per the skill's `seam placement` rule, code should live where it has leverage — if only one caller uses it, that's where it belongs. |
| 5 | Is the crop-scale selection (2.7 vs 1.5) per-call or part of pipeline configuration? | A `LivenessPreprocessing(scale=2.7)` config embedded in the pipeline is cleaner than passing scale as a parameter to each call. |

**Expected output:** One implementation plan (e.g., `0004-ai-pipeline-orchestrator.md`) + possible `CONTEXT.md` additions for the `PipelineResult` term.

**Effort estimate:** M (2-3 days).

---

### #3 🟠 Centralize configuration resolution — defaults scattered in 4 places

**Modules involved:** `main.py`, `user_mode_view.py`, `settings_widget.py`, `services/ai_pipeline.py`, `settings_service.py`, `core/bootstrap.py`, `.env.example`.

**Friction recap:** Default `0.3` for liveness threshold is hardcoded in 4 files. Precedence chain (CLI > env > DB > default) is implicit in the order of operations in `main.py`, not a single data structure. `bootstrap.py` uses a different strategy (no dotenv). 0.5→0.3 migration touched 7 files (per `CONTEXT.md`).

**Design questions to grill:**

| # | Question | Why it matters |
|---|----------|----------------|
| 1 | `SystemConfig` dataclass with all tunables, or a `ConfigResolver` with named entries? | Dataclass = data; resolver = behavior. The behavior (resolution order) is the complex part. |
| 2 | Is `bootstrap.py` a different resolver, or should it share the same one? | `bootstrap.py` is the storage initializer; it runs in a different mode. A shared resolver that knows "I am in init mode" is possible but couples the two. |
| 3 | Where do defaults live — in the dataclass, in a separate `defaults.py`, or in `.env.example`? | `.env.example` is a docs file, not an executable. Defaults should be in Python. |
| 4 | Is the threshold-seeding pattern (env → DB on first run, then DB owns) encoded in the resolver, or in a separate seeding step? | Seeding is a one-time migration; resolution is per-read. These are different concerns. |
| 5 | Does `SettingsService` earn its keep post-refactor, or does it become a 1-line wrapper? | If the resolver does the work, the service may be unnecessary. |

**Expected output:** One implementation plan (e.g., `0005-system-config-resolver.md`) + possibly removal of `SettingsService` if it becomes a pass-through.

**Effort estimate:** S (1 day).

---

### #4 🟠 Enforce cache invalidation — `FaceReferenceRepository._cache_all` invalidated by convention

**Modules involved:** `repositories/face_reference_repository.py`, `services/enrollment_service.py`.

**Friction recap:** Class-level cache invalidated on every write path, but **by convention only**. `EnrollmentService.save_face_references()` bypasses `replace_all()`, duplicates transaction logic, calls private methods `self.references._encrypt_embedding()` and `self.references._invalidate_cache()`. Cache-invalidation knowledge leaks out of the repository. No test verifies invalidation.

**Design questions to grill:**

| # | Question | Why it matters |
|---|----------|----------------|
| 1 | `CachingFaceReferenceRepository` wrapper vs `@invalidate_cache` decorator vs proxy class? | The wrapper is explicit and testable; the decorator is implicit; the proxy is over-engineered. |
| 2 | Should the cache be moved to a port (`FaceReferenceCache` interface) with two adapters (caching, no-op)? | Per `LANGUAGE.md` "one adapter = hypothetical seam, two adapters = real seam." Is the no-op adapter justified? |
| 3 | Does `EnrollmentService.save_face_references()` decompose into `replace_all()` + `users.face_registered = 1` in one transaction, or two? | Transaction boundaries matter — partial failure mode needs to be defined. |
| 4 | Should we add a test that catches future "forgot to invalidate" regressions? | A contract test: "for every write method, after the call, cache is empty for that user_id." |
| 5 | Does the cache belong at all? `get_all()` could just hit the DB — is the performance gain worth the invalidation risk? | Empirical question. If `identify()` calls `get_all()` once per frame, that's N+1; if rarely, cache may not be earning its keep. |

**Expected output:** One implementation plan (e.g., `0006-caching-face-repository.md`) + cache-invalidation contract test.

**Effort estimate:** S-M (1-2 days).

---

### #5 🟡 Extract `FacePreprocessor` — preprocessing logic distributed across 3 files

**Modules involved:** `utils/face_utils.py`, `services/ai_pipeline.py` (`LivenessChecker._preprocess`), `services/head_pose.py` (`HeadPoseEstimator._preprocess`).

**Friction recap:** Each model has its own preprocessing pipeline embedded in the model class. `_crop_face` scale parameter is the only abstraction for switching between liveness (2.7) and head-pose (1.5). `CONTEXT.md` says CLAHE is "always-on" but the code may not reflect this — a documentation/code conflict.

**Design questions to grill:**

| # | Question | Why it matters |
|---|----------|----------------|
| 1 | `FacePreprocessor` class with composable steps, or a `preprocessing` module with free functions? | Class enables configuration objects; functions are simpler. Given the per-model configurations (2.7/1.5, 128/224, [0,1]/imagenet), a class with named configs reads better. |
| 2 | Is CLAHE part of the preprocessor or a separate "image enhancement" step? | `CONTEXT.md` decision: "Remove by default, CLAHE is mismatch" — but code may still have it. Resolving this conflict is part of the design. |
| 3 | Should the preprocessor know about model-specific quirks (e.g., MiniFASNet expects no ImageNet norm, just [0,1])? | Encoding model expectations in the preprocessor config avoids per-model conditional code in the pipeline. |
| 4 | Does this candidate overlap with #2 (`AIPipeline`)? | If we do #2 first, the pipeline might own preprocessing naturally. Should we do #5 before #2 so the pipeline consumes an already-deep preprocessor, or after? |
| 5 | What's the test strategy — verify preprocessing matches the training pipeline (snapshot test on output tensor)? | Preprocessing is high-risk (silent accuracy degradation if shape/range/order changes). |

**Expected output:** One implementation plan (e.g., `0007-face-preprocessor.md`) + CLAHE-on/off config (resolves CONTEXT.md ambiguity).

**Effort estimate:** S (half a day for the extraction; #2 may consume it as a precondition).

---

## Design Decisions

_To be filled as each candidate is grilled. One table per candidate._

### #1 CameraWorkerBase
_(pending grilling session)_

### #2 AIPipeline orchestrator
_(pending grilling session)_

### #3 Configuration resolution
_(pending grilling session)_

### #4 Cache invalidation
_(pending grilling session)_

### #5 FacePreprocessor
_(pending grilling session)_

---

## Implementation

Each candidate, once grilled, produces its **own** implementation plan in `docs/plans/active/`. This meta-plan is updated with a one-line note in the corresponding section above pointing to the follow-up plan ID. Sequence:

| # | Candidate | Follow-up plan | Status |
|---|-----------|----------------|--------|
| 1 | `CameraWorkerBase` | _(to be created)_ | not started |
| 2 | `AIPipeline` orchestrator | _(to be created)_ | not started |
| 3 | `SystemConfig` resolver | _(to be created)_ | not started |
| 4 | `CachingFaceReferenceRepository` | _(to be created)_ | not started |
| 5 | `FacePreprocessor` | _(to be created)_ | not started |

**Cross-candidate dependencies:**

- #2 (`AIPipeline`) and #5 (`FacePreprocessor`) overlap. Recommend doing #5 first so the pipeline consumes a deep preprocessor.
- #1 (`CameraWorkerBase`) is independent and can be done in parallel with the others.
- #3 (`SystemConfig`) is independent.
- #4 (cache invalidation) is independent but the wrapper-style solution may benefit from a `Repository[T]` port introduced in a future candidate.

---

## Testing

Since this is a design plan (not an implementation plan), the "testing" here is **the grilling process itself**, not test code. Per candidate, the acceptance criteria for "grilling complete" are:

1. **Design questions answered** (table filled in `## Design Decisions`).
2. **Seam placement decided** — does the new module live where it's used, or where it's owned? Justify.
3. **Test strategy decided** — through the new interface, not by mocking internals.
4. **ADR conflicts resolved** — either the ADR is reaffirmed (and the reason recorded here), or the ADR is updated.
5. **CONTEXT.md updated** if any new domain term was named.
6. **Follow-up plan created** in `docs/plans/active/` with a file change list + tests.

For the **follow-up** implementation plans (created per candidate), the test discipline is:

- **Replace, don't layer** (per `DEEPENING.md`). Tests on the new deepened module's interface; old unit tests on the shallow pieces are deleted if they become waste.
- **No mocking past the interface.** If a test has to change when the implementation changes, it's testing past the seam.
- **Contract test for the cache** (candidate #4): "for every write method, after the call, cache returns fresh data."

---

## Related

- `AGENTS.md` "Gotchas" — hints at the friction surfaced (cache invalidation convention, hardcoded `_COOLDOWN_SECONDS` / `_AI_FRAME_SKIP`, repository cache key, etc.).
- `CONTEXT.md` — domain glossary. May grow new terms (e.g., `PipelineResult`, `FacePreprocessor`, `SystemConfig`) as candidates are resolved.
- `docs/adr/0001-onnx-circuit-breaker.md` — only existing ADR; candidate #1 may update it.
- `.agents/skills/improve-codebase-architecture/{LANGUAGE.md,DEEPENING.md,INTERFACE-DESIGN.md}` — vocabulary and methodology this plan follows.
- Branch: `refactor/source-code`.
