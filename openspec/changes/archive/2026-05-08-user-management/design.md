## Context

Currently, the system is missing the User Management phase (UC-07) defined in the SRS. The application has basic admin UI scaffolding (`AdminDashboardView` with a `QStackedWidget`), but there's no interface or wiring to manage the `User` entities (students and staff). This change introduces `UserManagementWidget`, dialogs for CRUD operations, and handles referential integrity when deleting users (since users are tied to `face_embeddings` and `attendance_logs`).

## Goals / Non-Goals

**Goals:**
- Provide a responsive UI (`UserManagementWidget`) within the admin dashboard to list all users using a `QTableWidget`.
- Support creating, editing, and deleting users via dedicated dialogs.
- Ensure referential integrity when users are deleted (handling related face embeddings and attendance logs).
- Integrate cleanly with the existing `UserRepository` and `Database` session management.

**Non-Goals:**
- Rebuilding the `User` data model or `UserRepository` from scratch (they already exist, though we may need to ensure proper delete logic).
- Implementing bulk imports/exports (out of scope for basic CRUD unless specified).

## Decisions

**1. Delete Strategy: Soft Delete for Historical Accuracy**
- *Decision:* We will implement a "Soft Delete" strategy. When a user is deleted, their `is_active` flag in the `users` table will be set to `0`. We will explicitly delete their `face_references` so they can no longer be recognized by the system. However, their `attendance_records` will be preserved so that historical attendance data remains intact.
- *Rationale:* Business logic requires that historical attendance data is not lost when a user is removed from the active roster.

**2. UI Architecture: Data Grid & Dialogs**
- *Decision:* Use `QTableWidget` for listing users. Use modal `QDialog` for "Add User" and "Edit User". The `UserManagementWidget` will manage the table state and spawn these dialogs.
- *Rationale:* Standard PyQt5 pattern that provides a clean user experience and isolates form logic from list presentation.

**3. Data Binding & Refresh**
- *Decision:* The table will be re-populated directly from `UserRepository` upon any successful CRUD operation.
- *Rationale:* Ensures the UI always reflects real-time database changes without complex state synchronization.

## Risks / Trade-offs

- *Risk:* Hard deleting a user deletes crucial historical attendance data due to SQLite cascade constraints.
  *Mitigation:* The "Delete User" functionality will use a soft-delete mechanism (`is_active = 0`), which bypasses the cascading delete for attendance records while safely removing face embeddings to prevent future access.
- *Risk:* Table performance with a massive number of users.
  *Mitigation:* `QTableWidget` can handle thousands of rows comfortably. If it becomes a bottleneck, we might switch to `QTableView` with a custom `QAbstractTableModel`, but `QTableWidget` is sufficient for the initial implementation.
