# Plan 0002: Architecture Deepening — Checklist

**Parent tracker** for the 5 deepening opportunities surfaced by the `improve-codebase-architecture` skill. This plan **does not contain implementation details** — those live in the per-candidate plans listed below. This file is a **status board**: as each per-candidate plan is implemented and merged, mark its checkbox below. **4 of 5 done as of 2026-06-06**; the file was moved to `archive/2026-06-06-0002-architecture-deepening.md` on that date. Only #3 (`SystemConfig`) remains in `active/`.

See `.agents/skills/improve-codebase-architecture/LANGUAGE.md` for the architecture vocabulary (**module**, **interface**, **seam**, **adapter**, **leverage**, **locality**) and `CONTEXT.md` for the domain glossary.

## Status

**Done (4 of 5 candidates)** — #5 2026-06-03 commit `8863ec1`, #2 2026-06-03 commit `a1590c1`, #1 2026-06-04 commit `7e0e747`, #4 2026-06-06 commit `68ca3fc`, all on `refactor/source-code`. Only #3 (`SystemConfig`) remains in Draft on `active/0005-system-config-resolver.md`.

## Context

A `Explore` sub-agent walked the codebase and produced a ranked friction report. The top 5 opportunities (shallow modules, leaky seams, scattered defaults) are tracked here in the order the user requested (#1 → #5). Each was promoted to its own implementation plan with full Design Decisions / Implementation / Testing sections.

This plan remains useful as:
- A **checklist** of where the 5 refactors stand.
- A **pointer** to the per-candidate plans (which contain the actual work).
- A record of the **cross-candidate dependencies** and **ADR conflicts** that span multiple plans.

### Deletion test reminder

For every candidate: *if I deleted this module, would complexity vanish (pass-through) or reappear across N callers (earning its keep)?* A "yes, vanishes" is the signal to either delete or merge. A "no, reappears" is the signal to **deepen**.

### The interface is the test surface

For every candidate: *can the deepened module be tested through its public interface alone, or do tests reach into internals?* If the latter, the seam is in the wrong place.

## Goals

1. Drive each per-candidate plan to **Done** (merged to `main`). **4 of 5 done (#5, #2 — 2026-06-03; #1 — 2026-06-04; #4 — 2026-06-06).**
2. Resolve the ADR-0001 circuit-breaker replication inconsistency under candidate #1.
3. Update `CONTEXT.md` inline whenever a new domain term is named. ✅ **Done for #5, #2, and #4** — `FacePreprocessor`, `PipelineResult`, `AIPipeline`, `CachingFaceReferenceRepository` terms added.
4. Update `docs/adr/` whenever a decision is load-bearing enough that a future explorer would re-suggest the same refactor.

## Non-Goals

- **No new feature work.** These are refactors — they preserve behavior.
- **No UI/UX changes.** All 5 candidates are below the presentation layer.
- **No docs rewrites outside of inline `CONTEXT.md` / `docs/adr/` updates** required by the decisions.

## Checklist

Mark each item as it is **implemented and merged to `main`**. The per-candidate plan (linked) is moved to `docs/plans/archive/` on merge, and this checklist is updated.

- [x] **#1** — Extract `CameraWorkerBase` → archived as [2026-06-04-0003-camera-worker-base.md](../archive/2026-06-04-0003-camera-worker-base.md). _Status: **Done** (2026-06-04, commit `7e0e747`). Branch `refactor/source-code`. Resolves ADR-0001 circuit-breaker inconsistency._
- [x] **#2** — Introduce `AIPipeline` orchestrator → archived as [2026-06-03-0004-ai-pipeline-orchestrator-implement.md](../archive/2026-06-03-0004-ai-pipeline-orchestrator-implement.md). _Status: **Done** (2026-06-03, commit `a1590c1`). Branch `refactor/source-code`._
- [ ] **#3** — Centralize configuration resolution (`SystemConfig`) → [0005-system-config-resolver.md](0005-system-config-resolver.md). _Status: Draft. Independent of other candidates._
- [x] **#4** — Enforce cache invalidation (`CachingFaceReferenceRepository`) → archived as [2026-06-06-0006-caching-face-repository.md](../archive/2026-06-06-0006-caching-face-repository.md). _Status: **Done** (2026-06-06, commit `68ca3fc`). Branch `refactor/source-code`. Wrapper owns the cache; inner repo is a pure SQLite adapter; 14 new unit tests + 7 new integration tests (272/272 pass)._
- [x] **#5** — Extract `FacePreprocessor` → archived as [2026-06-03-0007-face-preprocessor.md](../archive/2026-06-03-0007-face-preprocessor.md). _Status: **Done** (2026-06-03, commit `8863ec1`). Branch `refactor/source-code`. Unblocked #2._

### Status legend

- `[ ]` — Plan drafted, not yet implemented.
- `[~]` — Plan grilled, decisions filled, implementation in progress on a feature branch.
- `[x]` — Plan implemented, tests pass, merged to `main`, file moved to `docs/plans/archive/`.

## Cross-candidate dependencies

| From | To | Reason |
|------|-----|--------|
| ~~#5 (`FacePreprocessor`)~~ | ~~#2 (`AIPipeline`)~~ | **Resolved (2026-06-03):** #5 is done, so #2 is unblocked. Pipeline can consume `FacePreprocessor` directly via `preprocessing_configs.{LIVENESS_CONFIG, HEAD_POSE_CONFIG}`. |
| ~~#5 (`FacePreprocessor`)~~ | ~~#2 (`AIPipeline`)~~ | **Resolved (2026-06-03):** #2 is done. Pipeline composes `LivenessChecker` + `LivenessTracker` + `FaceRecognizer`. |
| ~~#1 (`CameraWorkerBase`)~~ | — | **Resolved (2026-06-04):** #1 is done. Base classes live in `ui/camera_worker_base.py`. |
| #3 (`SystemConfig`) | — | Independent. |
| ~~#4 (`CachingFaceReferenceRepository`)~~ | — | **Resolved (2026-06-06):** #4 is done. `CachingFaceReferenceRepository` wrapper enforces cache invalidation by invariant. The wrapper pattern may inspire a future generic `Repository[T]` port, but that's not in scope here. |

**Recommended order:** ~~#5 → #2 → #1 → #4 →~~ #3. (#3 is the last open candidate.)

## ADR conflicts

**ADR-0001** (`docs/adr/0001-onnx-circuit-breaker.md`) — only existing ADR.

The ADR says the circuit-breaker counter is "shared between liveness and head-pose in the enrollment thread." In `EnrollmentAIWorker`, the counter is shared **by variable reuse, not by design** — a success in head-pose resets failures counted by liveness. This is a partial implementation of the ADR's intent.

**Resolution (2026-06-04, #1):** Candidate #1 (`CameraWorkerBase`) encoded the correct semantics in `AIWorkerBase`. The shared counter is now explicit: one broken model kills both attendance and enrollment. No ADR update needed — the base class implementation matches ADR-0001 intent.

## Testing discipline (applies to all candidates)

Per `DEEPENING.md`:
- **Replace, don't layer.** Tests on the new deepened module's interface; old unit tests on the shallow pieces are deleted if they become waste.
- **No mocking past the interface.** If a test has to change when the implementation changes, it's testing past the seam.
- **Contract test for the cache** (candidate #4): "for every write method, after the call, cache returns fresh data."

## Related

- `AGENTS.md` "Gotchas" — hints at the friction surfaced (cache invalidation convention, hardcoded `_COOLDOWN_SECONDS` / `_AI_FRAME_SKIP`, repository cache key, etc.).
- `CONTEXT.md` — domain glossary. Terms added: `FacePreprocessor` (#5), `PipelineResult`, `AIPipeline` (#2), `CachingFaceReferenceRepository` (#4). Future terms from remaining candidate: `SystemConfig` (#3).
- `docs/adr/0001-onnx-circuit-breaker.md` — only existing ADR; candidate #1 may update it.
- `.agents/skills/improve-codebase-architecture/{LANGUAGE.md,DEEPENING.md,INTERFACE-DESIGN.md}` — vocabulary and methodology this plan follows.
- Per-candidate plans: [archived 0003](../archive/2026-06-04-0003-camera-worker-base.md) (done 2026-06-04) · [archived 0004 design](../archive/2026-06-03-0004-ai-pipeline-orchestrator.md) + [archived 0004 implement](../archive/2026-06-03-0004-ai-pipeline-orchestrator-implement.md) (done 2026-06-03) · [0005](0005-system-config-resolver.md) (active) · [archived 0006](../archive/2026-06-06-0006-caching-face-repository.md) (done 2026-06-06) · [archived 0007](../archive/2026-06-03-0007-face-preprocessor.md) (done 2026-06-03).
- Branch: `refactor/source-code`.
