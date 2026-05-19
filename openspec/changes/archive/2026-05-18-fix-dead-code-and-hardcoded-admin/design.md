## Context

The project is a Python desktop face attendance system with ~30 source files. Two P0 issues exist:

1. **Dead code**: `services/security.py` is entirely unreferenced, `raw_image_path` parameter in `save_face_reference()` is always `None`, and `admin_repository.py` has an unused `import sqlite3`.
2. **Hardcoded admin credentials**: `storage_manager.py` hardcodes `admin`/`admin` despite `.env.example` providing `ADMIN_USERNAME`/`ADMIN_PASSWORD` vars that are never read.

The codebase follows a 4-layer architecture (core → repositories → services → ui) with `load_dotenv()` called in `main.py:main()` before any `os.getenv()` usage.

## Goals / Non-Goals

**Goals:**
- Remove all dead/zombie code identified in the refactoring plan (Nhóm 1)
- Read admin credentials from environment variables with safe fallback defaults
- Remove stale "Bug 1 fix" comment (Nhóm 5.2)
- Keep all changes backward-compatible — no breaking changes to public APIs

**Non-Goals:**
- No changes to DRY refactoring (Nhóm 2) — separate change
- No type hint additions (Nhóm 3) — separate change
- No architecture changes like DI improvements (Nhóm 4) — separate change
- No modifications to the database schema or migration logic

## Decisions

### D1: Environment variable reading approach for admin credentials

**Decision**: Read `ADMIN_USERNAME` and `ADMIN_PASSWORD` via `os.getenv()` with fallback to `"admin"`/`"admin"` for backward compatibility with existing installations that already seeded the default admin.

**Rationale**: `load_dotenv()` is called in `main()` before `StorageManager.initialize()`, so env vars will be available. The fallback ensures existing databases without custom admin credentials continue to work.

**Alternatives considered**:
- Raise error if env vars not set → breaks existing installations
- Read from config file → adds complexity not justified for 2 values

### D2: `raw_image_path` parameter removal

**Decision**: Remove the `raw_image_path` parameter entirely from `save_face_reference()` signature and the single caller in `enrollment_widget.py:235`.

**Rationale**: The parameter is always `None` — the unlink logic never executes. Removing simplifies the API. This is technically a signature change but not breaking since no external callers exist.

### D3: `security.py` deletion vs. deprecation

**Decision**: Delete the file outright rather than deprecate.

**Rationale**: Zero imports across the entire project. No tests reference it. Keeping it as deprecated adds maintenance burden with zero benefit.

### D4: `import sqlite3` removal from `admin_repository.py`

**Decision**: Remove the unused import. The `sqlite3.Row` type hint works without importing `sqlite3` because it's used only as a string annotation in the return type.

**Rationale**: Python's `from __future__ import annotations` defers type evaluation, so `sqlite3.Row` in a return type annotation doesn't require the module to be imported at runtime.

## Risks / Trade-offs

| Risk | Mitigation |
|------|-----------|
| Existing installations with `admin`/`admin` password may be confused if they set env vars after first run | Env vars only seed on first run (when `admin_credentials` table is empty). Document this behavior. |
| Removing `raw_image_path` could break external forks/extensions | No external API consumers known. Parameter was never functional. |
| `sqlite3.Row` type hint without import may confuse static analyzers | `from __future__ import annotations` handles this; ruff check passes without the import. |
