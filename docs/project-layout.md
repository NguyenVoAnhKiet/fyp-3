# Project Layout

The repository is organized with a clear package structure under `src/attendance_system/` for the face attendance system.

```text
src/
└── attendance_system/      # Main application package
    ├── core/               # SQLite connection, schema initialization, storage bootstrap
    ├── models/             # Data classes and entity definitions
    ├── repositories/       # Database CRUD and persistence helpers
    ├── services/           # Business logic built on repositories
    ├── ui/                 # UI-facing code and presentation helpers
    └── utils/              # Shared utility functions
```

## Runtime Entry Point

- Install or run the bootstrap command through the project script `attendance-storage-init`
- Or invoke the module directly with `python -m attendance_system.core.bootstrap --database-path attendance.db`

## Module Imports

All imports use the explicit `attendance_system` package prefix:
- `from attendance_system.core.db import Database`
- `from attendance_system.repositories.user_repository import UserRepository`
- `from attendance_system.services.attendance_service import AttendanceService`

## Notes

- The source tree uses a `src` source root with `attendance_system` as the application package, keeping imports explicit and avoiding namespace pollution.
- Database initialization is idempotent and only creates the schema defined in `src/attendance_system/core/schema.py`.
- No business logic was altered; this change only standardized package naming and import paths for clarity and maintainability.
