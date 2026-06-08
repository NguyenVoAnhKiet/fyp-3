# Tài liệu Đặc tả Yêu cầu Hệ thống (SRS)

Tài liệu này đặc tả các yêu cầu, cơ sở lý thuyết, phân tích thiết kế và kết quả đánh giá cho dự án **"Hệ thống điểm danh sử dụng nhận diện khuôn mặt và chống giả mạo"**.

## Danh mục các chương nội dung

Dưới đây là liên kết đến nội dung chi tiết của từng chương:

### 1. [Chương 1. Giới thiệu đề tài](chuong_1.md)
*   **Nội dung chính:** Lý do chọn đề tài, mục tiêu nghiên cứu, đối tượng và phạm vi nghiên cứu, ý nghĩa khoa học và thực tiễn, các nghiên cứu liên quan, đặc tả bài toán (bằng toán học).
*   **Mô tả:** Giới thiệu tổng quan về sự cần thiết của hệ thống điểm danh tự động kết hợp chống giả mạo khuôn mặt bằng học sâu, xác định bài toán nghiệp vụ cụ thể.

### 2. [Chương 2. Cơ sở lý thuyết](chuong_2.md)
*   **Nội dung chính:** Tổng quan về thị giác máy tính, phương pháp Face Detection (YuNet), Face Anti-Spoofing (MiniFASNet + SE Block + Logit space), Face Recognition (SFace), các độ đo khoảng cách (Cosine, Euclid), và làm mịn thời gian (EMA, Hysteresis, IoU Tracking).
*   **Mô tả:** Trình bày chi tiết toán học và mô hình học sâu cốt lõi sử dụng trong AI Pipeline để định danh và bảo vệ hệ thống trước tấn công giả mạo (Print/Replay attacks).

### 3. [Chương 3. Phân tích và thiết kế hệ thống](chuong_3.md)
*   **Nội dung chính:** Kiến trúc hệ thống tổng thể (Modular Architecture), thiết kế Cơ sở dữ liệu (SQLite WAL schema cho `users`, `face_references`, `sessions`, `attendance_records`, `recognition_events`), thiết kế luồng xử lý AI (AI Pipeline), các giải pháp tối ưu (Caching, mã hóa Fernet).
*   **Mô tả:** Phác thảo thiết kế cơ cấu phần mềm, kiến trúc DB và giải pháp tối ưu hóa bộ nhớ đệm giúp chạy thời gian thực trên CPU.

### 4. [Chương 4. Xây dựng và đánh giá hệ thống](chuong_4.md)
*   **Nội dung chính:** Môi trường triển khai (Python, PyQt5, ONNX Runtime), thông số cấu hình hệ thống, kết quả kiểm thử tự động với `pytest` (280 kịch bản), đánh giá hiệu năng thực tế (tốc độ ~10ms, tỷ lệ chống giả mạo ~95%).
*   **Mô tả:** Đánh giá thực nghiệm hiệu suất, độ chính xác nhận diện liveness và độ bao phủ của bộ mã nguồn kiểm thử.
