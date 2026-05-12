## 1. UI Dialogs Implementation

- [x] 1.1 Create `UserDialog` class to handle both "Add" and "Edit" user operations.
- [x] 1.2 Add input fields for "Student ID" and "Full Name" to the dialog, along with validation logic.

## 2. User Management Widget Implementation

- [x] 2.1 Create `UserManagementWidget` class inheriting from `QWidget`.
- [x] 2.2 Add a `QTableWidget` to the layout with columns: ID, Student ID, and Full Name.
- [x] 2.3 Add action buttons below or above the table: "Add User", "Edit User", "Delete User".

## 3. Data Integration and Business Logic

- [x] 3.1 Implement `load_users()` method to fetch all users via `UserRepository` and populate the `QTableWidget`.
- [x] 3.2 Wire the "Add User" button to open `UserDialog`, save the new user via `UserRepository.create()`, and refresh the table.
- [x] 3.3 Wire the "Edit User" button to open `UserDialog` with selected user's data, save changes via `UserRepository.update()`, and refresh the table.
- [x] 3.4 Wire the "Delete User" button to show a `QMessageBox` warning that face data will be deleted but attendance history preserved.
- [x] 3.5 Implement soft-delete logic (`UserRepository.soft_delete()` or updating `is_active`) and explicitly delete `face_references`, then refresh the table.
- [x] 3.6 Update `UserRepository.get_all()` (or `load_users`) to only fetch active users (`is_active = 1`).

## 4. Admin Dashboard Integration

- [x] 4.1 Instantiate `UserManagementWidget` and add it to the `QStackedWidget` in `AdminDashboardView`.
- [x] 4.2 Add a navigation button (e.g., "Manage Users") in `AdminDashboardView` sidebar to switch to the User Management view.
