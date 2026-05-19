## 1. Nhóm 3 - Type hints & naming

### 1.1 UI Widgets - standardize method naming

- [x] 1.1.1 Check user_management_widget.py for init_ui() → _build_ui()
- [x] 1.1.2 Check attendance_history_widget.py for init_ui() → _build_ui()
- [x] 1.1.3 Check other UI widgets for inconsistent naming

### 1.2 Repositories - add return type annotations

- [x] 1.2.1 Add return types to user_repository.py (get_by_id, get_by_student_id, list_active, list_unregistered)
- [x] 1.2.2 Add return type to attendance_repository.py (get)
- [x] 1.2.3 Add return type to session_repository.py (get_by_id)

### 1.3 Entities - remove unused attributes

- [x] 1.3.1 Check AdminCredential in entities.py - remove unused attributes

### 1.4 UI - replace magic numbers with constants

- [x] 1.4.1 Check enrollment_widget.py for hardcoded numbers
- [x] 1.4.2 Replace with named constants where applicable

## 2. Nhóm 4 - Architecture

### 2.1 Soft dependency handling

- [x] 2.1.1 Wrap pandas import in attendance_service.py with try/except
- [x] 2.1.2 Add clear error message when pandas not available

### 2.2 Admin credentials migration

- [x] 2.2.1 Move create_admin_credential from UserRepository to AdminRepository
- [x] 2.2.2 Move get_admin_credential from UserRepository to AdminRepository
- [x] 2.2.3 Update callers to use AdminRepository instead

## 3. Verification

- [x] 3.1 Run ruff check to verify no new issues
- [x] 3.2 Run pytest to ensure no regressions