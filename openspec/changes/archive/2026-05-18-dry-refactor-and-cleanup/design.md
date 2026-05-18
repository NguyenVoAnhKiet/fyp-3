## Context

The codebase has three areas of duplicated code that violate DRY principles:
1. `attendance_service.py` has near-identical validation in `record_success` and `record_duplicate`, and near-identical export logic in `export_session_to_csv` and `export_session_to_excel`
2. `face_reference_repository.py` has identical try/except import blocks in `_encrypt_embedding` and `_decrypt_embedding`
3. Minor cleanliness issues: dead `raw_image_path` parameter, stale bug comment, ambiguous `0.0` similarity on spoof

The project uses a 4-layer architecture (core → repositories → services → ui) with strict separation of concerns.

## Goals / Non-Goals

**Goals:**
- Eliminate duplicated validation and export logic in `attendance_service.py`
- Eliminate duplicated cryptography import logic in `face_reference_repository.py`
- Remove dead code parameter and stale comments
- Clarify spoof similarity score semantics
- Zero behavior changes — all refactoring must be transparent to callers

**Non-Goals:**
- No changes to public API signatures (except internal private methods)
- No changes to camera thread DRY (2.3, 2.4 in plan) — scoped out for this change
- No changes to pandas soft dependency handling (4.1 in plan) — scoped out
- No changes to repository responsibility separation (4.3 in plan) — scoped out

## Decisions

### D1: Private helper for validation in `attendance_service.py`
**Decision**: Extract `_validate_session_and_user(session_id, user_id) -> None` that raises `LookupError` if either is missing.
**Rationale**: Both `record_success` and `record_duplicate` perform identical validation: `require_positive_int` x2, `require_non_empty_text`, session lookup, user lookup. The only difference is `record_success` also validates `event_time` separately, which stays inline since `record_duplicate` doesn't take it as a parameter.
**Alternatives considered**: 
- Decorator pattern — overkill for 2 methods
- Base class — adds inheritance complexity for minimal gain

### D2: Unified export method with format parameter
**Decision**: Replace `export_session_to_csv` and `export_session_to_excel` with `_export_session(session_id, file_path, format)` where format is `"csv"` or `"excel"`.
**Rationale**: 90% identical logic — only the final `df.to_csv()` vs `df.to_excel()` differs. A single method with a format branch eliminates duplication.
**Alternatives considered**:
- Strategy pattern — overkill for 2 formats
- Keep separate methods with shared `_prepare_export_df()` helper — viable but still leaves two nearly-identical public methods

### D3: `_get_fernet()` helper in `face_reference_repository.py`
**Decision**: Extract a `_get_fernet() -> Fernet | None` method that handles the lazy import and key check once.
**Rationale**: Both `_encrypt_embedding` and `_decrypt_embedding` have identical try/except import blocks. A single helper centralizes the import and error message.
**Alternatives considered**:
- Module-level lazy import — doesn't work because the key is instance-level from env var

### D4: Remove `raw_image_path` parameter entirely
**Decision**: Delete the unused `raw_image_path` parameter from `save_face_reference()` and its unlink logic.
**Rationale**: Caller always passes `None`. The parameter and its conditional unlink are dead code.
**Alternatives considered**: Keep with `# unused` comment — no value, just noise

### D5: Change spoof similarity from `0.0` to `None`
**Decision**: Emit `None` instead of `0.0` for similarity score when spoof detected.
**Rationale**: `0.0` implies a measured similarity of zero, which is misleading. `None` correctly signals "no recognition was attempted." The `record_success` method already accepts `float | None`, so downstream handles this.
**Alternatives considered**: Keep `0.0` — simpler but semantically incorrect

## Risks / Trade-offs

- **[Risk]** `_validate_session_and_user` changes error message format slightly if consolidated — **Mitigation**: Keep identical error messages from original code
- **[Risk]** `_export_session` format parameter could be typo'd — **Mitigation**: Use literal type `Literal["csv", "excel"]` with ValueError for invalid values
- **[Risk]** `_get_fernet()` returns `None` when no key — callers must handle — **Mitigation**: Existing logic already guards with `if not self._fernet_key` before calling encrypt/decrypt
- **[Trade-off]** Keeping `event_time` validation inline in `record_success` rather than in helper — minor inconsistency but avoids passing optional params through helper
