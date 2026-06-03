# Implement Plan: Plan 0004 - Introduce `AIPipeline` Orchestrator

**Created by:** @oracle
**Based on:** [0004-ai-pipeline-orchestrator.md](0004-ai-pipeline-orchestrator.md)
**Status:** Ready for execution

---

## Design Resolution

### 1. Pipeline Specialization
**Decision:** One `AIPipeline` class with specialized methods for different use cases (`run_attendance`, `run_enrollment`)  
**Justification:** Attendance and enrollment pipelines share core components (liveness checking, face recognition) but have distinct sequences and purposes. A single class with focused methods avoids code duplication while maintaining clear separation of concerns. This is preferable to either completely separate pipelines (duplication) or one monolithic method trying to handle all cases (complexity).

### 2. PipelineResult Shape
**Decision:** `@dataclass(slots=True)` with optional fields for all possible outputs plus a `result_type` discriminator  
**Justification:** Follows existing patterns in the codebase (e.g., `LivenessResult`, `RecognitionResult`). Provides flexibility for different use cases while maintaining type safety. Required fields will be minimal (timestamp, frame metadata); outputs from specific pipeline stages will be optional.

### 3. Frame-Skip Counter Ownership
**Decision:** Frame-skip counter (`_AI_FRAME_SKIP = 3`) remains in UI/camera thread layer  
**Justification:** This is a performance optimization policy that determines when to invoke the pipeline, not part of the pipeline's core responsibility. Keeping it at the call site maintains proper separation of concerns.

### 4. LivenessTracker Location
**Decision:** Move `LivenessTracker` from `core/liveness_tracker.py` to `services/liveness_tracker.py` and compose it within `AIPipeline`  
**Justification:** The `LivenessTracker` is an AI service component, not a fundamental system core component. Moving it to `services/` groups it with related AI services. Having `AIPipeline` own and manage the tracker instance preserves the existing behavior where each worker thread has its own tracker state.

### 5. Crop-Scale Selection
**Decision:** Use `PreprocessingConfig` objects (from Plan 0007) that encapsulate scale and other preprocessing parameters  
**Justification:** Leverages the work completed in Plan 0007 (`FacePreprocessor`). Provides clean, configurable preprocessing that eliminates hardcoded scale values while maintaining consistency with the existing architecture.

---

## Task Breakdown

### Phase 1: Foundation Components

| # | Task | Agent | File | Description |
|---|------|-------|------|-------------|
| 1.1 | Create PipelineResult dataclass | @fixer | `services/pipeline_result.py` | Define `@dataclass(slots=True) PipelineResult` with optional fields |
| 1.2 | Relocate LivenessTracker | @fixer | `core/liveness_tracker.py` → `services/liveness_tracker.py` | Move file, update all imports |
| 1.3 | Create AIPipeline class | @fixer | `services/ai_pipeline.py` | Add orchestrator class with dependency injection |

### Phase 2: Pipeline Implementation

| # | Task | Agent | File | Description |
|---|------|-------|------|-------------|
| 2.1 | Implement run_attendance() | @fixer | `services/ai_pipeline.py` | Liveness → recognition → PipelineResult |
| 2.2 | Implement run_enrollment() | @fixer | `services/ai_pipeline.py` | Head-pose → liveness → embedding → PipelineResult |

### Phase 3: Integration & Updates

| # | Task | Agent | File | Description |
|---|------|-------|------|-------------|
| 3.1 | Update AIWorker | @fixer | `ui/camera_thread.py` | Replace 79-line run() with ~5-line pipeline call |
| 3.2 | Update EnrollmentAIWorker | @fixer | `ui/enrollment_ai_worker.py` | Replace 87-line run() with ~5-line pipeline call |

### Phase 4: Testing & Documentation

| # | Task | Agent | File | Description |
|---|------|-------|------|-------------|
| 4.1 | PipelineResult unit tests | @fixer | `tests/unit/test_pipeline_result.py` | Dataclass behavior, field access |
| 4.2 | AIPipeline unit tests | @fixer | `tests/unit/test_ai_pipeline.py` | Both pipeline modes, edge cases |
| 4.3 | Update CONTEXT.md | @fixer | `CONTEXT.md` | Add PipelineResult term |

### Phase 5: Verification

| # | Task | Agent | Command | Description |
|---|------|-------|---------|-------------|
| 5.1 | Run test suite | Orchestrator | `pytest tests/` | Ensure no regressions |
| 5.2 | Run linting | Orchestrator | `ruff check src/` | Code quality check |
| 5.3 | Code review | @oracle | — | Final architecture review |

---

## Dependency Graph

```
Phase 1 (Parallel):
  1.1 Create PipelineResult ─────┐
  1.2 Relocate LivenessTracker ──┼──▶ Phase 2
  1.3 Create AIPipeline class ───┘

Phase 2 (Sequential after Phase 1):
  2.1 Implement run_attendance() ──┐
  2.2 Implement run_enrollment() ──┼──▶ Phase 3
                                   │
Phase 3 (Parallel after Phase 2):  │
  3.1 Update AIWorker ────────────┤
  3.2 Update EnrollmentAIWorker ──┘
        │
        ▼
Phase 4 (Parallel after Phase 3):
  4.1 PipelineResult tests ──┐
  4.2 AIPipeline tests ──────┼──▶ Phase 5
  4.3 Update CONTEXT.md ─────┘

Phase 5 (Sequential):
  5.1 Run tests ──▶ 5.2 Run lint ──▶ 5.3 Code review
```

---

## Parallel Execution Opportunities

| Group | Tasks | Parallel? | Blocked By |
|-------|-------|-----------|------------|
| G1 | 1.1, 1.2, 1.3 | ✅ Yes | Plan 0007 complete |
| G2 | 2.1, 2.2 | ⚠️ Sequential | G1 complete |
| G3 | 3.1, 3.2 | ✅ Yes | G2 complete |
| G4 | 4.1, 4.2, 4.3 | ✅ Yes | G3 complete |
| G5 | 5.1, 5.2, 5.3 | ⚠️ Sequential | G4 complete |

**Total sub-agent tasks:** 9 (all @fixer)
**Orchestrator tasks:** 3 (verification + review)

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Behavioral changes during refactor | Medium | High | Write tests before modifying workers; approval testing |
| Incorrect PipelineResult field mapping | Medium | Medium | Define fields based on actual signal emissions |
| Threading issues with LivenessTracker | Low | High | Each AIPipeline instance owns its own tracker |
| Performance regression | Low | Medium | Benchmark before/after; no unnecessary object creation |
| Import chain disruptions | Medium | Medium | Update imports in batches with immediate testing |

---

## Sub-Agent Summary

```
┌─────────────────────────────────────────────────────────────┐
│                    TASK DISTRIBUTION                         │
│                                                             │
│  @fixer (9 tasks):                                         │
│  ├─ 1.1 Create PipelineResult                              │
│  ├─ 1.2 Relocate LivenessTracker                           │
│  ├─ 1.3 Create AIPipeline class                            │
│  ├─ 2.1 Implement run_attendance()                         │
│  ├─ 2.2 Implement run_enrollment()                         │
│  ├─ 3.1 Update AIWorker                                    │
│  ├─ 3.2 Update EnrollmentAIWorker                          │
│  ├─ 4.1 PipelineResult tests                               │
│  └─ 4.2 AIPipeline tests                                  │
│                                                             │
│  @oracle (1 task):                                         │
│  └─ 5.3 Final architecture review                         │
│                                                             │
│  Orchestrator (3 tasks):                                   │
│  ├─ 4.3 Update CONTEXT.md                                 │
│  ├─ 5.1 Run test suite                                    │
│  └─ 5.2 Run linting                                       │
│                                                             │
│  Total: 13 tasks                                           │
│  @fixer: 69% | @oracle: 8% | Orchestrator: 23%            │
└─────────────────────────────────────────────────────────────┘
```

---

## Verification Commands

```bash
# Phase 4 tests
pytest tests/unit/test_pipeline_result.py -v
pytest tests/unit/test_ai_pipeline.py -v

# Phase 5 verification
pytest tests/ -v
ruff check src/attendance_system/services/
ruff check src/attendance_system/ui/
```

---

## Notes

- **Dependency:** Plan 0007 (FacePreprocessor) must be completed first
- **Branch:** `refactor/source-code`
- **No changes to:** ONNX models, decision logic, temporal smoothing algorithm
- **Backward compatibility:** All existing behavior preserved through interface contracts
