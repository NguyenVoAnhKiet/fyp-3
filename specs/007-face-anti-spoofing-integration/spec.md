# Feature Specification: Face Anti-Spoofing Integration

**Feature ID**: 007-face-anti-spoofing-integration  
**Status**: PROPOSED  
**Priority**: CRITICAL (Fixes C-2 security issue)  
**Target Release**: Q2 2026

---

## 1. Executive Summary

Replace the non-functional dummy anti-spoofing evaluator with a real face liveness detection system using MiniFASNetV2-SE, a lightweight (600 KB) quantized ONNX model. This fixes the critical security issue where spoof attacks (printed photos, screen displays) can bypass facial recognition.

**Key Benefit**: Prevent unauthorized access via spoof attacks while maintaining real-time performance on edge devices.

---

## 2. Problem Statement

### Current Issue (Code Review C-2)
**File**: `src/services/ai_backends.py:72-85`

```python
def evaluate(face: dict[str, Any]) -> float:
    return 1.0  # ALWAYS PASSES - no actual liveness check
```

**Impact**:
- Printed photos of enrolled faces can gain access
- Screen replays can defeat attendance system
- False sense of security for users
- **Severity**: CRITICAL - undermines core security feature

### Root Cause
- `deepface-cv2` library lacks anti-spoofing module
- Placeholder implementation never replaced
- No error raised on bypass

---

## 3. Proposed Solution

### 3.1 Solution Overview
Integrate **MiniFASNetV2-SE** anti-spoofing model:
- **Type**: Binary classifier (Real vs Spoof)
- **Model Size**: 600 KB (quantized INT8 ONNX)
- **Performance**: 98.20% accuracy on 70k+ samples
- **Input**: 128×128 RGB face image
- **Output**: Probability 0.0 (spoof) to 1.0 (real)
- **Speed**: <50ms per face on CPU
- **Framework**: ONNX Runtime (already in project)

### 3.2 Architecture

```
┌─────────────────┐
│  Video Frame    │
└────────┬────────┘
         │
         v
┌─────────────────────────────────┐
│  Face Detector (existing)        │
│  - deepface-cv2 or MiniFAS       │
└────────┬────────────────────────┘
         │ face region
         v
┌─────────────────────────────────┐
│  AntiSpoofService (NEW)          │ ← Phase 2
│  - Load ONNX model               │
│  - Preprocess (128×128 RGB)      │
│  - Inference via ONNX Runtime    │
│  - Extract logits, compute score │
└────────┬────────────────────────┘
         │ liveness_score (0.0-1.0)
         v
┌─────────────────────────────────┐
│  Threshold Check (existing)      │
│  - score < threshold → SPOOF     │
│  - score >= threshold → RECOGNIZE│
└────────┬────────────────────────┘
         │
    ┌────┴────┐
    v         v
┌─────┐   ┌───────────────┐
│SPOOF│   │Face Recognition│
│ EXIT│   │ (existing)     │
└─────┘   └────────┬───────┘
              │
              v
          ┌────────────┐
          │User ID or  │
          │ UNKNOWN    │
          └────────────┘
```

### 3.3 Data Model

```python
@dataclass
class AntiSpoofEvaluation:
    """Anti-spoofing evaluation result."""
    is_real: bool              # True if real, False if spoof
    confidence: float          # 0.0-1.0
    real_logit: float         # Raw model output (class 0)
    spoof_logit: float        # Raw model output (class 1)
    logit_diff: float         # Difference (real - spoof)
    model_version: str        # "MiniFASNetV2-SE:quantized:600KB"
    inference_time_ms: float  # Performance metric
```

---

## 4. User Stories & Requirements

### 4.1 Functional Requirements

**FR-1**: Load Pre-trained Model
- System loads `best_model_quantized.onnx` at startup
- Model cached in memory for performance
- Graceful fallback if model unavailable

**FR-2**: Real-Time Liveness Evaluation
- Evaluate liveness for each detected face
- Return score 0.0 (spoof) to 1.0 (real)
- Max latency: 50ms per face at 640×480

**FR-3**: Threshold-Based Decision
- Compare score against configurable threshold (default 0.5)
- If score < threshold: emit SPOOF_WARNING event
- If score >= threshold: proceed to recognition

**FR-4**: Graceful Degradation
- If model fails to load: disable anti-spoofing with warning
- If inference fails: return 0.0 (reject as spoof for safety)
- Never crash, always provide fallback

### 4.2 Non-Functional Requirements

**NFR-1**: Performance
- Inference: <50ms per face on Intel i7 CPU
- Model load: <2 seconds
- Memory footprint: <100 MB (model + buffers)

**NFR-2**: Reliability
- 99%+ uptime (graceful fallback on error)
- No memory leaks on continuous operation

**NFR-3**: Security
- Model path configurable via environment variable
- No hardcoded paths in source code
- All evaluations logged for audit trail

**NFR-4**: Compatibility
- Python 3.11+
- Works on Windows, Linux, macOS
- GPU optional (CPU-only is primary)

---

## 5. Configuration & Settings

### 5.1 Environment Variables

```env
# Enable/disable anti-spoofing
FACE_ANTISPOOF_ENABLED=true

# Path to ONNX model
FACE_ANTISPOOF_MODEL_PATH=models/anti_spoof/best_model_quantized.onnx

# Threshold for liveness (0.0-1.0)
FACE_ANTISPOOF_CONFIDENCE_THRESHOLD=0.5
```

### 5.2 Session Configuration
- `liveness_threshold_snapshot` (already exists in `sessions` table)
- Default: 0.5 (50% confidence minimum)
- Adjustable per session by operators

### 5.3 Model Specifications
- **Input Size**: 128×128 RGB
- **Preprocessing**: Normalization to [0, 1]
- **Output**: 2 logits [real_logit, spoof_logit]
- **Postprocessing**: Softmax/sigmoid → probability

---

## 6. Integration Points

### 6.1 Modified Modules

**src/services/ai_backends.py**
- Replace `create_liveness_evaluator()` to use real model
- Remove dummy implementation warning

**src/core/config.py**
- Add FACE_ANTISPOOF_ENABLED, FACE_ANTISPOOF_MODEL_PATH, FACE_ANTISPOOF_CONFIDENCE_THRESHOLD

**pyproject.toml**
- Ensure onnxruntime>=1.16.0 in dependencies

### 6.2 New Modules

**src/services/antispoof_service.py**
```python
class AntiSpoofService:
    def __init__(self, model_path: str | Path, enabled: bool)
    def load(self) -> bool
    def evaluate(self, face: dict[str, Any]) -> float
    def _preprocess(self, face_img: np.ndarray) -> np.ndarray
    def _postprocess_logits(self, logits: np.ndarray) -> float
```

**tools/download_antispoof_models.py**
- Download `best_model_quantized.onnx` from GitHub releases
- Verify checksums
- Extract to `models/anti_spoof/`

### 6.3 Existing Integrations (No Changes)

**src/services/vision_pipeline_service.py**
- Uses liveness_evaluator callback
- Already handles threshold check
- No changes needed (interface compatible)

**src/models/entities.py**
- VisionEventType already has SPOOF_WARNING
- No changes needed

---

## 7. Technical Implementation Details

### 7.1 Model Preprocessing

```python
def _preprocess(self, face_img: np.ndarray) -> np.ndarray:
    """
    Convert face image to model input format.
    
    Input: Any size BGR or RGB image (H, W, C) uint8
    Output: (1, 3, 128, 128) float32 [0, 1]
    """
    # 1. Resize to 128×128 (preserve aspect, pad if needed)
    # 2. Ensure RGB format (convert BGR if needed)
    # 3. Normalize to [0, 1] (divide by 255)
    # 4. Add batch dimension (1, 3, 128, 128)
    # 5. Ensure NCHW format for ONNX
```

### 7.2 Model Inference

```python
def evaluate(self, face: dict[str, Any]) -> float:
    """
    1. Extract face image: face['face']
    2. Preprocess to 128×128 RGB
    3. Run ONNX inference:
       - Input: preprocessed image
       - Output: [real_logit, spoof_logit]
    4. Compute probability:
       - real_logit - spoof_logit = logit_diff
       - sigmoid(logit_diff) = probability
       - Or softmax([real_logit, spoof_logit]) = [p_real, p_spoof]
    5. Return p_real (0.0-1.0)
    """
```

### 7.3 Error Handling

```
Model Load Failure → Log error, fallback (disable anti-spoofing)
Inference Error → Log error, return 0.0 (fail-safe: reject)
Invalid Input → Log warning, return 0.0 (reject)
```

---

## 8. Testing Strategy

### 8.1 Unit Tests

| Test | Purpose | Expected |
|------|---------|----------|
| `test_antispoof_model_loads` | Verify ONNX session created | Session not None |
| `test_antispoof_preprocess_shape` | Verify input shape (1,3,128,128) | Shape matches |
| `test_antispoof_eval_real_face` | Evaluate known real face | Score > 0.7 |
| `test_antispoof_eval_spoof_face` | Evaluate printed photo | Score < 0.3 |
| `test_antispoof_invalid_input` | Handle corrupted image | Returns 0.0, logs error |
| `test_antispoof_disabled` | Disable via config | Returns 1.0 (pass) |
| `test_antispoof_model_missing` | Model file not found | Returns 1.0, logs warning |

### 8.2 Integration Tests

| Test | Purpose | Expected |
|------|---------|----------|
| `test_pipeline_spoof_warning` | Spoof detected → SPOOF_WARNING event | Event emitted |
| `test_pipeline_real_recognition` | Real face → proceeds to recognition | Recognizer called |
| `test_pipeline_disabled_antispoof` | Anti-spoof disabled → all pass | No spoof warnings |

### 8.3 Performance Tests

| Test | Target | Acceptable |
|------|--------|-----------|
| Model load time | <2 sec | <5 sec |
| Inference per face | <50 ms | <100 ms |
| FPS impact | <10% drop | <20% drop |
| Memory usage | <100 MB | <200 MB |

---

## 9. Acceptance Criteria

### Phase: Development Complete
- [ ] AntiSpoofService created with full coverage
- [ ] Unit tests passing (>90% code coverage)
- [ ] ai_backends.py updated and tested
- [ ] Integration tests passing
- [ ] Performance benchmarks met

### Phase: Code Review
- [ ] Code review approved
- [ ] No hardcoded paths or credentials
- [ ] Error handling verified
- [ ] Documentation complete

### Phase: Testing Complete
- [ ] Real face recognized (liveness >= threshold)
- [ ] Spoof face rejected (liveness < threshold)
- [ ] Graceful fallback when model unavailable
- [ ] No performance regression

### Phase: Production Ready
- [ ] Deployment checklist completed
- [ ] Models downloaded and verified
- [ ] Environment variables configured
- [ ] Smoke tests passed
- [ ] Monitoring/logging validated

---

## 10. Risk & Mitigation

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|-----------|
| Model not available | Feature disabled | Medium | Graceful fallback, clear error |
| False positives (reject real) | User frustration | Medium | Tunable threshold, logging |
| False negatives (accept spoof) | Security breach | Low | Conservative default (0.5), audit logs |
| Performance drop | UX degradation | Medium | Quantized model, benchmarking |
| GPU/ONNX compatibility | Runtime error | Low | Pin versions, test matrix |

---

## 11. Success Metrics

- **Security**: Zero known spoof bypass attacks
- **Performance**: <10% FPS impact vs dummy evaluator
- **Reliability**: 99%+ uptime with graceful fallback
- **Usability**: Tunable threshold per session
- **Auditability**: All evaluations logged for review

---

## 12. Future Enhancements

1. **Multi-Modal Liveness**: Combine face movement + anti-spoof
2. **Challenge-Response**: Request user actions (blink, turn head)
3. **Adversarial Robustness**: Defense against adversarial inputs
4. **Model Updates**: Periodic retraining on new attack patterns
5. **GPU Acceleration**: CUDA/TensorRT optimization
6. **Mobile Deployment**: TensorFlow Lite or CoreML conversion

---

## 13. Glossary

- **Liveness**: Face is alive/present (not photo/video playback)
- **Spoof**: Attack using photo, video, or 3D mask
- **Quantization**: Model compression (float32 → int8) without accuracy loss
- **ONNX**: Open Neural Network Exchange format
- **Logits**: Raw model outputs before softmax
- **Confidence**: Probability score for liveness

---

## 14. References

- MiniFAS Project: https://github.com/facenox/face-antispoof-onnx
- ONNX Runtime: https://onnxruntime.ai/
- Paper: "Silent Face Anti-Spoofing via Fourier Kernels" (Wang et al., 2021)
- CelebA Spoof Dataset: https://github.com/Shifeng-Zhang/CelebA-Spoof

---

**Document Version**: 1.0  
**Last Updated**: 2026-04-30  
**Status**: READY FOR IMPLEMENTATION
