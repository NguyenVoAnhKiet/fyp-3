# Chương 3. PHÂN TÍCH VÀ THIẾT KẾ HỆ THỐNG

*(Ghi chú cho tác giả: Phần này sẽ được phát triển thành nội dung chi tiết dựa trên các dàn ý kỹ thuật dưới đây)*

## 3.1. Kiến trúc hệ thống tổng thể
- Mô hình kiến trúc phần mềm (Architecture Pattern): Kiến trúc theo mô-đun (Modular Architecture) chia tách UI, Services và Repositories.
- Sự tương tác giữa các thành phần cốt lõi: 8 services (xử lý logic AI), 7 repositories (tương tác cơ sở dữ liệu), và 11 widgets (giao diện người dùng).

## 3.2. Thiết kế Cơ sở dữ liệu
- **Lựa chọn công nghệ:** Sử dụng SQLite3 với cơ chế WAL (Write-Ahead Logging) để hỗ trợ truy xuất đồng thời trong môi trường đa luồng.
- **Mô hình dữ liệu (Schema):**
  - Bảng `users`: Lưu trữ thông tin cá nhân.
  - Bảng `face_references`: Quản lý vector đặc trưng (embeddings) của người dùng.
  - Bảng `sessions`: Quản lý các phiên điểm danh.
  - Bảng `attendance_records`: Ghi nhận lịch sử điểm danh thành công (có liên kết khóa ngoại).
  - Bảng `recognition_events`: Nhật ký kiểm toán (audit trail) theo dõi lịch sử nhận diện và cảnh báo giả mạo.

## 3.3. Thiết kế luồng xử lý AI (AI Pipeline)
- **Tiền xử lý hình ảnh (Preprocessing):** Thiết kế `PreprocessingConfig` độc lập cho từng mô hình:
  - Model Liveness: Tỷ lệ cắt (scale) 2.7, kích thước 128x128, hệ màu RGB.
  - Model Head-pose/Recognition: Tỷ lệ cắt 1.5, kích thước 224x224, hệ màu BGR.
- **Đường ống đồng bộ:** Khung hình camera → Cắt khuôn mặt → Kiểm tra Anti-spoofing → Rút trích Embedding → Truy vấn CSDL.

## 3.4. Các giải pháp tối ưu hiệu năng và độ tin cậy
- **Làm mịn theo thời gian (Temporal Smoothing):** Áp dụng thuật toán EMA (Exponential Moving Average) với α=0.4 và cơ chế Hysteresis để khắc phục hiện tượng nhấp nháy (flicker) trong đánh giá liveness.
- **Chiến lược Bộ nhớ đệm (Caching):** Triển khai `CachingFaceReferenceRepository` với cơ chế in-memory cache nhằm tăng tốc quá trình so khớp ở tần số cao.
- **Bảo mật dữ liệu:** Tích hợp mã hóa Fernet cho các đặc trưng sinh trắc học lưu trong cơ sở dữ liệu.
