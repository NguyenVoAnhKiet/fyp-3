## Why

The system needs a robust, guided UI for capturing reference faces and generating biometric embeddings for users (Biometric Registration - UC-08). This is essential for the system to accurately recognize users during the attendance process and must include liveness detection and quality assurance to prevent poor reference data.

## What Changes

- Create `EnrollmentWidget` UI component in the Admin Dashboard.
- Add a user selection dropdown to pick which user to enroll.
- Implement an `EnrollmentCameraThread` (separate from the attendance thread) to stream video for enrollment.
- Add visual guidance text overlays ("Nhìn thẳng", "Xoay nhẹ trái/phải").
- Implement auto-capture logic in `ai_pipeline.py` or `EnrollmentService` (e.g., capture 3-5 high-quality frames automatically when a face is steady and liveness passes).
- Calculate the *Average Embedding* from the captured frames.
- Save the embedding blob via `EnrollmentService` and mark `face_registered = 1` in the `users` table.

## Capabilities

### New Capabilities
- `face-enrollment`: Biometric registration of users, including guided UI, auto-capture of high-quality frames, average embedding calculation, and database storage.

### Modified Capabilities

## Impact

- `src/attendance_system/ui/` (new `EnrollmentWidget` and `EnrollmentCameraThread`)
- `src/attendance_system/services/` (updates or creation of `EnrollmentService`)
- `src/attendance_system/core/ai_pipeline.py` (auto-capture and embedding averaging logic)
- Database updates to save embeddings and mark `face_registered = 1` in the `users` table.
