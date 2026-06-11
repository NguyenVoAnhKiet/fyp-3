# Chương 5. KẾT LUẬN

## 5.1. Tổng kết kết quả đạt được

Trong quá trình thực hiện đề tài, hệ thống điểm danh khuôn mặt offline chống giả mạo đã được xây dựng và hoàn thiện đáp ứng được các mục tiêu đề ra ban đầu. Kết quả đạt được có thể được tổng kết trên hai phương diện chính: chức năng phần mềm và hiệu năng kỹ thuật.

### 5.1.1. Kết quả về mặt chức năng phần mềm

Hệ thống đã xây dựng thành công một ứng dụng Desktop hoàn chỉnh với giao diện trực quan, dễ sử dụng và cung cấp đầy đủ các tính năng cần thiết cho quy trình điểm danh nội bộ:

- **Chức năng điểm danh tự động:** Ứng dụng có khả năng thu nhận hình ảnh từ Webcam, tự động phát hiện và nhận diện khuôn mặt nhân viên trong thời gian thực mà không cần thao tác thủ công.
- **Tính năng chống giả mạo (Liveness):** Hệ thống tích hợp thành công cơ chế phát hiện thực thể sống, đưa ra cảnh báo bằng hình ảnh (UI báo đỏ) ngay lập tức khi phát hiện các hành vi gian lận như sử dụng ảnh in giấy hoặc hình ảnh trên điện thoại.
- **Quản lý nhân sự và lịch sử:** Cung cấp module quản lý thông tin nhân viên, cho phép thêm mới, cập nhật khuôn mặt tham chiếu, cũng như theo dõi chi tiết lịch sử ra vào của từng cá nhân.
- **Cấu hình hệ thống linh hoạt:** Ứng dụng cho phép người quản trị dễ dàng tùy chỉnh các thông số hoạt động như độ nhạy nhận diện (Threshold), ngưỡng Liveness, và chọn thiết bị Camera đầu vào trực tiếp trên giao diện cài đặt.

### 5.1.2. Kết quả về mặt kỹ thuật và thuật toán

Bên cạnh sự hoàn thiện về mặt tính năng, hệ thống cũng đạt được những kết quả khả quan về mặt kỹ thuật khi triển khai các mô hình Deep Learning trên môi trường Desktop phổ thông:

- **Tốc độ xử lý thời gian thực:** Nhờ sử dụng nền tảng ONNX Runtime, các mô hình siêu nhẹ (YuNet, SFace) và mô hình lượng tử hóa (MiniFASNet V2 SE), kết hợp cùng kiến trúc lập trình đa luồng (tách biệt UI Thread và AI Worker Thread), ứng dụng cho tốc độ khung hình (FPS) ổn định, đáp ứng tốt yêu cầu chạy thuần túy trên CPU.
- **Độ chính xác và tính ổn định:** Trong điều kiện ánh sáng văn phòng tiêu chuẩn, hệ thống cho tỷ lệ nhận diện chính xác cao. Việc áp dụng các kỹ thuật ổn định kết quả (như bộ lọc trung bình động EMA và theo dõi vùng khuôn mặt IoU) giúp giảm thiểu hiện tượng nhấp nháy, mang lại trải nghiệm mượt mà.
- **Cơ sở dữ liệu an toàn, không tắc nghẽn:** Áp dụng SQLite với cơ chế WAL (Write-Ahead Logging) giúp giải quyết triệt để tình trạng khóa cơ sở dữ liệu (Database Locked) khi nhiều luồng thực hiện đọc/ghi đồng thời trong quá trình nhận diện và ghi nhận lịch sử.

## 5.2. Ưu điểm và hạn chế

Dựa trên quá trình xây dựng và đánh giá, hệ thống bộc lộ những ưu điểm nổi bật cũng như một số hạn chế nhất định cần khắc phục trong tương lai.

### 5.2.1. Ưu điểm

- **Khả năng hoạt động độc lập (Offline):** Toàn bộ quá trình xử lý hình ảnh, nhận diện và lưu trữ cơ sở dữ liệu được thực hiện cục bộ trên máy tính cá nhân. Điều này giúp hệ thống hoạt động ổn định mà không phụ thuộc vào kết nối Internet, đồng thời đảm bảo tính riêng tư dữ liệu cao nhất.
- **Tốc độ phản hồi nhanh:** Bằng việc tối ưu hóa kiến trúc xử lý qua đa luồng (QThread) và ONNX Runtime, hệ thống đem lại trải nghiệm điểm danh mượt mà, thời gian xử lý toàn trình (từ nhận diện đến ghi nhận cơ sở dữ liệu) diễn ra gần như tức thời.
- **Ngăn chặn gian lận cơ bản:** Việc triển khai thành công mô hình MiniFASNet V2 SE đã giúp chặn đứng hiệu quả các thủ đoạn gian lận phổ biến bằng hình ảnh 2D (như sử dụng ảnh in giấy, hoặc đưa màn hình điện thoại/tablet trước Camera), vốn là điểm yếu của các phần mềm điểm danh khuôn mặt thông thường.

### 5.2.2. Hạn chế

- **Giới hạn của mô hình chống giả mạo 2D:** Do MiniFASNet V2 SE về bản chất là một bộ phân loại kết cấu bề mặt 2D (2D texture classifier), hệ thống rất nhạy cảm với điều kiện ánh sáng. Trong môi trường quá thiếu sáng hoặc ngược sáng, mô hình có thể bị từ chối sai (False Reject - nhận diện nhầm người thật thành ảnh giả). Hơn nữa, vì chỉ đánh giá đặc trưng 2D, mô hình vẫn có rủi ro bị đánh lừa bởi các loại mặt nạ 3D tinh vi có độ chi tiết cao.
- **Mức độ tiêu thụ CPU cao:** Mặc dù mô hình đã được lượng tử hóa (Quantization) để phù hợp với CPU, việc duy trì tác vụ phân tích AI liên tục ở tốc độ cao trên luồng nền (AI Worker Thread) vẫn tiêu thụ một lượng tài nguyên xử lý đáng kể. Điều này có thể gây nóng máy hoặc suy giảm hiệu năng đối với các máy tính có cấu hình thấp nếu chạy liên tục thời gian dài.
- **Chỉ nhận diện đơn lẻ:** Trong phiên bản hiện tại, hệ thống mới chỉ áp dụng cắt cúp (crop) và xử lý liveness cho khuôn mặt có kích thước lớn nhất trong khung hình, do đó chưa hỗ trợ tính năng điểm danh nhiều nhân viên xuất hiện cùng lúc trước ống kính (Multi-face tracking).

## 5.3. Đề xuất hướng phát triển cho đề tài

Để khắc phục những hạn chế còn tồn tại và nâng cao khả năng ứng dụng thực tế của hệ thống, các hướng phát triển tiếp theo được đề xuất như sau:

- **Khắc phục giới hạn của mô hình Liveness 2D:** Hướng nghiên cứu tiếp theo là tích hợp phần cứng chuyên dụng như camera hồng ngoại (IR) hoặc camera đo chiều sâu (Depth). Song song đó, có thể nghiên cứu nâng cấp lên các kiến trúc Liveness 3D tiên tiến hơn. Việc này sẽ giúp hệ thống hoạt động ổn định trong mọi điều kiện ánh sáng và chống lại hiệu quả các hình thức tấn công bằng mặt nạ 3D tinh vi.
- **Giải quyết vấn đề tiêu tốn tài nguyên CPU:** Để tối ưu hóa quá trình tính toán, hệ thống có thể tích hợp các công cụ tăng tốc suy luận phần cứng như OpenVINO (cho CPU Intel) hoặc TensorRT (nếu có GPU Nvidia). Một hướng tiếp cận khác là chuyển đổi sang kiến trúc Client - Edge Server, trong đó thiết bị đầu cuối chỉ thu nhận hình ảnh, còn các tác vụ AI nặng sẽ được đẩy lên một Edge Server cục bộ xử lý tập trung, giúp giảm tải hoàn toàn cho máy trạm.
- **Mở rộng chức năng đáp ứng quy mô lớn:**
  - *Điểm danh đám đông (Multi-face tracking):* Nâng cấp luồng xử lý AI để hệ thống có khả năng nhận diện và kiểm tra Liveness đồng thời cho nhiều khuôn mặt cùng xuất hiện trong một khung hình, qua đó tăng tốc độ lưu thông tại các khu vực đông người.
  - *Đồng bộ hóa Cloud:* Dù khả năng hoạt động offline là một lợi thế, việc phát triển thêm module tùy chọn để đồng bộ hóa dữ liệu định kỳ (Sync) lên hệ thống Cloud quản trị trung tâm sẽ giúp ứng dụng dễ dàng triển khai và quản lý nhân sự tại các doanh nghiệp có nhiều chi nhánh.
