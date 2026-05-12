# Quickstart: Database & Storage Core

## Purpose

Use this checklist to verify the storage core once implementation exists.

## Setup

1. Ensure a Python 3.11+ environment is active.
2. Install project dependencies for the application and test suite.
3. Confirm the SQLite database file can be created in the project workspace.

## Validation Steps

1. Run the storage initialization flow against a fresh database.
2. Confirm the required tables and constraints are created.
3. Restart the application and verify existing records still load.
4. Create a session, record one attendance success, then attempt a duplicate entry for the same learner.
5. Verify the duplicate is blocked and only one final attendance record exists.
6. Complete an enrollment workflow and confirm no raw face images remain in persistent storage.
7. Update a system setting and verify the new value is read back correctly.

## Expected Outcomes

- Core tables initialize successfully on first run.
- Data persists across restart.
- Duplicate attendance is blocked at the storage boundary.
- Only derived biometric data is retained.
- Settings changes persist and remain auditable.

## Troubleshooting

- If initialization fails, check schema creation order and foreign key constraints.
- If duplicates appear, verify the session/user uniqueness rule is enforced in the database layer.
- If raw images persist, inspect the enrollment cleanup path and storage writes.