# src/attendance_system/

## Responsibility

Root package of the face-attendance desktop application. Owns the full
attendance pipeline — face detection, anti-spoofing liveness checking,
SFace recognition, enrollment, session management, and the PyQt5 GUI.
All business logic, persistence, and UI live under this tree; the only
entry point (`main.py`) sits one level above.

## Subdirectory Map

| Sub-package | Responsibility |
|---|---|
| `core/` | SQLite/WAL connection management, schema DDL/DML, DB-backed storage init CLI (`attendance-storage-init`), and file-storage orchestration |
| `models/` | Pure dataclass entities (`UserAccount`, `FaceReference`, `AttendanceSession`, `AttendanceRecord`, `SystemSetting`) with no business logic |
| `repositories/` | CRUD data-access layer parameterizing raw SQL behind typed methods; cache-aware for face references, enforces `ON DELETE SET NULL` semantics |
| `services/` | Business logic layer — ONNX liveness + SFace recognition pipeline, attendance/session orchestration, enrollment, authentication (bcrypt), head-pose estimation, and setting CRUD |
| `ui/` | PyQt5 widgets, windows, and QThread workers (camera capture, enrollment AI); holds the main-window entry point that the `attendance-app` CLI launches |
| `utils/` | Stateless helper functions — face detection/cropping (`_crop_face`, `_create_face_detector`) and timezone-aware datetime formatting |
