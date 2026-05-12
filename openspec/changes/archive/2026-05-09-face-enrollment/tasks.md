## 1. UI Components Setup

- [x] 1.1 Create `EnrollmentWidget` in `src/attendance_system/ui/`.
- [x] 1.2 Implement user selection dropdown in `EnrollmentWidget`.
- [x] 1.3 Add camera feed layout and control buttons (Start/Stop Enrollment) to `EnrollmentWidget`.

## 2. Enrollment Service & Logic

- [x] 2.1 Update or Create `EnrollmentService` in `src/attendance_system/services/`.
- [x] 2.2 Add method in service/AI logic to calculate Average Embedding from multiple face frames.
- [x] 2.3 Add method to save the final embedding blob and update `face_registered = 1` in the database.

## 3. Camera & AI Integration

- [x] 3.1 Implement `EnrollmentCameraThread` to handle video streaming separately from main attendance.
- [x] 3.2 Add visual guidance text overlays logic ("Nhìn thẳng", "Xoay nhẹ trái/phải") on frames.
- [x] 3.3 Implement auto-capture logic to automatically buffer 3-5 high-quality, steady faces that pass the liveness check.

## 4. Wiring and Integration

- [x] 4.1 Integrate `EnrollmentWidget` into `AdminDashboardView`.
- [x] 4.2 Connect UI buttons to start/stop the `EnrollmentCameraThread` and ensure resources are handled correctly.
- [x] 4.3 Trigger the save logic in `EnrollmentService` when auto-capture is complete, then reset the UI.
