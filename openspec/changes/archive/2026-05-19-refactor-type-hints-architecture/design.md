## Context

Dựa trên codebase refactoring plan, project có ~30 source files với kiến trúc 4 lớp (core → repositories → services → ui). Hiện tại có nhiều inconsistent type hints, naming conventions, và architectural issues cần giải quyết.

## Goals / Non-Goals

**Goals:**
- Chuẩn hóa method naming trong UI widgets (`_build_ui()` thay vì `init_ui()`)
- Bổ sung return type annotations cho repositories và widgets
- Wrap pandas import với try/except để handle soft dependency đúng cách
- Di chuyển admin credential methods từ UserRepository sang AdminRepository
- Thay hardcoded numbers bằng constants có tên

**Non-Goals:**
- Không thay đổi business logic
- Không thêm feature mới
- Không thay đổi public APIs

## Decisions

**D1: Type annotations approach**
- Bổ sung return types dạng `-> sqlite3.Row | None`, `-> list[sqlite3.Row]`, `-> None`
- Lý do: Đã có type hints cho parameters, chỉ thiếu return types

**D2: Pandas soft dependency handling**
- Dùng try/except pattern giống như cryptography trong face_reference_repository.py
- Lý do: Đảm bảo graceful degradation khi pandas không được install

**D3: Admin credential methods migration**
- Di chuyển `create_admin_credential`, `get_admin_credential` từ UserRepository sang AdminRepository
- Lý do: Admin credentials không thuộc user domain, nên ở AdminRepository

## Risks / Trade-offs

- [Risk] Di chuyển methods có thể break callers đang dùng
  - **Mitigation**: Kiểm tra tất cả callers trước khi refactor, update imports
- [Risk] Type annotations có thể miss edge cases
  - **Mitigation**: Review kỹ mỗi file sau khi thay đổi
