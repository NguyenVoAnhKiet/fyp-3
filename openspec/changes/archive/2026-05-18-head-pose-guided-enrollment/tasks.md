## 1. Configuration and model wiring

- [ ] 1.1 Add head-pose configuration surface in `src/main.py` (`--headpose-model`, `FACE_HEADPOSE_MODEL_PATH`, `FACE_HEADPOSE_ENABLED`) with defaults and path resolution.
- [ ] 1.2 Update startup initialization to construct `HeadPoseEstimator` only when enabled and model path is valid, then pass it into `MainWindow`.
- [ ] 1.3 Document new environment variables in `.env.example`.

## 2. Head pose estimation service

- [ ] 2.1 Create `src/attendance_system/services/head_pose.py` with `HeadPoseEstimator` session setup and model I/O metadata handling.
- [ ] 2.2 Implement preprocessing (BGR->RGB, resize to 224x224, ImageNet normalization) and inference execution.
- [ ] 2.3 Implement rotation-matrix to Euler-angle conversion and expose `estimate(face_crop_bgr) -> (pitch, yaw, roll)`.

## 3. UI dependency injection updates

- [ ] 3.1 Update `MainWindow` constructor and wiring to accept and forward `head_pose_estimator`.
- [ ] 3.2 Update `AdminDashboardView` to accept and forward `head_pose_estimator` into `EnrollmentWidget`.
- [ ] 3.3 Update `EnrollmentWidget` and `EnrollmentCameraThread` constructors to receive optional head pose estimator consistently.

## 4. Enrollment pose-gated workflow

- [ ] 4.1 Add pose sequence definitions (frontal, left tilt, right tilt, tilt up, tilt down) with target yaw/pitch and tolerance in `EnrollmentCameraThread`.
- [ ] 4.2 Implement pose-state tracking (`current_pose_index`, hold-frame counter) and enforce hold-to-capture gating.
- [ ] 4.3 Integrate pose gating with existing liveness and embedding checks so failed quality checks do not advance pose.
- [ ] 4.4 Emit and render real-time guidance (required pose label, current angles, hold progress, correction direction) in frame/UI status updates.

## 5. Backward-compatible fallback behavior

- [ ] 5.1 Preserve legacy enrollment behavior when head pose is disabled by configuration.
- [ ] 5.2 Preserve legacy enrollment behavior when head pose estimator cannot initialize and emit user-visible warning/status message.
- [ ] 5.3 Ensure attendance flow and non-enrollment camera usage paths remain unchanged.

## 6. Verification and regression coverage

- [ ] 6.1 Add/extend unit tests for Euler-angle conversion and pose matching threshold behavior.
- [ ] 6.2 Add/extend integration tests for pose-sequence advancement, hold reset on mismatch, and fallback mode.
- [ ] 6.3 Run project lint and tests, then resolve regressions caused by pose-guided enrollment changes.
