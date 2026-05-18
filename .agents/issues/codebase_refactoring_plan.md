# Kế Hoạch Refactor - Face Attendance System

## Tổng quan

Project có **~30 file source**, kiến trúc 4 lớp rõ ràng (core → repositories → services → ui). Code nhìn chung sạch, nhưng có nhiều cơ hội cải thiện.

---

## NHÓM 1: Dead Code & Unused Code (Ưu tiên cao)

### 1.1 `security.py` — Hoàn toàn không được dùng
- `SecurityService`, `AdminCredentialRateLimiter`, `hash_password`, `verify_password`, `validate_password_strength` — **không file nào import**
- **Hành động**: Xóa file `services/security.py` (hoặc giữ lại nếu có kế hoạch dùng sau, nhưng hiện tại là zombie code)

### 1.2 `raw_image_path` — Parameter chết trong `save_face_reference()`
- `enrollment_service.py:21` — tham số `raw_image_path` luôn `None` ở caller (`enrollment_widget.py:235`)
- **Hành động**: Xóa parameter và logic unlink liên quan

### 1.3 Unused import `sqlite3` trong `admin_repository.py:2`
- Import nhưng không dùng (kiểu trả về dùng `sqlite3.Row` từ type hint nhưng không cần import trực tiếp)
- **Hành động**: Xóa import

---

## NHÓM 2: DRY — Gom logic lặp (Ưu tiên cao)

### 2.1 `attendance_service.py` — `record_success` và `record_duplicate` trùng validation
- Cả 2 method đều lặp: `require_positive_int`, `require_non_empty_text`, `sessions.get_by_id`, `users.get_by_id`
- **Hành động**: Gom thành `_validate_session_and_user()` private helper

### 2.2 `attendance_service.py` — `export_session_to_csv` và `export_session_to_excel` trùng 90%
- Chỉ khác `to_csv` vs `to_excel`
- **Hành động**: Gom thành `_export_session(session_id, file_path, format)`

### 2.3 `camera_thread.py` và `enrollment_camera_thread.py` — `_crop_face` giống hệt nhau
- Cả 2 file đều có hàm crop face với logic identical
- **Hành động**: Đưa `_crop_face` vào `utils/face_utils.py` hoặc kế thừa từ base class

### 2.4 Detector initialization lặp ở 3 nơi
- `main_window.py` (qua `camera_thread`), `camera_thread.py`, `enrollment_camera_thread.py` đều tự tạo `cv2.FaceDetectorYN.create`
- **Hành động**: Factory method hoặc dependency injection từ `main.py`

### 2.5 `_encrypt_embedding` / `_decrypt_embedding` trùng import logic
- `face_reference_repository.py` — 2 hàm lặp try/except import `cryptography.fernet`
- **Hành động**: Gom thành `_get_fernet()` private helper

---

## NHÓM 3: Clean Code — Đặt tên, convention, type hints

### 3.1 Inconsistent method naming trong UI widgets
- `user_management_widget.py`: `init_ui()` (public)
- `attendance_history_widget.py`: `init_ui()` (public)
- Các widget khác: `_build_ui()` (private)
- **Hành động**: Đổi tất cả thành `_build_ui()` cho thống nhất

### 3.2 Missing return type annotations
- `user_repository.py:25-37`: `get_by_id`, `get_by_student_id`, `list_active`, `list_unregistered` — không có return type
- `attendance_repository.py:33`: `get` — không có return type
- `session_repository.py:46`: `get_by_id` — không có return type
- `user_management_widget.py`: `get_data()`, `load_users()`, `add_user()`, v.v.
- `attendance_history_widget.py`: Nhiều method thiếu return type
- **Hành động**: Bổ sung `-> sqlite3.Row | None`, `-> list[sqlite3.Row]`, `-> None`

### 3.3 Public attributes trong entities không cần thiết
- `entities.py` — các dataclass tốt, nhưng `AdminCredential` không có `created_at`/`updated_at` (không dùng)
- **Hành động**: Xem xét xóa nếu không dùng

### 3.4 Magic numbers trong UI
- `enrollment_camera_thread.py:18`: `_POSE_TOLERANCE_DEG = 15.0` — tốt (đã đặt tên)
- `camera_thread.py:17-18`: `_AI_FRAME_SKIP = 3`, `_COOLDOWN_SECONDS = 3.0` — tốt
- Nhưng `enrollment_widget.py:111-114`: `self._progress_bar.setMaximum(5)` — hardcode
- **Hành động**: Dùng constant `_TARGET_CAPTURE_COUNT = 5`

---

## NHÓM 4: Architecture & Design

### 4.1 `pandas` là soft dependency nhưng không được xử lý
- `attendance_service.py:149,160` — `import pandas as pd` lazy import nhưng nếu không có sẽ crash
- **Hành động**: Wrap trong try/except với thông báo lỗi rõ ràng (giống pattern `cryptography` trong `face_reference_repository.py`)

### 4.2 `EnrollmentService` tạo `UserRepository` bên trong method
- `enrollment_service.py:31`: `user_repo = UserRepository(self.references.database)` — vi phạm DI
- **Hành động**: Inject `UserRepository` vào `__init__`

### 4.3 `UserRepository` chứa admin credential methods
- `user_repository.py:58-72`: `create_admin_credential`, `get_admin_credential` — không thuộc responsibility của user repo
- **Hành động**: Di chuyển sang `AdminRepository` (vốn đã có `create`)

### 4.4 `Database.session()` tạo connection mới mỗi lần
- Mỗi `fetch_one`, `fetch_all`, `execute` mở/đóng connection riêng → overhead
- **Hành động**: Chấp nhận (thiết kế intentional cho thread-safety), nhưng có thể document rõ

### 4.5 `schema.py` migration duplicate
- `schema.py:94`: `ALTER TABLE users ADD COLUMN face_registered` — column đã có trong `CREATE TABLE` (dòng 13)
- **Hành động**: Xóa migration thừa này

---

## NHÓM 5: Bug Fixes & Safety

### 5.1 Hardcoded admin password
- `storage_manager.py:22-23`: `username = "admin"`, `password = "admin"`
- **Hành động**: Đọc từ env vars `ADMIN_USERNAME`/`ADMIN_PASSWORD` (đã có trong `.env.example` nhưng không được dùng)

### 5.2 `enrollment_camera_thread.py` — Comment "Bug 1 fix"
- Dòng 249: `# Bug 1 fix: Reset counter khi capture thất bại`
- **Hành động**: Xóa comment này (đã fix rồi, không cần lưu)

### 5.3 `camera_thread.py:208` — Similarity score = 0.0 khi spoof
- `self.recognition_result.emit("spoof", 0, "", liveness.score, 0.0)` — similarity luôn 0.0
- **Hành động**: Truyền `None` thay vì `0.0` cho rõ nghĩa (hoặc giữ nếu UI phụ thuộc)

---

## NHÓM 6: Minor Improvements

### 6.1 `__init__.py` files có docstring không thống nhất
- `core/__init__.py`: `"Core storage utilities."`
- `services/__init__.py`: `"Service layer for storage-related workflows."`
- `repositories/__init__.py`: `"Repository layer for SQLite persistence."`
- `models/__init__.py`, `ui/__init__.py`, `utils/__init__.py`: trống
- **Hành động**: Thêm docstring thống nhất cho tất cả

### 6.2 `constants.py` — Font "JetBrains Mono" có thể không có trên máy user
- **Hành động**: Fallback về QFont fallback chain

### 6.3 `bootstrap.py` không gọi `load_dotenv()`
- Đã document trong AGENTS.md nhưng dễ gây nhầm lẫn
- **Hành động**: Thêm comment giải thích tại sao

---

## Thứ tự thực hiện đề xuất

| Ưu tiên | Nhóm | Ước lượng | status |
|---------|------|-----------|-------|------|
| P0 | Nhóm 1: Dead code | 15 phút | done
| P0 | Nhóm 5.1: Hardcoded password | 10 phút | done
| P1 | Nhóm 2: DRY (2.1, 2.2, 2.5) | 30 phút | done
| P1 | Nhóm 5.2, 5.3: Bug comments | 5 phút | done
| P2 | Nhóm 3: Type hints, naming | 45 phút |
| P2 | Nhóm 4: Architecture (4.1, 4.3) | 30 phút |
| P2 | Nhóm 2.3, 2.4: Camera DRY | 45 phút |
| P3 | Nhóm 6: Minor | 20 phút |

---

**Tổng ước lượng**: ~3-4 giờ làm việc tập trung. Tất cả thay đổi giữ nguyên business logic, không phá public API.
