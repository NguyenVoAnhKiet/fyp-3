# Chương 1. GIỚI THIỆU ĐỀ TÀI

- **1.1. Lý do chọn đề tài:** Hạn chế của điểm danh truyền thống (chậm, dễ gian lận). Nhược điểm của giải pháp Cloud (phụ thuộc Internet, rủi ro bảo mật). Nhu cầu về hệ thống offline, có tính năng chống giả mạo (liveness).
- **1.2. Mục đích nghiên cứu:** Xây dựng ứng dụng Desktop điểm danh khuôn mặt offline, chống giả mạo, tốc độ nhanh, quản lý giao diện trực quan.
- **1.3. Đối tượng và phạm vi nghiên cứu:**
  - 1.3.1. Đối tượng: Các mô hình AI (nhận diện, liveness), framework ONNX Runtime, quy trình điểm danh.
  - 1.3.2. Phạm vi: Desktop app (Python/PyQt5), lưu trữ cục bộ (SQLite), xử lý qua Webcam, tập trung chức năng check-in (không làm module tính lương phức tạp).
- **1.4. Ý nghĩa khoa học và thực tiễn:**
  - Khoa học: Triển khai và tối ưu hóa Deep Learning trên môi trường Desktop/CPU.
  - Thực tiễn: Cung cấp giải pháp mã nguồn mở, bảo mật, chi phí thấp cho quy mô vừa và nhỏ.
- **1.5. Tình hình nghiên cứu và các công trình liên quan:**
  - 1.5.1. Giải pháp hiện có: Vân tay, thẻ từ, máy chấm công truyền thống.
  - 1.5.2. Các nghiên cứu liên quan: FaceNet, ArcFace (nhận diện), kiến trúc MiniFASNet (chống giả mạo 2D).
  - 1.5.3. Vấn đề còn tồn tại: Các phần mềm offline yêu cầu cấu hình cao (GPU) hoặc thường thiếu khả năng Liveness.
- **1.6. Đặc tả bài toán:**
  - 1.6.1. Bài toán: Xây dựng hệ thống nhận diện nhanh, chống gian lận liveness trên phần cứng máy tính thông thường.
  - 1.6.2. Hướng giải quyết: Dùng PyQt5 quản lý giao diện & đa luồng, SQLite/WAL cho CSDL, ONNX xử lý AI (MiniFASNet V2 SE).

# Chương 2.     CƠ SỞ LÝ THUYẾT

Trình bày các cơ sở lý thuyết, các công cụ sẽ sử dụng trong Đồ án;

# Chương 3.     PHÂN TÍCH VÀ THIẾT KẾ HỆ THỐNG

Trình bày các mô hình phân tích và thiết kế đồ án

# Chương 4.     XÂY DỰNG VÀ ĐÁNH GIÁ HỆ THỐNG

- Trình bày kết quả hệ thống đã xây dựng và đánh giá kết quả đạt được

# Chương 5.     KẾT LUẬN

·         Tổng kết kết quả đạt được.

·         Ưu điểm và hạn chế.

·         Đề xuất hướng phát triển cho đề tài.
