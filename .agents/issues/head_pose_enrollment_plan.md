# Head Pose Guided Enrollment - Implementation Plan

## Overview

Upgrade the biometric enrollment feature (UC-08) from simple 5-frontal-face capture to a pose-guided enrollment system where the AI model requires the user to perform 5 specific head poses before capturing each photo.

## Background

**Current Enrollment Flow:**
- Captures 5 face images with 1-second cooldown between captures
- Uses simple 2D heuristic (nose position ratio) for basic guidance
- No 3D head pose estimation
- User can be in any orientation - only frontal faces are implicitly expected

**Required Enrollment Flow:**
- User must perform 5 specific poses in order: frontal, left tilt, right tilt, tilt up, tilt down
- AI model verifies correct pose using head pose estimation before allowing capture
- Real-time visual feedback shows current pose, angles, and guidance
- Enforced capture: wrong pose = no capture until correct pose is held

## Scope

- Add head pose estimation using MobileNetV2 ONNX model
- Modify enrollment flow to require specific poses in sequence
- Update UI to show pose guidance and real-time angles
- Maintain backward compatibility (head pose can be disabled)

## Non-Scope

- Attendance flow (User Mode) remains unchanged
- Face recognition and liveness detection logic unchanged
- Database schema unchanged (still stores averaged embedding)

---

## Model Selection

**Chosen Model:** yakhyo/head-pose-estimation - MobileNetV2 ONNX
- Size: 8.5 MB
- Accuracy: ~5.7° MAE on AFLW2000
- Input: 224×224 RGB face crop, ImageNet normalized
- Output: Rotation matrix (3×3) → Euler angles (pitch, yaw, roll) in degrees
- Dependencies: None new (uses existing `onnxruntime`)

**Download URL:**
```
https://github.com/yakhyo/head-pose-estimation/releases/download/weights/mobilenetv2.onnx
```

**Target Location:** `models/head_pose/mobilenetv2.onnx`

---

## Pose Definitions

| # | Pose Name | Vietnamese | Yaw Target | Pitch Target | Tolerance |
|---|-----------|------------|-----------|--------------|-----------|
| 1 | Frontal | Chính diện | 0° | 0° | ±15° |
| 2 | Left Tilt | Nghiêng trái | -30° | 0° | ±15° |
| 3 | Right Tilt | Nghiêng phải | +30° | 0° | ±15° |
| 4 | Tilt Up | Ngửa lên | 0° | -22° | ±15° |
| 5 | Tilt Down | Cúi xuống | 0° | +22° | ±15° |

**Capture Criteria:**
- Hold correct pose for 5 consecutive frames (~0.17s at 30fps)
- Liveness check must pass
- Embedding extracted successfully

---

## File Changes

### New Files

| File | Purpose |
|------|---------|
| `src/attendance_system/services/head_pose.py` | HeadPoseEstimator class - ONNX Runtime wrapper |

### Modified Files

| File | Changes |
|------|---------|
| `src/main.py` | Add `--headpose-model` CLI arg, `FACE_HEADPOSE_MODEL_PATH` env var, `HEADPOSE_ENABLED` toggle, create HeadPoseEstimator, pass to MainWindow |
| `src/attendance_system/ui/main_window.py` | Accept `head_pose_estimator` parameter, pass to AdminDashboardView |
| `src/attendance_system/ui/admin_dashboard_view.py` | Accept `head_pose_estimator` parameter, pass to EnrollmentWidget |
| `src/attendance_system/ui/enrollment_widget.py` | Accept `head_pose_estimator`, pass to EnrollmentCameraThread, update UI for pose guidance |
| `src/attendance_system/ui/enrollment_camera_thread.py` | Add state machine for pose tracking, pose validation logic, hold counter, real-time angle display |
| `.env.example` | Add `FACE_HEADPOSE_MODEL_PATH` and `FACE_HEADPOSE_ENABLED` |

---

## Implementation Steps

### Step 1: Create HeadPoseEstimator Class
- [ ] Implement `HeadPoseEstimator` in `head_pose.py`
- [ ] Follow pattern of `LivenessChecker` (ONNX Runtime initialization)
- [ ] Preprocess: BGR→RGB, resize to 224×224, ImageNet normalize (mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
- [ ] Postprocess: rotation matrix to Euler angles conversion
- [ ] Method: `estimate(face_crop_bgr) -> (pitch, yaw, roll)` in degrees

### Step 2: Wire Head Pose Model in Main
- [ ] Add `DEFAULT_HEADPOSE_MODEL = Path("models/head_pose/mobilenetv2.onnx")`
- [ ] Add CLI arg `--headpose-model`
- [ ] Add env var resolution for `FACE_HEADPOSE_MODEL_PATH`
- [ ] Add optional toggle `FACE_HEADPOSE_ENABLED` (default: true)
- [ ] Validate model path exists (if enabled)
- [ ] Create `HeadPoseEstimator` instance
- [ ] Pass to MainWindow

### Step 3: Pass Through UI Layers
- [ ] MainWindow: add `head_pose_estimator` param, pass to AdminDashboardView
- [ ] AdminDashboardView: add `head_pose_estimator` param, pass to EnrollmentWidget
- [ ] EnrollmentWidget: add `head_pose_estimator` param, pass to EnrollmentCameraThread

### Step 4: Update EnrollmentCameraThread State Machine
- [ ] Add pose definitions constant array (5 poses with yaw/pitch targets)
- [ ] Add state variables: `_current_pose_idx`, `_pose_hold_counter`
- [ ] Add constant: `HOLD_FRAMES = 5`
- [ ] Modify `run()` loop:
  - After face detection, estimate head pose
  - Check if current pitch/yaw matches required pose
  - If match: increment hold counter, check if >= HOLD_FRAMES
  - If hold >= 5: attempt capture (liveness + embedding)
  - If capture success: advance pose, reset counter, emit progress
  - If mismatch: reset counter, show guidance
- [ ] Add guidance logic: determine which direction to move based on error
- [ ] Add overlay rendering: pose name, angles, hold progress, guidance text
- [ ] Update status text logic for new flow

### Step 5: Update EnrollmentWidget UI
- [ ] Add pose-specific progress label (e.g., "📸 Ảnh 2/5: Nghiêng trái")
- [ ] Update progress bar to reflect pose index
- [ ] Add angle display (optional, or keep on frame overlay)

### Step 6: Backward Compatibility
- [ ] If `head_pose_estimator` is None, revert to old behavior (5 frontal captures, simple nose-ratio guidance)
- [ ] Handle missing model gracefully with warning message
- [ ] Allow disable via env var

### Step 7: Testing
- [ ] Unit test: HeadPoseEstimator angle conversion
- [ ] Integration test: full enrollment flow with head pose
- [ ] Test edge cases: rapid pose changes, borderline angles

---

## UI/UX Design

### Camera Frame Overlay
```
┌─────────────────────────────────────────────┐
│ [BBox: Green=Correct | Yellow=Wrong]        │
│                                             │
│  Yaw: -28°  Pitch: 3°    ← Real-time angles │
│                                             │
│              [FACE IMAGE]                   │
│                                             │
│  📸 Ảnh 2/5: Nghiêng trái                   │
│  ████████░░░░░░ Hold: 3/5                   │
│                                             │
│  ← Hãy quay sang trái một chút             │
└─────────────────────────────────────────────┘
```

### Status Messages by State
- No face detected: "Không tìm thấy khuôn mặt"
- Wrong pose: "Hãy thực hiện: Nghiêng trái ←" or "Ngửa mặt lên ↑"
- Correct pose, holding: "Tốt! Giữ yên... (3/5)"
- Capturing: "✓ Đã chụp!"
- Liveness failed: "⚠ Cảnh báo: Liveness failed"
- Enrollment complete: "Hoàn tất!"

---

## Acceptance Criteria

1. **Pose Detection:** System correctly identifies when user is in each of the 5 required poses within ±15° tolerance
2. **Pose Enforcement:** Capture only occurs when pose is held for 5+ consecutive frames AND liveness passes
3. **User Guidance:** Clear visual feedback showing current pose, required pose, and direction to adjust
4. **Backward Compatibility:** When head pose model is disabled, enrollment falls back to old behavior
5. **Performance:** No noticeable lag in camera feed (head pose inference < 50ms per frame)
6. **Storage:** Final embedding stored in same format as before (128-dim averaged embedding)

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Head pose model accuracy insufficient | Users may struggle to get correct pose | Use ±15° tolerance, show real-time feedback |
| Extreme lighting affects detection | Face not detected, enrollment stuck | Keep existing liveness check as secondary validation |
| Model file missing | App crashes or broken enrollment | Make head pose optional, warn but allow fallback |
| User moves too fast between poses | Extended enrollment time | Show clear guidance, optimize inference speed |

---

## Dependencies

- **Existing:** `onnxruntime`, `opencv-python`, `numpy`
- **New:** None (MobileNetV2 ONNX uses existing deps)
- **External:** Download `mobilenetv2.onnx` from GitHub releases (~8.5 MB)

---

## Timeline Estimate

- Step 1-3 (Core infrastructure): ~2 hours
- Step 4 (State machine): ~3 hours
- Step 5-6 (UI & compatibility): ~1 hour
- Step 7 (Testing): ~1 hour
- **Total:** ~7 hours

---

## Open Questions

1. Should head pose angles be persisted per-capture for debugging? (No, not in scope)
2. Should we allow configurable pose tolerance? (No, hardcoded for now)
3. What if user cannot perform a pose (e.g., physical limitation)? (Not handled - full 5 poses required)