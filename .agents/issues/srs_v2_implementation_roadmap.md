# SRS V2.0 Implementation Roadmap: Admin Features & Gap Closure

This document outlines the step-by-step implementation plan to resolve the missing features identified in the SRS v2.0 gap analysis. The plan is organized in logical phases to ensure smooth integration without breaking the existing User Mode (IDLE/ACTIVE).

## Phase 1: Authentication & UI Restructuring (UC-06)
**Goal**: Establish a secure Admin mode and restructure the main window to support navigation between User and Admin modes.
- [x] Create `LoginWidget` UI component with Username and Password fields.
- [x] Implement `AuthenticationService` with bcrypt password verification against `admin_credentials` (or `users` with admin role).
- [x] Refactor `MainWindow` to use a master `QStackedWidget` for switching between `LoginView`, `UserModeView` (the current UI), and `AdminDashboardView`.
- [x] Add a hidden/small "Admin Login" button or shortcut in the `UserModeView` to access the login screen.
- [x] Create a basic `AdminDashboardView` skeleton with a sidebar navigation menu (Users, Enrollment, History, Settings).
- [x] Implement secure Logout functionality to return to `UserModeView`.

## Phase 2: System Configuration (UC-10)
**Goal**: Allow admins to configure hardware and AI parameters directly from the UI.
- [x] Create `SettingsWidget` UI component in the Admin Dashboard.
- [x] Implement Camera selection dropdown (scanning available `cv2.VideoCapture` indices).
- [ ] Add UI sliders/input fields for `Liveness Threshold` (e.g., 0.1 to 1.0) and `Similarity Threshold`.
- [x] Wire the UI to `SettingsService` to read/write values to the `system_settings` table.
- [x] Ensure the main attendance pipeline dynamically respects these settings when starting a new session.

## Phase 3: User Management (UC-07)
**Goal**: Implement CRUD operations for students/staff.
- [x] Create `UserManagementWidget` UI component with a Data Grid (`QTableWidget`).
- [x] Implement "Add User" dialog (Student ID, Full Name).
- [x] Implement "Edit User" dialog.
- [x] Implement "Delete User" logic with confirmation warnings (and cascade delete or soft delete for related embeddings/attendance).
- [x] Wire the UI to `UserRepository` to reflect real-time database changes.

## Phase 4: Face Enrollment - Biometric Registration (UC-08)
**Goal**: Provide a robust, guided UI for capturing reference faces and generating embeddings.
- [ ] Create `EnrollmentWidget` UI component in the Admin Dashboard.
- [ ] Add a user selection dropdown/search to pick which user to enroll.
- [ ] Implement an `EnrollmentCameraThread` (separate from the attendance thread) to stream video for enrollment.
- [ ] Add visual guidance text overlays ("Nhìn thẳng", "Xoay nhẹ trái/phải").
- [ ] Implement auto-capture logic in `ai_pipeline.py` or `EnrollmentService` (e.g., capture 3-5 high-quality frames automatically when a face is steady and liveness passes).
- [ ] Calculate the *Average Embedding* from the captured frames.
- [ ] Save the embedding blob via `EnrollmentService` and mark `face_registered = 1` in the `users` table.

## Phase 5: Attendance History (UC-09) & Reporting (UC-11)
**Goal**: Allow admins to review past sessions and export data.
- [ ] Create `AttendanceHistoryWidget` UI component.
- [ ] Build a split view: Left side for "Session List", right side for "Session Details (Records)".
- [ ] Implement database queries in `AttendanceService` to fetch sessions and their associated attendance logs.
- [ ] Add a date range filter and class/subject filter for the Session List.
- [ ] Implement "Export to Excel" functionality using `pandas` or `openpyxl`.
- [ ] Implement "Export to CSV" functionality.
- [ ] Add an "Export" button in the Session Details view that triggers the file save dialog and writes the report.

## Phase 6: Final Polish & Testing
**Goal**: Ensure all new components work harmoniously and meet SRS performance requirements.
- [ ] Conduct integration testing between Admin Mode and the existing User Mode (ensure camera releases properly between views).
- [ ] Perform UI/UX review (fonts, colors, spacing) to match the existing `_FONT_BODY`, `_FONT_TITLE` design system.
- [ ] Test the Excel/CSV export files for correct formatting and data accuracy.
- [ ] Verify that FAR/FRR requirements are maintained when using the newly enrolled average embeddings.
