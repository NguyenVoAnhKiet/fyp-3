# Chương 1. GIỚI THIỆU ĐỀ TÀI

## 1.1. Lý do chọn đề tài

Phương pháp điểm danh truyền thống (gọi tên, quẹt thẻ, vân tay) có nhiều hạn chế như tốn thời gian, dễ xảy ra tình trạng điểm danh hộ, hoặc gặp khó khăn khi phần cứng lỗi (vân tay mờ, xước). Nhận diện khuôn mặt giải quyết triệt để các vấn đề này, tuy nhiên đa số các giải pháp thương mại hiện nay dựa vào Cloud API. Việc phụ thuộc vào Cloud mang lại nhiều rủi ro: yêu cầu kết nối Internet liên tục, độ trễ mạng, tốn chi phí duy trì hàng tháng và đặc biệt là nguy cơ lộ lọt dữ liệu hình ảnh sinh trắc học nhạy cảm.

Do đó, đề tài hướng tới việc xây dựng một hệ thống điểm danh khuôn mặt hoàn toàn Offline trên máy tính (Desktop), tận dụng sức mạnh của các mô hình AI nhẹ (ONNX Runtime) chạy trực tiếp trên máy tính cục bộ. Giải pháp này vừa đảm bảo tốc độ, tính bảo mật dữ liệu tuyệt đối, vừa tích hợp cơ chế chống giả mạo (Liveness detection) để ngăn chặn các hình thức gian lận tinh vi bằng ảnh chụp hoặc video.

## 1.2. Mục đích nghiên cứu

Đề tài hướng tới việc xây dựng thành công một phần mềm Desktop điểm danh bằng khuôn mặt đáp ứng các tiêu chí sau:
- Tự động hóa quá trình điểm danh với độ chính xác cao nhờ tích hợp Deep Learning.
- Tích hợp khả năng chống gian lận (Liveness detection - phân biệt khuôn mặt thật/giả) để tăng tính minh bạch và tin cậy.
- Hoạt động hoàn toàn Offline, đảm bảo an toàn và quyền riêng tư cho dữ liệu người dùng.
- Cung cấp một giao diện trực quan, dễ sử dụng giúp quản trị viên dễ dàng thêm mới nhân sự và trích xuất lịch sử điểm danh.

## 1.3. Đối tượng và phạm vi nghiên cứu

### 1.3.1. Đối tượng nghiên cứu
- Các mô hình học máy và học sâu trong bài toán nhận diện khuôn mặt và chống giả mạo (Liveness detection).
- Nền tảng tăng tốc suy luận AI cục bộ (ONNX Runtime).
- Quy trình điểm danh và hệ thống quản trị cơ sở dữ liệu nhúng (SQLite).

### 1.3.2. Phạm vi nghiên cứu
- **Về tính năng:** Phần mềm tập trung vào chức năng cốt lõi: đăng ký khuôn mặt, nhận diện điểm danh tự động qua camera thời gian thực, cảnh báo gian lận và thống kê lịch sử điểm danh. Hệ thống không mở rộng sang các phân hệ nhân sự phức tạp như tính lương hay phân ca đa chi nhánh.
- **Về công nghệ:** Ứng dụng được phát triển dưới dạng Desktop Application chạy trên hệ điều hành Windows sử dụng ngôn ngữ Python và thư viện giao diện PyQt5. Dữ liệu được lưu trữ cục bộ hoàn toàn.
- **Về thiết bị đầu vào:** Thu thập dữ liệu video thông qua Webcam tiêu chuẩn tích hợp trên máy tính.

## 1.4. Ý nghĩa khoa học và thực tiễn của đề tài

**Ý nghĩa khoa học:**
Đề tài góp phần minh chứng và đánh giá hiệu năng thực tế của việc tối ưu hóa các mô hình học sâu (như MiniFASNet) để chạy trên thiết bị biên (Edge Computing) thông qua kiến trúc ONNX Runtime mà không cần phụ thuộc vào GPU rời. Đồng thời, đề tài đưa ra giải pháp kiến trúc phần mềm kết hợp đa luồng (multi-threading) nhằm tối ưu độ trễ xử lý video trong một ứng dụng GUI bằng Python.

**Ý nghĩa thực tiễn:**
Hệ thống mang lại một giải pháp điểm danh tự động chi phí thấp, dễ triển khai, không yêu cầu thiết lập máy chủ hay hạ tầng mạng. Đây là giải pháp rất phù hợp cho các doanh nghiệp quy mô nhỏ, trung tâm giáo dục muốn áp dụng công nghệ điểm danh sinh trắc học hiện đại, minh bạch mà vẫn bảo vệ tuyệt đối sự riêng tư của nhân viên/học viên.

## 1.5. Tình hình nghiên cứu và các công trình liên quan

### 1.5.1. Các hệ thống/giải pháp điểm danh hiện có
Trên thị trường, máy chấm công vân tay và thẻ từ vẫn phổ biến nhất nhưng thường có lỗ hổng về điểm danh hộ (mượn thẻ) và không linh hoạt về mặt xuất báo cáo nếu không có phần mềm đi kèm tốt. Bên cạnh đó, các hệ thống camera AI thương mại (như Hanet) mang lại độ tiện dụng cao nhưng chi phí phần cứng đắt đỏ, đồng thời dữ liệu buộc phải đẩy lên Cloud để xử lý, gây e ngại cho các tổ chức chú trọng bảo mật nội bộ.

### 1.5.2. Các nghiên cứu về nhận diện khuôn mặt và chống giả mạo (Liveness)
Trong bài toán nhận diện đặc trưng khuôn mặt, các công trình nền tảng có thể kể đến:
- **FaceNet (2015):** Sử dụng kiến trúc CNN kết hợp Triplet Loss để ánh xạ khuôn mặt thành vector đặc trưng (embedding), tạo tiền đề cho hệ thống tìm kiếm khuôn mặt.
- **ArcFace (2019):** Đề xuất hàm mất mát Additive Angular Margin Loss, giúp phân tách không gian đặc trưng rõ ràng hơn nhiều so với FaceNet, đạt độ chính xác (State-of-the-art) trên nhiều tập dữ liệu mở.

Trong bài toán phát hiện thực thể sống (Face Anti-Spoofing):
- Đáng chú ý là dự án mã nguồn mở **Silent-Face-Anti-Spoofing** (Minivision) với kiến trúc **MiniFASNet**. Bằng cách sử dụng các phép tích chập tách rời chiều sâu (Depthwise Separable Convolutions) và khối Squeeze-and-Excitation (SE), mô hình này phát hiện được các bất thường về kết cấu 2D (như viền màn hình, nhiễu Moiré) trên dữ liệu đầu vào. Đề tài kế thừa kiến trúc mô hình này nhằm đạt hiệu suất cao với tài nguyên tính toán hạn chế.

### 1.5.3. Những vấn đề còn tồn tại
Các giải pháp điểm danh nhận diện khuôn mặt ngoại tuyến (Offline) hiếm khi tích hợp khả năng chống giả mạo do các mô hình liveness truyền thống thường quá nặng để chạy trên CPU. Ngược lại, các hệ thống nhỏ nhẹ mã nguồn mở trên mạng lại thiếu tính bảo mật, rất dễ bị vượt qua bằng cách đưa một bức ảnh hoặc điện thoại lên trước camera. Đây chính là khoảng trống bài toán cần được giải quyết.

## 1.6. Đặc tả bài toán

### 1.6.1. Bài toán đặt ra
Cần xây dựng một hệ thống phần mềm chạy hoàn toàn cục bộ trên máy tính, thực hiện điểm danh tự động bằng hình ảnh. Các yêu cầu khắt khe bao gồm: duy trì tốc độ khung hình tốt (đảm bảo thời gian thực) trong khi phải xử lý song song cả nhận diện khuôn mặt và kiểm tra độ sống thực (Liveness) mà không có sự trợ giúp của card đồ họa rời.

### 1.6.2. Hướng giải quyết của đề tài
- **Giao diện & Quản lý luồng:** Sử dụng Python kết hợp PyQt5. Tách biệt hoàn toàn luồng giao diện (UI Thread) và luồng xử lý AI (Worker Thread) để đảm bảo ứng dụng không bị treo.
- **Cơ sở dữ liệu:** Sử dụng cơ sở dữ liệu nhúng SQLite (bật chế độ WAL) nhằm đáp ứng tốt các tác vụ đọc ghi đồng thời (ghi lịch sử điểm danh, truy vấn dữ liệu khuôn mặt).
- **Lõi AI & Xử lý ảnh:** Triển khai pipeline 3 bước: phát hiện khuôn mặt (Face Detection), kiểm tra thực thể sống bằng mô hình MiniFASNet V2 SE quantized, và so khớp đặc trưng khuôn mặt. Tất cả đều chạy qua nền tảng ONNX Runtime để tận dụng tối đa tập lệnh CPU.
