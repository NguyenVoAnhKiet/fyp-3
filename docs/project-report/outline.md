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

# Chương 2. CƠ SỞ LÝ THUYẾT

- **2.1. Tổng quan về bài toán nhận diện khuôn mặt**
	  - 2.1.1. Bài toán phát hiện khuôn mặt (Face Detection): Khái niệm chung, mô hình YuNet siêu nhẹ và ưu điểm về tốc độ trên CPU.
  - 2.1.2. Bài toán nhận diện khuôn mặt (Face Recognition): Quá trình rút trích đặc trưng (Feature Extraction), mô hình SFace, và độ đo khoảng cách (Cosine Similarity).
- **2.2. Bài toán chống giả mạo khuôn mặt (Face Anti-Spoofing)**
  - 2.2.1. Khái niệm và phân loại: So sánh Liveness 2D và 3D, lý do chọn 2D Liveness.
  - 2.2.2. Mô hình MiniFASNet V2 SE: Tổng quan kiến trúc và kỹ thuật lượng tử hóa (Quantization) để chạy thực tế.
  - 2.2.3. Các kỹ thuật ổn định kết quả (Temporal Smoothing): Lý thuyết Trung bình động hàm mũ (EMA) và hệ số giao nhau (IoU).
- **2.3. Công nghệ và công cụ phát triển**
  - 2.3.1. Ngôn ngữ Python và Framework PyQt5: Khái niệm đa luồng (Multithreading) và lý do tách luồng AIWorker khỏi luồng UI (QThread).
  - 2.3.2. Nền tảng thực thi ONNX Runtime: Tối ưu hóa tính toán Inference trên CPU.
  - 2.3.3. CSDL SQLite và cơ chế WAL (Write-Ahead Logging): Lý thuyết hỗ trợ đa luồng đọc/ghi không bị khóa (Database Locked).

# Chương 3. PHÂN TÍCH VÀ THIẾT KẾ HỆ THỐNG

- **3.1. Phân tích yêu cầu**
  - 3.1.1. Yêu cầu chức năng và Phi chức năng
  - 3.1.2. Biểu đồ Use Case tổng quát
  - 3.1.3. Đặc tả các Use Case chính (Điểm danh AI, Quản lý nhân viên, Cấu hình hệ thống)
- **3.2. Thiết kế kiến trúc**
  - 3.2.1. Kiến trúc tổng thể hệ thống
  - 3.2.2. Kiến trúc phân lớp phần mềm (UI, Service, Repository)
  - 3.2.3. Kiến trúc xử lý đa luồng (UI Thread & AI Worker Thread)
- **3.3. Thiết kế chi tiết**
  - 3.3.1. Thiết kế Cơ sở dữ liệu (Sơ đồ ERD & Đặc tả các bảng)
  - 3.3.2. Sơ đồ hoạt động (Activity Diagram) cho luồng Nhận diện & Liveness
  - 3.3.3. Sơ đồ tuần tự (Sequence Diagram) cho các chức năng chính
- **3.4. Thiết kế giao diện**
  - 3.4.1. Tiêu chuẩn và nguyên tắc thiết kế (Màu sắc, Font chữ, Bố cục)
  - 3.4.2. Thiết kế các màn hình chính (Màn hình điểm danh, Quản lý nhân viên, Cấu hình)

# Chương 4. XÂY DỰNG VÀ ĐÁNH GIÁ HỆ THỐNG

- **4.1. Môi trường triển khai**
  - 4.1.1. Môi trường phần cứng (Cấu hình PC/Laptop cài đặt, thông số Webcam)
  - 4.1.2. Môi trường phần mềm và thư viện (HĐH Windows, Python, ONNX Runtime, PyQt5, SQLite)
- **4.2. Kết quả xây dựng hệ thống**
  - 4.2.1. Giao diện chức năng điểm danh & cảnh báo (Minh họa check-in thành công và chặn giả mạo/spoofing)
  - 4.2.2. Giao diện quản lý nhân viên và lịch sử điểm danh
  - 4.2.3. Giao diện cấu hình hệ thống
- **4.3. Đánh giá hệ thống**
  - 4.3.1. Đánh giá hiệu năng xử lý (Thời gian Inference trên CPU, tốc độ khung hình - FPS thực tế)
  - 4.3.2. Đánh giá độ chính xác qua kịch bản thực tế (Kiểm thử người thật ở nhiều điều kiện sáng, test với ảnh in giấy, màn hình điện thoại/tablet; thống kê tỷ lệ Pass/Fail)
  - 4.3.3. Đánh giá mức tiêu thụ tài nguyên (Theo dõi lượng RAM, % CPU khi app hoạt động)

# Chương 5. KẾT LUẬN

- **5.1. Tổng kết kết quả đạt được:**
  - Về chức năng: Hoàn thiện ứng dụng Desktop điểm danh offline với giao diện trực quan, quản lý nhân viên và cấu hình hệ thống.
  - Về kỹ thuật: Tích hợp thành công mô hình Liveness (MiniFASNet V2) và tối ưu hóa tốc độ xử lý AI trên CPU bằng ONNX Runtime và kiến trúc đa luồng.
- **5.2. Ưu điểm và hạn chế:**
  - Ưu điểm: Hệ thống phản hồi nhanh, không phụ thuộc kết nối Internet, tích hợp tính năng chống giả mạo cơ bản.
  - Hạn chế 1: Mô hình chống giả mạo 2D dễ bị từ chối sai (False Reject) trong điều kiện thiếu sáng hoặc có nguy cơ bị lừa bởi mặt nạ 3D tinh vi.
  - Hạn chế 2: Quá trình suy luận (Inference) vẫn tiêu tốn nhiều tài nguyên CPU khi ứng dụng hoạt động liên tục trong thời gian dài.
- **5.3. Đề xuất hướng phát triển cho đề tài:**
  - Cải thiện Liveness: Nghiên cứu sử dụng camera hồng ngoại/chiều sâu (IR/Depth) hoặc nâng cấp lên các mô hình Liveness 3D để tăng cường bảo mật.
  - Tối ưu hóa hiệu năng: Tích hợp OpenVINO/TensorRT hoặc kết hợp xử lý qua Edge Server/GPU nhằm giảm tải cho CPU của thiết bị.
  - Mở rộng hệ thống: Bổ sung tính năng đồng bộ dữ liệu lên hệ thống Cloud quản lý tập trung và hỗ trợ phát hiện/điểm danh nhiều khuôn mặt cùng lúc (Multi-face tracking).
