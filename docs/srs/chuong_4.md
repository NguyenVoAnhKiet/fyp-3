# Chương 4. XÂY DỰNG VÀ ĐÁNH GIÁ HỆ THỐNG

*(Ghi chú cho tác giả: Phần này sẽ được phát triển thành nội dung chi tiết dựa trên các dàn ý kỹ thuật dưới đây)*

## 4.1. Môi trường triển khai và cấu hình
- **Công cụ và nền tảng:** Ngôn ngữ Python 3.11+, giao diện PyQt5, môi trường suy luận ONNX Runtime.
- **Thông số cấu hình vận hành (System Config):**
  - Ngưỡng từ chối giả mạo (Liveness Threshold): 0.3.
  - Tần số xử lý AI (Frame skip): Xử lý AI mỗi 3 khung hình (~10 Hz tại 30 FPS).
  - Thời gian chờ giữa các lần điểm danh (Per-User Cooldown): 3.0 giây.
- **Hỗ trợ múi giờ:** Hệ thống tự động đồng bộ giờ UTC trong lưu trữ và hỗ trợ hiển thị 13 múi giờ IANA chuẩn.

## 4.2. Kết quả kiểm thử (Testing)
- Phương pháp kiểm thử tự động với bộ công cụ `pytest`.
- Độ bao phủ: Tổng cộng 280 kịch bản kiểm thử (250 unit tests, 30 integration tests) đạt tỷ lệ vượt qua (pass rate) 100%, đảm bảo các module giao tiếp không có lỗi.

## 4.3. Đánh giá hiệu năng và độ chính xác thực tế
- **Tốc độ xử lý:** Đo lường thời gian trích xuất và so khớp sinh trắc học trên mỗi khung hình (~10ms đối với tập dữ liệu cơ bản).
- **Độ ổn định của hệ thống chống giả mạo:** Nhờ cơ chế Temporal Smoothing kết hợp IoU tracking, thời gian phản hồi nhấp nháy (flicker) được kéo giãn ổn định ở mức 2-3 giây.
- **Độ chính xác nhận diện liveness:** Tỷ lệ từ chối các nỗ lực giả mạo (Spoof rejection rate) đạt khoảng 95% trong các điều kiện ánh sáng văn phòng tiêu chuẩn.
- **Hình ảnh giao diện thực tế:** (Chèn các hình ảnh minh họa về màn hình quản trị, màn hình điểm danh, nhật ký).
