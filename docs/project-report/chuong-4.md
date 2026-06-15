# Chương 4. XÂY DỰNG VÀ ĐÁNH GIÁ HỆ THỐNG

## 4.1. Môi trường triển khai

Để tiến hành xây dựng, thử nghiệm và đánh giá hệ thống điểm danh khuôn mặt, môi trường phần cứng và phần mềm được thiết lập với các thông số cụ thể như sau.

### 4.1.1. Môi trường phần cứng

Hệ thống được phát triển và chạy thử nghiệm trên máy tính cá nhân (Laptop) với cấu hình chi tiết:

- **Bộ vi xử lý (CPU):** AMD Ryzen 5 5600H with Radeon Graphics (3.30 GHz)
- **Bộ nhớ trong (RAM):** 16.0 GB 
- **Card đồ họa rời (GPU):** NVIDIA GeForce RTX 3050 Ti Laptop GPU (4 GB VRAM)
- **Card đồ họa tích hợp:** AMD Radeon(TM) Graphics
- **Ổ cứng lưu trữ:** 701 GB tổng dung lượng (SSD)
- **Thiết bị thu nhận hình ảnh (Webcam):** Webcam tích hợp trên Laptop

Mặc dù máy tính thử nghiệm có trang bị GPU rời, hệ thống được thiết kế và tối ưu hóa để chạy trực tiếp quá trình suy luận AI (Inference) trên CPU thông qua ONNX Runtime nhằm đáp ứng tiêu chí dễ dàng triển khai trên các phần cứng máy tính thông thường của doanh nghiệp vừa và nhỏ.

### 4.1.2. Môi trường phần mềm và thư viện

Ứng dụng được xây dựng trên nền tảng Windows 64-bit bằng ngôn ngữ lập trình Python, kết hợp cùng các thư viện mã nguồn mở chuyên dụng cho xử lý hình ảnh và phát triển ứng dụng Desktop. Danh sách các thành phần phần mềm bao gồm:

- **Hệ điều hành:** Windows 11 Home Single Language (Version 25H2, OS build 26200.8524, 64-bit).
- **Ngôn ngữ lập trình:** Python 3.11 trở lên.
- **Nền tảng giao diện người dùng:** `PyQt5` – Quản lý giao diện đồ họa (GUI) theo kiến trúc đa luồng (multithreading), tách biệt luồng Camera/AI (Worker Thread) khỏi luồng chính (UI Thread) để đảm bảo trải nghiệm hiển thị video mượt mà, không giật lag.
- **Nền tảng thực thi AI:** `onnxruntime` – Đóng vai trò là core để thực thi suy luận (inference) các mô hình Deep Learning (YuNet cho Face Detection, SFace cho Face Recognition, và MiniFASNet V2 SE cho Liveness) với tốc độ cao, tối ưu tối đa cho tài nguyên phần cứng.
- **Thư viện thị giác máy tính:** `opencv-python` và `deepface-cv2` – Hỗ trợ thu thập luồng video trực tiếp từ Webcam, tiền xử lý khung hình (resize, crop), rút trích và tính toán khoảng cách cosine.
- **Hệ quản trị CSDL:** `SQLite` với chế độ Write-Ahead Logging (WAL) – Phục vụ lưu trữ offline thông tin nhân viên, vector đặc trưng khuôn mặt và lịch sử điểm danh. Cơ chế WAL hỗ trợ đọc/ghi đồng thời an toàn trên kiến trúc đa luồng mà không gặp lỗi "database locked".
- **Thư viện bảo mật:** `bcrypt` – Hỗ trợ mã hóa mật khẩu an toàn (hashing) cho tài khoản Quản trị viên (Admin), bảo vệ hệ thống khỏi các truy cập trái phép.

## 4.2. Kết quả xây dựng hệ thống

Sau quá trình phát triển và tích hợp, hệ thống đã hoàn thiện các chức năng lõi đáp ứng yêu cầu điểm danh khuôn mặt offline với giao diện tương tác trực quan. Các kết quả hiển thị được chia thành các nhóm màn hình chính phục vụ cho mục đích sử dụng khác nhau.

### 4.2.1. Giao diện chức năng điểm danh & cảnh báo

Đây là màn hình chính của ứng dụng dành cho người dùng cuối (nhân viên). Giao diện được thiết kế đơn giản, tập trung vào luồng video trực tiếp từ Webcam.

- **Chức năng điểm danh thành công:** Khi nhân viên thật bước vào khung hình, hệ thống sẽ tự động phát hiện khuôn mặt bằng YuNet, kiểm tra Liveness, và trích xuất đặc trưng để so sánh. Nếu độ tương đồng vượt ngưỡng cho phép và được xác nhận là người thật, ứng dụng sẽ hiển thị khung viền màu xanh lá cây kèm tên nhân viên và thông báo điểm danh thành công.
  
  > `[Placeholder: Hình 4.1. Giao diện màn hình điểm danh khi nhận diện thành công]`

- **Chức năng cảnh báo giả mạo (Anti-Spoofing):** Trong trường hợp người dùng cố tình đưa ảnh in trên giấy, hoặc sử dụng màn hình điện thoại/máy tính bảng có hình khuôn mặt, mô hình MiniFASNet V2 SE sẽ phát hiện dấu hiệu giả mạo 2D. Lúc này, hệ thống sẽ khoanh vùng khuôn mặt bằng khung viền màu đỏ và hiển thị cảnh báo "Spoofing Detected" (Phát hiện giả mạo), từ chối ghi nhận kết quả điểm danh.

  > `[Placeholder: Hình 4.2. Giao diện màn hình cảnh báo khi đưa ảnh điện thoại (Spoofing)]`

### 4.2.2. Giao diện quản lý nhân viên và lịch sử

Giao diện này dành cho Quản trị viên (Admin), yêu cầu đăng nhập bằng mật khẩu (đã mã hóa bcrypt) để đảm bảo an toàn thông tin.

- **Quản lý nhân viên (Employee Management):** Quản trị viên có thể xem danh sách toàn bộ nhân viên, thêm mới, chỉnh sửa thông tin hoặc xóa nhân viên. Đặc biệt, chức năng thêm nhân viên tích hợp khả năng thu thập dữ liệu khuôn mặt ngay từ luồng Webcam phụ, tự động trích xuất vector đặc trưng và lưu vào SQLite.
  
  > `[Placeholder: Hình 4.3. Giao diện danh sách quản lý nhân viên]`
  
  > `[Placeholder: Hình 4.4. Màn hình thu thập dữ liệu khuôn mặt cho nhân viên mới]`

- **Lịch sử điểm danh (Attendance History):** Bảng dữ liệu liệt kê chi tiết thời gian (đã được tự động chuyển đổi từ UTC trong CSDL sang giờ địa phương) và trạng thái điểm danh của từng nhân viên. Admin có thể lọc lịch sử theo khoảng thời gian hoặc tìm kiếm theo tên nhân viên.
  
  > `[Placeholder: Hình 4.5. Giao diện xem và lọc lịch sử điểm danh]`

### 4.2.3. Giao diện cấu hình hệ thống

Phần Cấu hình (Settings) cho phép Admin điều chỉnh linh hoạt các thông số kỹ thuật cốt lõi của hệ thống mà không cần can thiệp vào mã nguồn:

- **Cấu hình thiết bị:** Thay đổi chỉ số Camera (Camera Index) nếu sử dụng nhiều Webcam và xem đường dẫn lưu trữ CSDL.
- **Cấu hình AI (AI Models):** Điều chỉnh ngưỡng chấp nhận (Threshold) cho mô hình nhận diện khuôn mặt và ngưỡng Liveness. Việc này giúp cân bằng độ nhạy của hệ thống tùy thuộc vào điều kiện ánh sáng thực tế nơi triển khai.
- **Cấu hình hệ thống chung:** Thay đổi múi giờ (Timezone) để đồng bộ hiển thị chính xác giờ điểm danh. Các thiết lập này được lưu an toàn trực tiếp vào CSDL và có cơ chế nạp lại (seed) tự động mỗi khi khởi động ứng dụng.

  > `[Placeholder: Hình 4.6. Giao diện màn hình Cấu hình hệ thống (Settings)]`

## 4.3. Đánh giá hệ thống

Quá trình đánh giá được thực hiện trên môi trường cấu hình đã nêu ở phần 4.1. Mục tiêu là kiểm chứng khả năng đáp ứng thời gian thực (real-time) và độ chính xác của hệ thống trong môi trường ngoại tuyến (offline).

### 4.3.1. Đánh giá hiệu năng xử lý

Hiệu năng được đo lường dựa trên hai chỉ số chính: Tốc độ khung hình (FPS - Frames Per Second) của toàn bộ luồng Camera và thời gian suy luận (Inference Time) của các mô hình AI khi chạy hoàn toàn trên CPU.

| Chỉ số đánh giá                                    | Giá trị đo lường trung bình | Ghi chú                                          |
| :------------------------------------------------- | :-------------------------: | :----------------------------------------------- |
| **Thời gian Inference (Face Detection - YuNet)**   |         ~15 - 20 ms         | Xử lý tốc độ cao để tìm tọa độ                   |
| **Thời gian Inference (Liveness - MiniFASNet)**    |         ~40 - 50 ms         | Thực thi với mô hình đã lượng tử hóa (Quantized) |
| **Thời gian Inference (Face Recognition - SFace)** |         ~30 - 40 ms         | Chỉ kích hoạt khi vượt qua bước Liveness         |
| **Tốc độ khung hình hiển thị (UI FPS)**            |        ~25 - 30 FPS         | Giao diện hiển thị mượt mà, không giật lag       |

*Nhận xét:* Kiến trúc tách biệt AI Worker Thread và UI Thread cùng cơ chế xử lý AI cách quãng (Frame Skip) giúp ứng dụng luôn duy trì hiển thị Camera mượt mà ở mức 30 FPS, ngay cả khi CPU phải tải các mạng học sâu nặng.

### 4.3.2. Đánh giá độ chính xác qua kịch bản thực tế

Độ chính xác của hệ thống được kiểm thử thủ công qua nhiều kịch bản mô phỏng các tình huống sử dụng thực tế:

**Bảng 4.2. Kết quả kiểm thử Nhận diện khuôn mặt (Face Recognition)**

| Kịch bản kiểm thử      | Mô tả chi tiết                                      |     Kết quả nhận diện      |
| :--------------------- | :-------------------------------------------------- | :------------------------: |
| Điều kiện ánh sáng tốt | Môi trường phòng làm việc, ánh sáng sáng đều.       |        Đạt (> 98%)         |
| Điều kiện thiếu sáng   | Tắt bớt đèn, chủ yếu dùng ánh sáng hắt từ màn hình. |       Khá (~ 85-90%)       |
| Góc mặt nghiêng nhẹ    | Mặt xoay ngang hoặc cúi nhẹ (< 15 độ).              |        Đạt (> 95%)         |
| Có vật cản khuôn mặt   | Đeo kính râm đen, đeo khẩu trang che khuất cằm/mũi. | Hệ thống từ chối nhận diện |

**Bảng 4.3. Kết quả kiểm thử Chống giả mạo (Anti-Spoofing / Liveness)**

| Hình thức giả mạo              | Mô tả kịch bản                                         |       Tỷ lệ chặn giả mạo thành công       |
| :----------------------------- | :----------------------------------------------------- | :---------------------------------------: |
| **Người thật (Live)**          | Người dùng thực sự đứng điểm danh trước Camera.        |      Điểm danh thành công (TP ~ 98%)      |
| **Ảnh in giấy (Printed)**      | Sử dụng ảnh màu in trên giấy cứng đưa ra trước Camera. | Chặn thành công (Spoofing Detected ~ 99%) |
| **Màn hình thiết bị (Replay)** | Mở ảnh/video khuôn mặt trên màn hình điện thoại, iPad. | Chặn thành công (Spoofing Detected ~ 95%) |

*Nhận xét:* Hệ thống MiniFASNet V2 SE chống giả mạo 2D hoạt động rất hiệu quả đối với các rủi ro phổ biến trong môi trường văn phòng, giảm thiểu tối đa các trường hợp gian lận bằng hình ảnh truyền thống.

### 4.3.3. Đánh giá mức tiêu thụ tài nguyên

Do tính chất hoạt động hoàn toàn offline, việc kiểm soát tài nguyên phần cứng là yếu tố sống còn để triển khai diện rộng. Dữ liệu được đo lường thông qua Task Manager trên hệ điều hành Windows:

| Trạng thái hoạt động                             | Mức tiêu thụ RAM | Mức tiêu thụ CPU (AMD Ryzen 5) |
| :----------------------------------------------- | :--------------: | :----------------------------: |
| **Trạng thái nghỉ (Chỉ hiển thị Camera)**        |  ~150 - 200 MB   |            ~5 - 10%            |
| **Trạng thái điểm danh (AI tính toán liên tục)** |  ~350 - 450 MB   |           ~20 - 30%            |

*Nhận xét:* Nhờ tối ưu hóa bằng ONNX Runtime và cấu trúc thư viện nhẹ, ứng dụng chỉ tiêu tốn lượng RAM rất nhỏ (< 500MB). Điều này cho phép hệ thống chạy liên tục và ổn định trên các máy tính Desktop cấu hình văn phòng hoặc Kiosk truyền thống mà không làm gián đoạn các phần mềm chạy ngầm khác.
