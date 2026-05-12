# Implementation Summary: Face Anti-Spoofing Integration

## Quick Overview

**Goal**: Fix critical security issue C-2 by replacing dummy anti-spoofing with real MiniFASNetV2-SE model.

**Model**: 600 KB quantized ONNX model  
**Performance**: 98.20% accuracy (97.55% real, 98.73% spoof)  
**Latency**: <50ms per face inference  
**Status**: Ready to implement

---

## Key Deliverables

```
📦 007-face-anti-spoofing-integration/
├── spec.md           ← Feature specification (detailed requirements)
├── PLAN.md           ← Implementation plan (11 phases)
├── data-model.md     ← Data structures (to be created)
├── quickstart.md     ← Quick start guide (to be created)
└── tasks.md          ← Actionable tasks (to be created)
```

---

## Implementation Phases

### Phase 1: Setup (Day 1)
- [ ] Add `onnxruntime>=1.16.0` to dependencies
- [ ] Create `tools/download_antispoof_models.py`
- [ ] Update `.env.example` with anti-spoof config
- [ ] **Deliverable**: Model ready to use

### Phase 2: Core Service (Day 1-2)
- [ ] Create `src/services/antispoof_service.py`
  - Model loading & caching
  - Image preprocessing (128×128 RGB)
  - ONNX inference
  - Logit postprocessing
- [ ] Update `src/core/config.py` for anti-spoof settings
- [ ] **Deliverable**: AntiSpoofService fully functional

### Phase 3: Integration (Day 2)
- [ ] Replace dummy `create_liveness_evaluator()` in `src/services/ai_backends.py`
- [ ] Update documentation
- [ ] **Deliverable**: Real liveness evaluation in pipeline

### Phase 4: Testing (Day 2-3)
- [ ] Unit tests (model loading, preprocessing, inference)
- [ ] Integration tests (pipeline with real/spoof detection)
- [ ] Performance benchmarks
- [ ] **Deliverable**: >90% test coverage

### Phase 5: Validation (Day 3)
- [ ] Smoke tests
- [ ] Performance profiling
- [ ] Graceful fallback verification
- [ ] **Deliverable**: Production-ready

---

## Architecture Changes

### Before (Current - BROKEN)
```python
# src/services/ai_backends.py:72-85
def create_liveness_evaluator(model_dir=None):
    logger.warning("deepface-cv2 does not support anti-spoofing...")
    
    def evaluate(face):
        return 1.0  # ❌ ALWAYS PASSES - NO SECURITY!
    
    return evaluate
```

### After (Fixed)
```python
# src/services/ai_backends.py:72-85 (updated)
def create_liveness_evaluator(model_path=None):
    from services.antispoof_service import AntiSpoofService
    
    service = AntiSpoofService(
        model_path=model_path or CONFIG.FACE_ANTISPOOF_MODEL_PATH,
        enabled=CONFIG.FACE_ANTISPOOF_ENABLED
    )
    
    if not service.load():
        logger.error("Failed to load anti-spoofing model")
        return lambda face: 1.0  # Fallback (safe failure)
    
    def evaluate(face):
        score = service.evaluate(face)  # ✅ REAL INFERENCE
        logger.debug(f"Liveness: {score:.3f}")
        return score
    
    return evaluate
```

---

## Data Flow

```
Frame from Camera (640×480 BGR)
        ↓
[EXISTING] Face Detector (deepface-cv2)
        ↓
Face Region (variable size)
        ↓
[NEW] AntiSpoofService
   ├─ Crop face region
   ├─ Resize to 128×128
   ├─ Normalize RGB [0, 1]
   ├─ ONNX Inference → [real_logit, spoof_logit]
   └─ Return score 0.0-1.0
        ↓
Compare score vs threshold (default: 0.5)
        ↓
    [Score < 0.5]          [Score ≥ 0.5]
        ↓                        ↓
   SPOOF_WARNING        [EXISTING] Recognition
   (Reject)            (Continue to identify)
```

---

## Configuration

### Environment Variables
```env
# Enable/disable anti-spoofing
FACE_ANTISPOOF_ENABLED=true

# Path to ONNX model (600 KB)
FACE_ANTISPOOF_MODEL_PATH=models/anti_spoof/best_model_quantized.onnx

# Liveness threshold (0.0-1.0, higher = stricter)
FACE_ANTISPOOF_CONFIDENCE_THRESHOLD=0.5
```

### Database (no schema changes needed)
- Uses existing `sessions.liveness_threshold_snapshot` column
- Logs to existing `recognition_events` table
- Optional: new `antispoof_evaluations` audit table

---

## Testing Strategy

### Unit Tests (8 tests)
```
✓ Model loads successfully
✓ Image preprocessing correct (128×128 shape)
✓ Real face scores high (>0.7)
✓ Spoof face scores low (<0.3)
✓ Invalid input handled gracefully
✓ Error fallback works
✓ Disabled mode works
✓ Missing model handled
```

### Integration Tests (3 tests)
```
✓ Pipeline rejects spoof (SPOOF_WARNING event)
✓ Pipeline accepts real face (proceeds to recognition)
✓ Fallback when model unavailable
```

### Performance Benchmarks
```
✓ Model load: <2 seconds
✓ Inference: <50ms per face
✓ FPS impact: <10% (target)
```

---

## File Changes Summary

### New Files
```
src/services/antispoof_service.py          (200-250 lines)
tools/download_antispoof_models.py         (100-150 lines)
tests/unit/test_antispoof_service.py       (250-300 lines)
tests/integration/test_antispoof_pipeline.py (150-200 lines)
specs/007-face-anti-spoofing-integration/  (all files)
```

### Modified Files
```
src/services/ai_backends.py                (replace dummy evaluator)
src/core/config.py                         (add 3 new config fields)
pyproject.toml                             (add onnxruntime dependency)
.env.example                               (add 3 new env vars)
README.md                                  (add anti-spoof section)
AGENTS.md                                  (update stack info)
```

### Model Files
```
models/anti_spoof/best_model_quantized.onnx  (600 KB - download required)
```

---

## Success Criteria

✅ **Functional**
- Real faces detected as real (liveness > threshold)
- Spoofs detected as spoof (liveness < threshold)  
- SPOOF_WARNING event emitted correctly
- Graceful fallback when model unavailable

✅ **Performance**
- Inference <50ms per face
- <10% FPS impact
- Model loads in <2 seconds

✅ **Reliability**
- 99%+ uptime
- Proper error logging
- No crashes on edge cases

✅ **Security**
- No hardcoded paths
- Configuration via environment
- Audit trail for all evaluations

---

## Risk Assessment

| Risk | Severity | Mitigation |
|------|----------|-----------|
| False positives (reject real) | Medium | Tunable threshold, conservative default (0.5) |
| False negatives (accept spoof) | High | Conservative threshold, audit logging |
| Performance degradation | Medium | Quantized model, benchmarking before release |
| Model unavailable | Low | Graceful fallback, clear error messages |
| GPU compatibility issues | Low | CPU-first design, optional GPU support |

---

## Next Actions

1. **Review & Approve** the specification and plan
2. **Create data-model.md** (document AntiSpoofEvaluation dataclass)
3. **Create quickstart.md** (how to set up anti-spoof)
4. **Create tasks.md** (actionable implementation tasks)
5. **Begin Phase 1** (dependencies & model setup)

---

## Estimated Timeline

- **Phase 1-2 (Setup + Service)**: 8 hours
- **Phase 3 (Integration)**: 4 hours  
- **Phase 4 (Testing)**: 6 hours
- **Phase 5 (Validation)**: 4 hours
- **Total**: 22-24 hours (3 days with parallel work)

---

## Questions for Clarification

Before starting implementation, consider:

1. **Threshold Strategy**: Start with 0.5 or more conservative (0.6-0.7)?
2. **Audit Logging**: Create new `antispoof_evaluations` table or use existing `recognition_events`?
3. **Fallback Behavior**: If model unavailable, accept all (current) or reject all (fail-safe)?
4. **Performance Priority**: Prioritize speed or accuracy? (quantized model chosen for speed)
5. **GPU Support**: CPU-only for now, or add GPU acceleration immediately?

---

**This plan is ready to implement. Proceed with Phase 1 (dependencies & setup) to get started.**
