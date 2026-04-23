# AGENTS.md

See also: CLAUDE.md for behavioral guidelines.

## Project

Python desktop face attendance system with anti-spoofing. Currently implementing the database storage core module.

**Stack**: Python 3.11+, SQLite3 (WAL mode), bcrypt
**Source**: `src/core/` (db, schema, storage_manager), `src/models/`, `src/repositories/`, `src/services/`
**Tests**: `tests/unit/`, `tests/integration/`

## Constitution

Located at `.specify/memory/constitution.md`. Must be checked in every plan/spec/task.

Key principles: Attendance Integrity First, Privacy by Design (store embeddings only, hash admin credentials), Offline-First, Deterministic AI Pipeline, Measurable Quality Gates.

## Running Tests

```bash
pytest tests/
pytest tests/unit/
pytest tests/integration/
```

## Module Structure

- `src/core/` - Database connection (SQLite WAL, foreign keys), schema initialization
- `src/models/entities.py` - Data classes (User, FaceReference, Session, etc.)
- `src/repositories/` - Database access layer (CRUD operations per entity)
- `src/services/` - Business logic (enrollment, attendance, security, settings)

## Database Schema

Tables: `users`, `admin_credentials`, `face_references`, `sessions`, `recognition_events`, `attendance_records`, `system_settings`

Key constraints: `UNIQUE (session_id, user_id)` on attendance_records, foreign keys with CASCADE/SET NULL.

## Speckit Workflow (PowerShell)

```
.specify/scripts/powershell/check-prerequisites.ps1
.specify/scripts/powershell/create-new-feature.ps1
.specify/scripts/powershell/setup-plan.ps1
```

Branch naming: `NNN-feature-name` or `YYYYMMDD-HHMMSS-feature-name`

## Spec Files

- `specs/001-database-storage-core/spec.md` - Feature specification
- `specs/001-database-storage-core/plan.md` - Implementation plan
- `docs/srs/srs_2.md` - Full SRS requirements