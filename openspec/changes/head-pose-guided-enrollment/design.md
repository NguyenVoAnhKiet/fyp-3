## Context

The enrollment flow currently captures five images with lightweight 2D guidance and does not enforce view diversity. The project already uses ONNX Runtime for anti-spoofing and face models, with camera processing in `EnrollmentCameraThread` and UI composition through `MainWindow -> AdminDashboardView -> EnrollmentWidget`.

This change introduces head-pose-gated enrollment across multiple layers: startup configuration (`main.py`), a new pose estimation service, and enrollment thread/UI behavior. Constraints include preserving current attendance behavior, avoiding new runtime dependencies, and maintaining real-time camera responsiveness on Windows.

## Goals / Non-Goals

**Goals:**
- Enforce five required poses in a fixed sequence during enrollment when head pose is enabled.
- Provide clear real-time guidance based on estimated pitch/yaw and required target pose.
- Keep compatibility fallback to existing enrollment behavior if head pose is disabled or model is unavailable.
- Reuse existing ONNX Runtime stack and avoid schema/storage changes.

**Non-Goals:**
- Changing attendance (user mode) behavior.
- Modifying liveness decision logic or face recognition embedding format.
- Persisting per-frame pose telemetry to the database.

## Decisions

### 1. Add a dedicated `HeadPoseEstimator` service
- **Decision:** Implement a new service in `src/attendance_system/services/head_pose.py` that wraps ONNX Runtime, preprocessing, and Euler angle conversion.
- **Why:** Keeps model concerns out of UI/thread classes, matches existing service-oriented boundaries, and is testable in isolation.
- **Alternatives considered:** Embedding inference directly in `EnrollmentCameraThread` (rejected due to coupling and harder testing).

### 2. Gate enrollment capture through pose sequence state machine
- **Decision:** Extend `EnrollmentCameraThread` with pose definitions, current pose index, and hold-frame counter; capture only when current pose is within tolerance for required consecutive frames.
- **Why:** The thread already owns frame-by-frame inference and capture control, so this is the smallest coherent place for deterministic gating.
- **Alternatives considered:** Moving state machine to widget/UI (rejected due to frame-timing sensitivity and extra signal churn).

### 3. Keep fallback path as first-class behavior
- **Decision:** Treat head pose as optional at runtime via env/CLI toggle and model path checks. If disabled/unavailable, enrollment reuses existing five-capture behavior.
- **Why:** Prevents hard dependency on an external model file and preserves operability in existing deployments.
- **Alternatives considered:** Hard fail when model missing (rejected because it blocks enrollment and violates backward-compatibility goal).

### 4. Surface guidance primarily in enrollment UI/thread signals
- **Decision:** Emit pose status, target pose label, and current angles from thread to widget for display, while retaining frame overlay for immediate feedback.
- **Why:** Users need actionable guidance without reading logs; existing signal-based UI update flow supports this naturally.
- **Alternatives considered:** Overlay-only guidance (rejected as insufficient for accessibility/readability in some camera conditions).

## Risks / Trade-offs

- [Head pose estimation noise near thresholds] -> Use tolerance margins and hold-frame requirement before capture.
- [Per-frame inference latency impacts camera smoothness] -> Reuse single ONNX session, keep preprocessing minimal, and skip pose gating in fallback mode.
- [Model file missing or misconfigured] -> Explicit startup/runtime validation and graceful fallback messaging.
- [Pose instructions misunderstood by users] -> Use localized directional guidance text and live angle display.

## Migration Plan

1. Add model path and enable/disable configuration in `.env.example` and CLI wiring in `main.py`.
2. Introduce `HeadPoseEstimator` service and inject it through existing UI constructor chain.
3. Update enrollment thread/widget behavior to enforce pose sequence when estimator is present.
4. Keep and verify fallback mode parity when estimator is absent or disabled.
5. Rollback strategy: disable `FACE_HEADPOSE_ENABLED` to instantly revert to legacy enrollment flow without schema/code migration.

## Open Questions

- Whether tolerance and hold-frame thresholds should become configurable beyond initial fixed values.
- Whether to expose roll angle in UI or keep guidance focused on yaw/pitch only.
