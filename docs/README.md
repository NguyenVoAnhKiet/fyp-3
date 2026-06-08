# Documentation Index

## Project

Python desktop face attendance system with anti-spoofing. 100% offline, single-process desktop application.

- **Stack**: Python 3.11+, SQLite3 (WAL), bcrypt, PyQt5, ONNX Runtime
- **Package**: `database-storage-core` (`package-dir = {"" = "src"}`)
- **Entry points**: `attendance-app` (GUI), `attendance-storage-init` (DB bootstrap)

## Project Status

**Phase:** Phase 4 (Threshold Tuning) — Implementation Complete, Validation Pending  
**Test Coverage:** 280 tests (250 unit + 30 integration), 100% pass rate ✅  
**All Features:** Implemented (face detection, recognition, liveness, enrollment, UI, DB) ✅  
**Current Blocker:** Awaiting validation data for threshold tuning  

See `PROJECT_STATUS.md` for complete project inventory and current implementation status.

## Documentation Map

```
docs/
├── README.md              ← You are here
├── architecture.md        ← System architecture, layers, threading, startup
├── ai-pipeline.md         ← AI model details, preprocessing, enrollment flow
├── database.md            ← Schema, ERD, access patterns, encryption
├── modules.md             ← Complete module-by-module reference
├── adr/                   ← Architecture Decision Records
│   └── 0001-onnx-circuit-breaker.md
├── plans/                 ← Feature plans (active + archive)
│   ├── README.md          ← Plan conventions + active plans index
│   ├── active/            ← In-flight feature plans (currently empty)
│   └── archive/           ← Completed plans (8 plans, date-prefixed)
├── agents/                ← AI agent engineering conventions
│   ├── domain.md          ← Agent domain navigation
│   ├── issue-tracker.md   ← Issue tracking conventions
│   └── triage-labels.md   ← Triage label definitions
└── srs/
    ├── index.md           ← SRS Table of Contents & overview
    ├── chuong_1.md        ← Chapter 1: Introduction
    ├── chuong_2.md        ← Chapter 2: Theory
    ├── chuong_3.md        ← Chapter 3: System Design
    ├── chuong_4.md        ← Chapter 4: Construction & Evaluation
    └── srs_2.md           ← Software Requirements Specification (Vietnamese)
```

## Quick Start

```bash
pip install -e .                    # Editable install
cp .env.example .env                # Configure environment
attendance-storage-init             # Initialize database
attendance-app                      # Launch application
```

## Quick Navigation

| What | Where |
|------|-------|
| Entry point + config resolution | `src/main.py` |
| Database layer | `src/attendance_system/core/db.py`, `docs/database.md` |
| AI pipeline (liveness + recognition) | `src/attendance_system/services/ai_pipeline.py`, `docs/ai-pipeline.md` |
| AI pipeline (head-pose) | `src/attendance_system/services/head_pose.py` |
| Threads (camera + AI) | `src/attendance_system/ui/camera_worker_base.py` (base classes), `camera_thread.py`, `enrollment_camera_thread.py` |
| UI views | `src/attendance_system/ui/` (11 widgets), `docs/modules.md` |
| Repository layer | `src/attendance_system/repositories/` (7 repos) |
| Service layer | `src/attendance_system/services/` (7 services) |
| Entity models | `src/attendance_system/models/entities.py` |
| Tests (unit) | `tests/unit/` (9 files) |
| Tests (integration) | `tests/integration/` (9 files) |
| Configuration | `.env.example` |
| CLI commands | `pyproject.toml` → `[project.scripts]` |

## Key Architecture Documents

- **[Architecture Overview](architecture.md)** — Layer diagram, startup sequence, threading model, configuration resolution
- **[AI Pipeline](ai-pipeline.md)** — Model details, preprocessing, circuit-breaker pattern, enrollment flow, error handling
- **[Database Design](database.md)** — ERD, schema tables, access patterns, migration strategy, embedding encryption
- **[Module Reference](modules.md)** — Every Python file documented with classes, methods, and responsibilities

## Development

```bash
# Lint
ruff check src/

# Test
pytest tests/
pytest tests/unit/ -v
pytest tests/integration/ -v
```

## Gotchas

See `AGENTS.md` for the full list of known pitfalls:
- `onnxruntime` must be imported BEFORE `PyQt5` (DLL conflicts on Windows)
- `cryptography` is a soft dependency for embedding encryption
- `bootstrap.py` does NOT call `load_dotenv()` (CLI default used instead)
- `_crop_face` scale varies by use case (1.5 for detection, 2.7 for enrollment)
- Enrollment frame is horizontally flipped; attendance frame is not
- Circuit-breaker kills thread after 30 consecutive ONNX failures
