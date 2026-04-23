# TÀI LIỆU ĐẶC TẢ YÊU CẦU PHẦN MỀM (SRS)

**Tên đề tài:** Xây Dựng Hệ Thống Điểm Danh Sử Dụng Nhận Diện Khuôn Mặt Và Chống Giả Mạo

**Loại tài liệu:** Software Requirements Specification (SRS)

**Phiên bản:** 2.0

**Sinh viên thực hiện:** [Họ và Tên] – [MSSV]

**Giáo viên hướng dẫn:** [Họ và Tên GVHD]

**Đơn vị:** [Tên Khoa] – [Tên Trường]

**Ngày:** [Ngày/Tháng/Năm]

## Lịch Sử Chỉnh Sửa Tài Liệu

|   |   |   |   |
|---|---|---|---|
|**Phiên bản**|**Ngày**|**Người thực hiện**|**Nội dung thay đổi**|
|0.1|[Ngày]|[Họ tên]|Tạo bản nháp đầu tiên|
|1.0|[Ngày]|[Họ tên]|Hoàn thiện bản chính thức v1.0|
|2.0|[Ngày]|[Họ tên]|Chuẩn hóa định dạng. Bổ sung quản lý Lớp/Môn học. Thêm tính năng Cấu hình hệ thống (Ngưỡng AI, Camera). Tách biệt Use Case Xuất báo cáo. Bổ sung yêu cầu quyền riêng tư dữ liệu.|

## PHẦN 1 – GIỚI THIỆU

### 1.1 Mục Đích Tài Liệu

Tài liệu này mô tả đầy đủ các yêu cầu chức năng và phi chức năng của hệ thống điểm danh tự động sử dụng nhận diện khuôn mặt kết hợp cơ chế chống giả mạo (anti-spoofing). Tài liệu phục vụ cho quá trình phân tích, thiết kế, triển khai và kiểm thử trong khuôn khổ đồ án tốt nghiệp. Đối tượng đọc tài liệu này gồm: sinh viên thực hiện đề tài, giáo viên hướng dẫn, và hội đồng phản biện.

### 1.2 Phạm Vi Hệ Thống

Hệ thống là một ứng dụng desktop chạy trên máy tính cá nhân hoặc máy tính của phòng học. Ứng dụng cho phép điểm danh tự động thông qua nhận diện khuôn mặt qua webcam, không yêu cầu người dùng thao tác phức tạp. Hệ thống phục vụ hai nhóm đối tượng:

- **Người dùng thông thường (User):** Giảng viên hoặc người phụ trách buổi học. Mở app, chọn môn học/lớp học và quản lý phiên điểm danh bằng phím tắt, không cần tài khoản.
    
- **Quản trị viên (Admin):** Đăng nhập bằng tài khoản để quản lý dữ liệu người dùng, đăng ký khuôn mặt, cấu hình hệ thống và trích xuất báo cáo.
    

Sinh viên không cần thao tác gì — chỉ cần đứng trước camera trong phiên điểm danh đang mở.

### 1.3 Định Nghĩa và Từ Viết Tắt

|                        |                                                                                      |
| ---------------------- | ------------------------------------------------------------------------------------ |
| **Thuật ngữ**          | **Giải thích**                                                                       |
| **SRS**                | Software Requirements Specification – Đặc tả yêu cầu phần mềm                        |
| **DeepFace**           | Thư viện Python mã nguồn mở hỗ trợ nhận diện khuôn mặt (VGG-Face, ArcFace, FaceNet…) |
| **MiniFASNet**         | Mô hình liveness detection nhẹ, thuộc bộ Silent-Face-Anti-Spoofing                   |
| **Liveness Detection** | Kỹ thuật phân biệt khuôn mặt người thật với ảnh/video giả mạo                        |
| **Embedding**          | Vector số chiều cao biểu diễn đặc trưng khuôn mặt, dùng để so sánh nhận diện         |
| **Pipeline**           | Chuỗi các bước xử lý tuần tự: detect → liveness → recognize                          |
| **FAR / FRR**          | False Acceptance Rate (Nhận nhầm) / False Rejection Rate (Từ chối nhầm)              |
| **IDLE / ACTIVE**      | Trạng thái chờ của app (IDLE) / Trạng thái đang chạy phiên điểm danh (ACTIVE)        |

### 1.4 Tài Liệu Tham Khảo

1. Serengil, S. I., & Ozpinar, A. (2020). LightFace: A Hybrid Deep Face Recognition Framework.
    
2. Liu, S. et al. (2021). Silent-Face-Anti-Spoofing. GitHub Repository.
    
3. IEEE Standard 830-1998: Recommended Practice for Software Requirements Specifications.
    

## PHẦN 2 – MÔ TẢ TỔNG QUAN HỆ THỐNG

### 2.1 Bối Cảnh và Vấn Đề

Phương pháp điểm danh thủ công tốn nhiều thời gian và dễ xảy ra gian lận. Nhận diện khuôn mặt giải quyết vấn đề tốc độ nhưng dễ bị tấn công giả mạo (spoofing) bằng ảnh/video. Đề tài kết hợp DeepFace (nhận diện) và MiniFASNet (liveness) nhằm xây dựng ứng dụng điểm danh Nhanh - Chính xác - Khó gian lận.

### 2.2 Kiến Trúc Tổng Quát

Hệ thống gồm ba thành phần chính chạy trong cùng một ứng dụng desktop:

1. **Giao diện (GUI):** Xây dựng bằng Tkinter/PyQt5, hiển thị camera, kết quả trực tiếp, và các màn hình quản trị.
    
2. **AI Engine:** Chạy trên thread (luồng) riêng để không làm đơ giao diện. Thực hiện pipeline AI trên từng khung hình.
    
3. **Cơ sở dữ liệu:** SQLite cục bộ (offline) lưu thông tin người dùng, embedding, lịch sử và cấu hình.
    

### 2.3 Đối Tượng Sử Dụng

|   |   |   |
|---|---|---|
|**Vai trò**|**Mô tả**|**Cách truy cập**|
|**Sinh viên**|Đứng trước camera để điểm danh tự động|Không cần thao tác trên app|
|**User (Giảng viên)**|Mở/đóng phiên điểm danh, chọn lớp học|Mở app → dùng UI/phím tắt|
|**Admin (Quản trị)**|Quản lý dữ liệu, đăng ký khuôn mặt, cấu hình|Đăng nhập bằng tài khoản|

### 2.4 Giả Định và Ràng Buộc Chung

- Webcam hoạt động tốt, tối thiểu HD 720p, điều kiện ánh sáng phòng học tiêu chuẩn.
    
- Chỉ có một tài khoản Admin duy nhất (tạo sẵn khi khởi tạo CSDL).
    
- App hoạt động 100% offline, không yêu cầu Internet (đảm bảo tính bảo mật và độc lập).
    

## PHẦN 3 – YÊU CẦU CHỨC NĂNG

### 3.1 Tổng Quan Các Chức Năng

**Nhóm User Mode (Không cần đăng nhập):**

- UC-01: Khởi động và điều hướng ứng dụng
    
- UC-02: Bắt đầu phiên điểm danh (Có chọn thông tin Lớp/Môn)
    
- UC-03: Điểm danh tự động (Pipeline Nhận diện)
    
- UC-04: Kết thúc phiên điểm danh
    
- UC-05: Thoát ứng dụng
    

**Nhóm Admin Mode (Yêu cầu đăng nhập):**

- UC-06: Đăng nhập / Đăng xuất
    
- UC-07: Quản lý người dùng (CRUD)
    
- UC-08: Đăng ký khuôn mặt (Lấy Embedding)
    
- UC-09: Xem và quản lý lịch sử điểm danh
    
- UC-10: Cấu hình hệ thống (Camera, Ngưỡng AI)
    
- UC-11: Xuất báo cáo điểm danh
    

### 3.2 Chi Tiết Các Use Case Quan Trọng

**UC-02: Bắt Đầu Phiên Điểm Danh**

- **Tác nhân:** User (Giảng viên)
    
- **Luồng chính:**
    
    1. Trạng thái app: IDLE. User chọn "Bắt đầu điểm danh".
        
    2. Hệ thống yêu cầu nhập/chọn thông tin: **Tên Môn Học** và **Tên Lớp**.
        
    3. User nhấn nút "Khởi động Camera" hoặc phím `S`.
        
    4. Hệ thống tạo bản ghi session mới trong DB, bật luồng Camera.
        
    5. Giao diện chuyển sang ACTIVE.
        

**UC-03: Điểm Danh Tự Động Bằng AI (Cốt lõi)**

- **Kích hoạt:** Tự động chạy trên từng frame ảnh khi ở trạng thái ACTIVE.
    
- **Luồng xử lý:**
    
    1. Đọc frame từ Camera → Phát hiện khuôn mặt (Face Detection).
        
    2. Gửi vùng khuôn mặt qua MiniFASNet. Nếu `liveness_score < threshold_config`: Cảnh báo giả mạo, ghi Log, bỏ qua.
        
    3. Nếu là người thật: Gửi qua DeepFace trích xuất Embedding.
        
    4. So sánh Embedding với CSDL. Nếu `similarity_score > threshold_config`: Xác định danh tính.
        
    5. Kiểm tra trùng lặp trong phiên. Nếu chưa có: Ghi DB thành công.
        
- **Phản hồi UI:** ✅ Xanh (Thành công kèm Tên) | ⚠️ Vàng (Đã điểm danh) | 🚫 Đỏ (Giả mạo/Không nhận ra).
    

**UC-08: Đăng Ký Khuôn Mặt**

- **Tác nhân:** Admin
    
- **Luồng chính:** Chọn người dùng → Bật Camera → Hệ thống hướng dẫn "Nhìn thẳng, xoay nhẹ" → Chụp tự động 3-5 tấm đạt chuẩn → Tính toán Embedding trung bình → Lưu vào CSDL (Không lưu ảnh gốc).
    

**UC-10: Cấu Hình Hệ Thống (Mới)**

- **Tác nhân:** Admin
    
- **Chức năng:** Cho phép chọn thiết bị đầu vào (Camera Index: 0, 1, 2...). Cho phép điều chỉnh thanh trượt (slider) ngưỡng Liveness (mặc định 0.5) và ngưỡng Similarity của DeepFace.
    

**UC-11: Xuất Báo Cáo (Mới)**

- **Tác nhân:** Admin / User (sau khi kết thúc phiên)
    
- **Chức năng:** Trích xuất dữ liệu của một phiên điểm danh ra file Excel (.xlsx) hoặc CSV. File bao gồm: Mã SV, Họ Tên, Môn Học, Lớp, Thời gian đến, Trạng thái (Hợp lệ / Giả mạo).
    

## PHẦN 4 – YÊU CẦU PHI CHỨC NĂNG

### 4.1 Hiệu Năng (Performance)

- Thời gian xử lý toàn pipeline ≤ 1.5 - 2 giây/lượt người.
    
- Giao diện người dùng duy trì ít nhất 24 FPS (Frames Per Second) khi đang bật camera, không bị giật lag nhờ kiến trúc đa luồng.
    
- **Độ chính xác:** FAR ≤ 1% (rất khó nhận nhầm người lạ), FRR ≤ 5% (từ chối nhầm người thật).
    

### 4.2 Bảo Mật & Quyền Riêng Tư (Security & Privacy)

- Mật khẩu Admin được băm (hash) bằng bcrypt.
    
- **Privacy by Design:** Hệ thống TUYỆT ĐỐI KHÔNG lưu trữ ảnh chụp khuôn mặt gốc của sinh viên sau khi hoàn tất đăng ký. Chỉ lưu chuỗi số đặc trưng (Vector Embedding) không thể dịch ngược lại thành ảnh.
    
- Mọi dữ liệu nằm gọn trong file SQLite cục bộ, loại trừ rủi ro rò rỉ dữ liệu qua mạng internet.
    

### 4.3 Khả Năng Sử Dụng (Usability)

- Thiết kế tối giản: User chỉ cần 3 phím tắt (S: Start, E: End, Q: Quit) để vận hành trong lớp học.
    
- Cảnh báo trực quan, phông chữ lớn dễ nhìn từ khoảng cách 2-3 mét.
    

## PHẦN 5 – MÔI TRƯỜNG VÀ CÔNG NGHỆ

|   |   |   |
|---|---|---|
|**Thành phần**|**Công nghệ được chọn**|**Lý do**|
|**Ngôn ngữ**|Python 3.9+|Hệ sinh thái AI mạnh mẽ nhất, dễ tích hợp.|
|**Nhận diện khuôn mặt**|DeepFace|Bọc sẵn pipeline (detect, align, represent), dễ dùng.|
|**Liveness Detection**|MiniFASNet|Siêu nhẹ (~1MB), chạy mượt trên CPU, hiệu quả với ảnh in/video 2D.|
|**Giao diện (GUI)**|PyQt5 / Tkinter|Xây dựng ứng dụng desktop độc lập nhanh chóng.|
|**Cơ sở dữ liệu**|SQLite3|Nhúng trực tiếp, zero-configuration, dễ backup file.|
|**Xử lý luồng/ảnh**|Threading, OpenCV|Xử lý bất đồng bộ, thao tác với webcam chuẩn xác.|

## PHẦN 6 – THIẾT KẾ CƠ SỞ DỮ LIỆU (Cập nhật)

**Bảng `users` (Sinh viên/Nhân viên)**

|   |   |   |
|---|---|---|
|**Cột**|**Kiểu**|**Mô tả**|
|`id`|INTEGER PK|Khóa chính|
|`student_id`|TEXT UNIQUE|Mã sinh viên/nhân viên|
|`full_name`|TEXT|Họ và tên|
|`face_registered`|INTEGER|0 (Chưa), 1 (Đã đăng ký)|

**Bảng `face_embeddings` (Đặc trưng khuôn mặt)**

|   |   |   |
|---|---|---|
|**Cột**|**Kiểu**|**Mô tả**|
|`user_id`|INTEGER PK|Khóa ngoại (1-1 với users)|
|`embedding_blob`|BLOB|Vector dạng byte (Pickle/Numpy)|

**Bảng `sessions` (Phiên điểm danh - Đã cập nhật)**

|   |   |   |
|---|---|---|
|**Cột**|**Kiểu**|**Mô tả**|
|`id`|INTEGER PK|Khóa chính|
|`subject_name`|TEXT|Tên môn học (Ví dụ: Trí tuệ nhân tạo)|
|`class_name`|TEXT|Tên lớp (Ví dụ: IT01)|
|`start_time`|TEXT|Thời gian bắt đầu (ISO 8601)|
|`end_time`|TEXT|Thời gian kết thúc|

**Bảng `attendance_records` (Lịch sử điểm danh)**

|   |   |   |
|---|---|---|
|**Cột**|**Kiểu**|**Mô tả**|
|`id`|INTEGER PK|Khóa chính|
|`session_id`|INTEGER|FK -> sessions.id|
|`user_id`|INTEGER|FK -> users.id|
|`timestamp`|TEXT|Thời gian điểm danh|
|`status`|TEXT|'SUCCESS', 'SPOOF_WARNING'|

**Bảng `system_settings` (Cấu hình - Mới)**

|   |   |   |
|---|---|---|
|**Cột**|**Kiểu**|**Mô tả**|
|`key`|TEXT PK|Tên cấu hình (VD: `liveness_threshold`)|
|`value`|TEXT|Giá trị tương ứng (VD: `0.7`)|

## PHẦN 7 – KIỂM THỬ

### 7.1 Kịch Bản Kiểm Thử Hệ Thống (System Testing)

|   |   |   |   |
|---|---|---|---|
|**ID**|**Kịch bản**|**Đầu vào**|**Kết quả mong đợi**|
|T01|Nhận diện đúng danh tính|SV đã đăng ký đứng trước cam|✅ Hiển thị Tên, ghi DB (≤ 2s)|
|T02|Nhận diện người lạ|Người chưa đăng ký|❌ "Không nhận diện được"|
|T03|Tấn công ảnh in (Print)|Đưa ảnh chụp A4 ra trước cam|🚫 Cảnh báo giả mạo, ghi Log|
|T04|Tấn công video (Replay)|Phát video trên màn hình đt|🚫 Cảnh báo giả mạo|
|T05|Thay đổi cấu hình|Sửa ngưỡng liveness trong cài đặt|✅ Hệ thống áp dụng ngay lập tức|
|T06|Xuất báo cáo|Nhấn nút Export sau phiên|✅ Sinh ra file Excel chứa đủ dữ liệu|

## PHẦN 8 – RỦI RO VÀ BIỆN PHÁP GIẢM THIỂU

|   |   |   |
|---|---|---|
|**Rủi ro**|**Mức độ**|**Biện pháp khắc phục**|
|**Ánh sáng kém gây sai số**|Cao|Cung cấp tính năng tùy chỉnh Ngưỡng (Threshold) trong app. Hướng dẫn setup đèn lớp học.|
|**Lag giật trên máy yếu**|Trung bình|Resize frame ảnh xuống 480p trước khi đưa vào AI Pipeline. Skip frame (xử lý 10 FPS thay vì 30).|
|**Thiếu dữ liệu huấn luyện**|Cao|Thu thập ảnh thực tế từ các bạn cùng lớp, kết hợp Data Augmentation.|
|**Mất dữ liệu do cúp điện**|Thấp|Cấu hình SQLite commit ngay lập tức (Auto-commit) mỗi khi một người điểm danh xong.|

## PHẦN 9 – KẾ HOẠCH THỰC HIỆN

|   |   |   |
|---|---|---|
|**Giai đoạn**|**Nội dung công việc**|**Thời gian**|
|**1. Khởi tạo & Nghiên cứu**|Setup môi trường, chạy thử DeepFace & MiniFASNet độc lập.|Tuần 1-2|
|**2. Thu thập dữ liệu**|Xây dựng kịch bản lấy ảnh, tạo tool lấy Embedding tự động.|Tuần 3-4|
|**3. Tích hợp AI Pipeline**|Ghép nối Detect -> Liveness -> Recognize chạy đa luồng.|Tuần 5-7|
|**4. Phát triển GUI & DB**|Code giao diện PyQt5/Tkinter. Kết nối SQLite, chức năng Export.|Tuần 8-10|
|**5. Testing & Tối ưu**|UAT test ở phòng học thực tế, chỉnh ngưỡng, tối ưu FPS.|Tuần 11-13|
|**6. Hoàn thiện đồ án**|Viết báo cáo, làm slide, đóng gói ứng dụng (file .exe).|Tuần 14-15|

_(Tài liệu phiên bản 2.0 - Phục vụ phát triển và nghiệm thu đề tài)_