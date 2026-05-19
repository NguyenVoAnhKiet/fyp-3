## Why

Current enrollment accepts five face captures without enforcing head orientation, which weakens sample diversity and can reduce recognition robustness. We need pose-guided enrollment now to collect a consistent multi-angle reference set while keeping enrollment usable in real time.

## What Changes

- Add ONNX-based head pose estimation to enrollment camera processing.
- Enforce five required poses in sequence before each capture: frontal, left tilt, right tilt, tilt up, tilt down.
- Show real-time pose angles and directional guidance in enrollment UI.
- Gate capture on pose hold criteria plus existing liveness and embedding checks.
- Keep a fallback path to existing enrollment behavior when head pose is disabled or unavailable.

## Capabilities

### New Capabilities
- `head-pose-guided-enrollment`: Enforce pose-sequenced enrollment with real-time pose feedback and compatibility fallback.

### Modified Capabilities
- None.

## Impact

- Affected code: `src/main.py`, `src/attendance_system/services/`, and enrollment UI threading/widgets under `src/attendance_system/ui/`.
- New model asset expectation: `models/head_pose/mobilenetv2.onnx` resolved via CLI/env configuration.
- No database schema changes; existing embedding storage pipeline remains.
- Runtime dependency surface remains unchanged (uses existing ONNX Runtime stack).
