# Plan 0002: Architecture Deepening — Checklist

**Parent tracker** for the 5 deepening opportunities surfaced by the `improve-codebase-architecture` skill. This plan **does not contain implementation details** — those live in the per-candidate plans listed below. This file is a **status board**: as each per-candidate plan is implemented and merged, mark its checkbox below.

See `.agents/skills/improve-codebase-architecture/LANGUAGE.md` for the architecture vocabulary (**module**, **interface**, **seam**, **adapter**, **leverage**, **locality**) and `CONTEXT.md` for the domain glossary.

## Status

**In progress** — 1 of 5 candidates done (#5, 2026-06-03, commit `8863ec1` on `refactor/source-code`). The remaining 4 are still in Draft; no implementation has started on them yet.

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

1. Drive each per-candidate plan to **Done** (merged to `main`). **1 of 5 done (#5, 2026-06-03).**
2. Resolve the ADR-0001 circuit-breaker replication inconsistency under candidate #1.
3. Update `CONTEXT.md` inline whenever a new domain term is named. ✅ **Done for #5** — `FacePreprocessor` term added, CLAHE ambiguity resolved.
4. Update `docs/adr/` whenever a decision is load-bearing enough that a future explorer would re-suggest the same refactor.

## Non-Goals

- **No new feature work.** These are refactors — they preserve behavior.
- **No UI/UX changes.** All 5 candidates are below the presentation layer.
- **No docs rewrites outside of inline `CONTEXT.md` / `docs/adr/` updates** required by the decisions.

## Checklist

Mark each item as it is **implemented and merged to `main`**. The per-candidate plan (linked) is moved to `docs/plans/archive/` on merge, and this checklist is updated.

- [ ] **#1** — Extract `CameraWorkerBase` → [0003-camera-worker-base.md](0003-camera-worker-base.md). _Status: Draft. Independent of other candidates. Resolves ADR-0001 circuit-breaker inconsistency._
- [ ] **#2** — Introduce `AIPipeline` orchestrator → [0004-ai-pipeline-orchestrator.md](0004-ai-pipeline-orchestrator.md). _Status: Draft. **Unblocked** — #5 is done; pipeline can now consume `FacePreprocessor` directly._
- [ ] **#3** — Centralize configuration resolution (`SystemConfig`) → [0005-system-config-resolver.md](0005-system-config-resolver.md). _Status: Draft. Independent of other candidates._
- [ ] **#4** — Enforce cache invalidation (`CachingFaceReferenceRepository`) → [0006-caching-face-repository.md](0006-caching-face-repository.md). _Status: Draft. Independent of other candidates._
- [x] **#5** — Extract `FacePreprocessor` → archived as [2026-06-03-0007-face-preprocessor.md](../archive/2026-06-03-0007-face-preprocessor.md). _Status: **Done** (2026-06-03, commit `8863ec1`). Branch `refactor/source-code`. Unblocked #2._

### Status legend

- `[ ]` — Plan drafted, not yet implemented.
- `[~]` — Plan grilled, decisions filled, implementation in progress on a feature branch.
- `[x]` — Plan implemented, tests pass, merged to `main`, file moved to `docs/plans/archive/`.

## Cross-candidate dependencies

| From | To | Reason |
|------|-----|--------|
| ~~#5 (`FacePreprocessor`)~~ | ~~#2 (`AIPipeline`)~~ | **Resolved (2026-06-03):** #5 is done, so #2 is unblocked. Pipeline can consume `FacePreprocessor` directly via `preprocessing_configs.{LIVENESS_CONFIG, HEAD_POSE_CONFIG}`. |
| #1 (`CameraWorkerBase`) | — | Independent. Can be done in parallel with anything. |
| #3 (`SystemConfig`) | — | Independent. |
| #4 (`CachingFaceReferenceRepository`) | — | Independent. The wrapper pattern may inspire a future generic `Repository[T]` port, but that's not in scope here. |

**Recommended order:** ~~#5 →~~ #2 → #1 → #3 → #4. (#1 and #3 are interchangeable; both independent of #2 and #4.)

## ADR conflicts

**ADR-0001** (`docs/adr/0001-onnx-circuit-breaker.md`) — only existing ADR.

The ADR says the circuit-breaker counter is "shared between liveness and head-pose in the enrollment thread." In `EnrollmentAIWorker`, the counter is shared **by variable reuse, not by design** — a success in head-pose resets failures counted by liveness. This is a partial implementation of the ADR's intent.

**Resolution path:** candidate #1 (`CameraWorkerBase`) is the natural place to encode the correct semantics. The grilling session for #1 should decide between:
- Per-model counters (preserves "one broken model kills both" intent with explicit logic).
- Single shared counter (current accidental behavior, document the reset rule).
- A new ADR that revises the original decision.

If the design decision differs from ADR-0001, **update the ADR** as part of candidate #1.

## Testing discipline (applies to all candidates)

Per `DEEPENING.md`:
- **Replace, don't layer.** Tests on the new deepened module's interface; old unit tests on the shallow pieces are deleted if they become waste.
- **No mocking past the interface.** If a test has to change when the implementation changes, it's testing past the seam.
- **Contract test for the cache** (candidate #4): "for every write method, after the call, cache returns fresh data."

## Related

- `AGENTS.md` "Gotchas" — hints at the friction surfaced (cache invalidation convention, hardcoded `_COOLDOWN_SECONDS` / `_AI_FRAME_SKIP`, repository cache key, etc.).
- `CONTEXT.md` — domain glossary. New term added by #5: `FacePreprocessor`. Future terms from other candidates: `PipelineResult`, `SystemConfig`, `CachingFaceReferenceRepository`.
- `docs/adr/0001-onnx-circuit-breaker.md` — only existing ADR; candidate #1 may update it.
- `.agents/skills/improve-codebase-architecture/{LANGUAGE.md,DEEPENING.md,INTERFACE-DESIGN.md}` — vocabulary and methodology this plan follows.
- Per-candidate plans: [0003](0003-camera-worker-base.md) · [0004](0004-ai-pipeline-orchestrator.md) · [0005](0005-system-config-resolver.md) · [0006](0006-caching-face-repository.md) · [archived 0007](../archive/2026-06-03-0007-face-preprocessor.md) (done 2026-06-03).
- Branch: `refactor/source-code`.
