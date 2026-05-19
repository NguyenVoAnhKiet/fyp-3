## Why

Codebase có nhiều inconsistent type hints, naming conventions, và architectural issues ảnh hưởng đến maintainability. Việc refactor này sẽ:
- Cải thiện code consistency và readability
- Đảm bảo soft dependencies được handle đúng cách
- Di chuyển admin credentials methods đúng vị trí

## What Changes

**Nhóm 3 - Type hints & naming:**
- 3.1: Chuẩn hóa tất cả UI widgets sử dụng `_build_ui()` thay vì `init_ui()`
- 3.2: Bổ sung return type annotations cho repositories và widgets
- 3.3: Xóa unused public attributes trong entities (AdminCredential)
- 3.4: Thay hardcoded numbers bằng constants có tên

**Nhóm 4 - Architecture:**
- 4.1: Wrap pandas import trong try/except với error message rõ ràng
- 4.3: Di chuyển admin credential methods từ UserRepository sang AdminRepository

## Capabilities

### New Capabilities
<!-- Refactoring, không có new capabilities -->

### Modified Capabilities
<!-- Không có requirement changes, chỉ là implementation improvements -->

## Impact

- **Files bị ảnh hưởng:**
  - `src/attendance_system/repositories/user_repository.py`
  - `src/attendance_system/repositories/attendance_repository.py`
  - `src/attendance_system/repositories/session_repository.py`
  - `src/attendance_system/repositories/admin_repository.py`
  - `src/attendance_system/services/attendance_service.py`
  - `src/attendance_system/models/entities.py`
  - `src/attendance_system/ui/*.py`

- **Dependencies:** Không thay đổi

- **Breaking changes:** Không - refactor giữ nguyên business logic