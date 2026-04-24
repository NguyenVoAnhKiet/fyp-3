# AGENTS.md

See also: CLAUDE.md for behavioral guidelines.

## Project

Python desktop face attendance system with anti-spoofing.

**Stack**: Python 3.11+, SQLite3 (WAL mode), bcrypt
**Tests**: pytest

## Running Tests

```bash
PYTHONPATH=src pytest tests/
```

## Running Lint

```bash
ruff check src/
```

## Module Structure

- `src/core/` - Database connection, schema initialization
- `src/models/entities.py` - Data classes (User, FaceReference, Session, etc.)
- `src/repositories/` - CRUD operations per entity
- `src/services/` - Business logic (enrollment, attendance, security, settings)

## Database Schema

Tables: `users`, `admin_credentials`, `face_references`, `sessions`, `recognition_events`, `attendance_records`, `system_settings`
Key constraint: `UNIQUE (session_id, user_id)` on attendance_records

## Constitution

Located at `.specify/memory/constitution.md`. Check in every plan/spec/task.

## Speckit Workflow (PowerShell)

```bash
.specify/scripts/powershell/check-prerequisites.ps1
.specify/scripts/powershell/create-new-feature.ps1
.specify/scripts/powershell/setup-plan.ps1
```

Branch naming: `NNN-feature-name` or `YYYYMMDD-HHMMSS-feature-name`

## Known Issues / Fixes

See `.opencode/review-checklist.completed.md` for verified fixes applied to the codebase.