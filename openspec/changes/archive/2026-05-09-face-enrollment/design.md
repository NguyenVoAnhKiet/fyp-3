## Context

The current system has an AI pipeline capable of face detection, liveness checking, and feature extraction (SFace). However, we lack a formal enrollment process for administrators to register biometric templates (embeddings) for users in the database. This is phase 4 of the roadmap (Biometric Registration - UC-08).

## Goals / Non-Goals

**Goals:**
- Provide a `EnrollmentWidget` for selecting a user and capturing their face.
- Run a separate `EnrollmentCameraThread` to not interfere with the active attendance UI.
- Use the existing `ai_pipeline.py` to auto-capture high-quality faces that pass liveness.
- Generate an average embedding from 3-5 frames for robust matching.
- Save the final embedding blob and mark the user as enrolled.

**Non-Goals:**
- User management (CRUD), which is already handled in UC-07.
- Modifying the core detection models.

## Decisions

- **UI Component**: The `EnrollmentWidget` will sit in the `AdminDashboardView` alongside other admin tools. It needs a dropdown for selecting the user, a camera feed area, and control buttons (Start/Stop Enrollment).
- **Camera Thread**: An `EnrollmentCameraThread` will handle grabbing frames and pushing them through `ai_pipeline.py`. It's kept separate from `CameraThread` (used in IDLE mode) to avoid shared state issues and UI stuttering.
- **Auto-Capture Strategy**: The `EnrollmentCameraThread` or an `EnrollmentService` will automatically buffer valid faces (with liveness score > threshold and good alignment). Once 5 frames are buffered, it averages the embeddings and saves them. This avoids manual "click to capture" errors.
- **Guidance Overlays**: The thread will draw bounding boxes and status text directly on the frame (e.g., "Nhìn thẳng", "Liveness Failed") before emitting it to the UI.

## Risks / Trade-offs

- **Risk: Camera Resource Conflict** -> Both the main attendance UI and the enrollment UI might try to access the camera simultaneously.
  - *Mitigation*: Ensure `CameraThread` is stopped or released when entering the Admin Dashboard or starting `EnrollmentCameraThread`. The current implementation stops the attendance `CameraThread` when transitioning out of User mode.
- **Risk: Poor average embedding** -> Capturing blurry frames.
  - *Mitigation*: Only accept frames with high detection confidence from YuNet and a positive liveness check.
