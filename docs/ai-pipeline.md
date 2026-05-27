# AI Pipeline

Four ONNX models orchestrated across two camera threads.

## Model Inventory

| Model | File | Task | Input Shape | Output |
|-------|------|------|-------------|--------|
| **YuNet** | `face_detection_yunet_2023mar.onnx` | Face detection | Variable (640×480 default) | [N×15] detection rows |
| **SFace** | `face_recognition_sface_2021dec.onnx` | Face recognition | Variable (aligned crop) | 128-dim embedding |
| **MiniFASNet** | `best_model_quantized.onnx` | Liveness detection | [1,3,128,128] float32 | [1,2] logits |
| **MobileNetV2** | `mobilenetv2.onnx` | Head-pose estimation | [1,3,224,224] float32 | 3×3 rotation matrix |

> Models are gitignored — download separately. Default paths in `models/`.

## Liveness Checker (`LivenessChecker`)

**Module**: `attendance_system/services/ai_pipeline.py`

### Preprocessing (`_preprocess`)
1. Scale longest side to 128px (LANCZOS4 if upscaling, AREA if downscaling)
2. Pad shorter side with `BORDER_REFLECT_101` to make 128×128 square
3. Convert HWC uint8 → CHW float32 in [0, 1]

### Inference
```python
raw = session.run(None, {input_name: arr})  # → [1, 2] logits
logit_diff = output[0][0] - output[0][1]     # positive → real, negative → spoof
```

### Threshold
Threshold is expressed as probability (0–1) but compared in logit space:
```python
logit_threshold = log(p / (1 - p))  # inverse sigmoid
is_real = logit_diff > logit_threshold
```

### Bypass
When `FACE_ANTISPOOF_ENABLED=false` (or `model_path=None`), every face is treated as real:
```python
if self._session is None:
    return LivenessResult(is_real=True, score=1.0)
```

## Face Recognizer (`FaceRecognizer`)

**Module**: `attendance_system/services/ai_pipeline.py`

### Feature Extraction (`get_embedding`)
1. `sface.alignCrop(frame_bgr, yunet_face_row)` — aligns face using YuNet landmarks
2. `sface.feature(aligned_face)` — extracts 128-dim embedding
3. Returns `np.float32` embedding normalized to unit length (or `None` on failure)

### Identification (`identify`)
1. Extract live embedding from current frame
2. Cosine similarity against all stored embeddings in `face_references` table
3. Return best match above threshold as `RecognitionResult`, else `None`

### Embedding Averaging (`average_embeddings`)
During enrollment, multiple embeddings are captured at different poses, then averaged:
```python
avg = np.mean(embeddings, axis=0)
avg /= np.linalg.norm(avg)  # re-normalize to unit length
```

## Head-Pose Estimator (`HeadPoseEstimator`)

**Module**: `attendance_system/services/head_pose.py`

### Preprocessing
1. Convert BGR → RGB
2. Resize to 224×224 (bilinear)
3. Normalize with ImageNet mean/std: `(pixel/255 - [0.485,0.456,0.406]) / [0.229,0.224,0.225]`
4. HWC → CHW → add batch dim

### Euler Angle Extraction
The model outputs a 3×3 rotation matrix. Euler angles are extracted:
```python
pitch = atan2(R[2,1], R[2,2])
yaw   = atan2(-R[2,0], sqrt(R[2,1]^2 + R[2,2]^2))
roll  = atan2(R[1,0], R[0,0])
```

### Pose-Guided Enrollment Sequence

```python
_POSE_SEQUENCE = [
    ("Chính diện",     pitch=0,  yaw=0),
    ("Nghiêng trái",   pitch=0,  yaw=-30),
    ("Nghiêng phải",   pitch=0,  yaw=30),
    ("Ngửa lên",       pitch=20, yaw=0),
    ("Cúi xuống",      pitch=-20,yaw=0),
]
```

- Tolerance: ±15° per axis (`_POSE_TOLERANCE_DEG`)
- Hold requirement: 5 consecutive frames (`_HOLD_FRAMES`) at correct pose before capture
- Cooldown: 1 second between captures (`_CAPTURE_COOLDOWN`)
- Target: 5 embeddings (`_target_count`) for averaging

## Circuit-Breaker Pattern

**ADR**: `docs/adr/0001-onnx-circuit-breaker.md`

Both camera threads track consecutive ONNX inference failures:

```python
if self._consecutive_failures >= _MAX_CONSECUTIVE_FAILURES:  # 30
    camera_error.emit("AI model failed after 30 consecutive errors")
    self._running = False
```

- Counter resets on any successful inference
- 30 failures at ~30 fps ≈ 1 second of persistent failure
- Transient glitches (<30) emit `inference_warning` signals without stopping

## Error Handling Hierarchy

```
ONNXInferenceError (base)
├── PoseInferenceError     — head-pose estimation failure
└── LivenessInferenceError — liveness detection failure
```

All carry optional `input_shape` and `model_path` context for diagnostics.

## Enrollment-Specific Details

- Liveness checking is **intentionally bypassed** during enrollment (`LivenessChecker(model_path=None)`)
- Rationale: multi-pose sequence already provides strong implicit anti-spoofing
- Cropping scale differs: enrollment uses `scale=2.7`, head-pose uses `scale=1.5`
- Wrong scale silently rejects real users — this is a known gotcha

## Frame Processing Rate

- Full AI pipeline runs every **3rd frame** (`_AI_FRAME_SKIP=3`)
- At 30 fps camera → ~10 Hz inference rate
- Display frames are rendered every frame (30 fps) with cached bounding boxes
