# scripts/

## Responsibility

Standalone utility scripts for maintenance, debugging, and database management. These are not part of the main application entry points (`attendance-app`, `attendance-storage-init`) and are intended to be run manually by a developer or administrator.

## Scripts

### `reset_users.py`

**Purpose:** Deletes all users and face references from the database while preserving attendance records and recognition events for historical tracking.

**Usage:**
```bash
PYTHONPATH=src python scripts/reset_users.py
```

**Behavior:**
1. Reads `DATABASE_PATH` from `.env` (defaults to `attendance.db`).
2. Prints a summary of what will be deleted vs. preserved.
3. Prompts for interactive confirmation (must type `YES`).
4. Deletes rows from `face_references` first (to respect the FK constraint against `users`), then from `users`.
5. Attendance/recognition tables are left untouched.
