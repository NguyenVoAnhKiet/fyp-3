## Why

The system needs a way for administrators to manage users (students/staff) directly from the application interface. Implementing Phase 3: User Management (UC-07) fulfills the requirement for CRUD operations on user records, ensuring that the system can enroll, update, and remove users as needed. This is essential for a fully functional attendance tracking system.

## What Changes

- Add a `UserManagementWidget` UI component featuring a data grid (`QTableWidget`) to list all users.
- Implement an "Add User" dialog to capture Student ID and Full Name.
- Implement an "Edit User" dialog to modify existing user details.
- Implement a "Delete User" feature that uses a soft-delete mechanism (setting `is_active = 0`), explicitly removing face embeddings while safely preserving historical attendance records.
- Wire the UI to the existing `UserRepository` to reflect real-time database changes.

## Capabilities

### New Capabilities
- `user-management`: Provides UI and logic for administrators to perform CRUD operations on users, including adding, editing, and deleting students/staff, and handling related records like embeddings and attendance logs.

### Modified Capabilities

## Impact

- **UI**: New views added to the Admin Dashboard (`UserManagementWidget`, Dialogs).
- **Services/Repositories**: `UserRepository` will be utilized more extensively; delete operations must handle foreign key constraints or implement soft deletion for `face_embeddings` and `attendance_logs`.
- **Database**: No schema changes expected unless soft deletes are newly introduced, though cascade behavior needs careful handling.
