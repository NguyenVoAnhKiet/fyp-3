# CHƯƠNG 1. GIỚI THIỆU ĐỀ TÀI

## 1.1. LÝ DO CHỌN ĐỀ TÀI

Trong bối cảnh cuộc Cách mạng Công nghiệp 4.0 và xu hướng chuyển đổi số mạnh mẽ trong giáo dục, việc ứng dụng Trí tuệ nhân tạo (AI) vào công tác quản lý học đường đã trở thành một giải pháp thiết yếu nhằm tinh gọn bộ máy vận hành và tối ưu hóa thời gian giảng dạy. Một trong những tác vụ hành chính có tần suất thực hiện cao nhưng lại tiêu tốn nhiều thời gian nhất của giảng viên trong mỗi buổi học chính là hoạt động điểm danh sinh viên.

Để thấy rõ tính thiết thực và cấp bách của đề tài, bảng dưới đây đối chiếu chi tiết hiệu năng và tính thực tiễn giữa giải pháp đề xuất so với các phương thức điểm danh truyền thống và bán tự động hiện nay:

**Bảng 1.1: Ma trận so sánh giải pháp đề xuất với các phương pháp hiện hành**

|                                |                                                                                                                                                    |                                                                                                               |
| ------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------- |
| **Tiêu chí so sánh**           | **Phương pháp điểm danh hiện hành(Ký danh / Thẻ từ RFID / Vân tay / Face truyền thống)**                                                           | **Giải pháp đề xuất của đề tài(Face Recognition + Face Anti-Spoofing Offline)**                               |
| **Hiệu suất thời gian**        | - Điểm danh truyền thống: Rất tốn thời gian ($10\% - 15\%$ tiết học).<br><br>  <br><br>- Thẻ từ / Vân tay: Trung bình ($2 - 5\text{ giây/người}$). | **Tối ưu vượt trội:** Thời gian nhận diện và ghi nhận trạng thái cực nhanh ($< 1\text{ giây/người}$).         |
| **An toàn dịch tễ & Tiếp xúc** | - Máy quét vân tay: Thấp (Nhiều người tiếp xúc chung bề mặt cảm biến).<br><br>  <br><br>- Thẻ từ / Điểm danh giấy: Trung bình.                     | **Cao tuyệt đối:** Xác thực không tiếp xúc vật lý thông qua camera giám sát từ xa.                            |
| **Khả năng chống gian lận**    | - Ký danh / Thẻ từ: Rất thấp (Dễ ký hộ, trao đổi thẻ từ).<br><br>  <br><br>- Face truyền thống: Thấp (Dễ bị bypass bằng ảnh in/video).             | **Tuyệt đối:** Tích hợp bộ lọc chống giả mạo thụ động ngăn chặn triệt để ảnh chụp 2D và video tái phát.       |
| **Chi phí đầu tư phần cứng**   | - Vân tay / RFID: Phát sinh chi phí mua thiết bị quét chuyên dụng.<br><br>  <br><br>- Face truyền thống: Chi phí cao (Yêu cầu Cloud/GPU đắt tiền). | **Tối thiểu:** Tối ưu hóa thuật toán chạy offline trực tiếp trên các cấu hình CPU văn phòng và webcam sẵn có. |

Rào cản lớn nhất của hệ thống nhận diện khuôn mặt thông thường là tính dễ bị tổn thương trước các hành vi gian lận trình diện. Bảng dưới đây phân loại chi tiết hai dạng tấn công trình diện giả mạo phổ biến nhằm định hình cơ chế phòng vệ cho hệ thống:

**Bảng 1.2: Các dạng tấn công trình diện giả mạo (Presentation Attacks - PA) và Cơ chế phòng vệ**

|   |   |   |
|---|---|---|
|**Nhóm tấn công**|**Đặc trưng vật lý và Biểu hiện**|**Rủi ro bảo mật & Cơ chế phòng vệ đề xuất**|
|**Tấn công tĩnh 2D (Print Attack)**|- Sử dụng ảnh in chân dung màu hoặc trắng đen chụp sinh viên.<br><br>  <br><br>- Bề mặt phẳng ($2\text{D}$), không có sự thay đổi kết cấu da.<br><br>  <br><br>- Xuất hiện các loại nhiễu vật lý do vân ảnh in (moiré patterns).|- Dễ dàng bypass các hệ thống nhận diện thông thường.<br><br>  <br><br>- **Phòng vệ:** Sử dụng mô hình MiniFASNet để phân tích độ phân bổ tần số cao của cấu trúc bề mặt da thật so với giấy in.|
|**Tấn công động 2D (Replay Attack)**|- Phát lại video cử động khuôn mặt từ màn hình điện tử.<br><br>  <br><br>- Bề mặt phẳng có độ tương phản giả mạo và phản xạ ánh sáng.<br><br>  <br><br>- Hiện tượng lệch tần số quét màn hình gây nhiễu khung hình.|- Mô phỏng được các cử động cơ bản nhằm đánh lừa các cơ chế cũ.<br><br>  <br><br>- **Phòng vệ:** Kết hợp MiniFASNet với bộ lọc mịn thời gian thực (EMA) để theo dõi tính liên tục sinh học.|

Sự kết hợp giữa công nghệ nhận dạng khuôn mặt và mô hình chống giả mạo thụ động là chìa khóa then chốt giúp xây dựng một hệ thống điểm danh an toàn, minh bạch, vận hành ổn định trên các phần cứng có sẵn tại các nhà trường.

## 1.2. MỤC TIÊU NGHIÊN CỨU

Mục tiêu chung của đề tài là nghiên cứu, thiết kế và xây dựng hoàn chỉnh một ứng dụng điểm danh tự động hoạt động cục bộ (offline), có khả năng nhận diện chính xác danh tính sinh viên thông qua camera giám sát lớp học, đồng thời ngăn chặn hiệu quả các hành vi điểm danh giả mạo bằng ảnh in hoặc video tái phát.

Các mục tiêu thành phần cụ thể cùng các chỉ số đo lường kết quả được phân rã chi tiết trong bảng dưới đây:

**Bảng 1.3: Phân rã mục tiêu nghiên cứu và Chỉ số đánh giá kết quả (KPIs)**

|   |   |   |
|---|---|---|
|**Mục tiêu nghiên cứu**|**Nội dung triển khai chi tiết**|**Chỉ số đo lường kết quả hoàn thành (KPIs)**|
|**1. Nghiên cứu lý thuyết**|- Khảo sát các thuật toán định vị và trích xuất điểm mốc khuôn mặt.<br><br>  <br><br>- Nghiên cứu lý thuyết chống giả mạo thụ động dựa trên mạng CNN.<br><br>  <br><br>- Tìm hiểu hàm mất mát biên góc trong so khớp sinh trắc học.|Báo cáo chi tiết về cơ sở lý thuyết, kiến trúc vận hành của bộ ba mô hình học sâu rút gọn: YuNet, SFace và MiniFASNet.|
|**2. Xây dựng AI Pipeline**|- Tích hợp YuNet, MiniFASNet và SFace vào một luồng tuần tự.<br><br>  <br><br>- Thiết lập bộ lọc mịn thời gian thực và xử lý ngưỡng trễ.|- Đường ống xử lý AI khép kín, tối ưu hóa bộ nhớ.<br><br>  <br><br>- Loại bỏ hoàn toàn hiện tượng nhấp nháy trạng thái (state flickering).|
|**3. Phát triển ứng dụng**|- Thiết kế giao diện máy tính để bàn (Desktop App) bằng PyQt5.<br><br>  <br><br>- Quản trị cơ sở dữ liệu sinh viên và lịch sử bằng SQLite3.<br><br>  <br><br>- Mã hóa mật mã bảo vệ an toàn vector đặc trưng khuôn mặt.|- Ứng dụng Desktop chạy offline độc lập $100\%$.<br><br>  <br><br>- Xử lý luồng video camera mượt mà, không giật lag.<br><br>  <br><br>- Bảo mật toàn vẹn dữ liệu cá nhân sinh viên cục bộ.|
|**4. Đánh giá thực nghiệm**|- Thiết lập kịch bản kiểm thử giả mạo (Print/Replay) và thật.<br><br>  <br><br>- Đo đạc tốc độ suy luận và sai số thực tế trên CPU biên.|- Tốc độ xử lý video thực tế: $\text{FPS} \ge 15$ trên CPU thông thường.<br><br>  <br><br>- Chỉ số sai số chống giả mạo: $\text{ACER} \le 3\%$.<br><br>  <br><br>- Chỉ số sai số nhận diện sinh viên: $\text{FAR} \le 0.1\%$.|

## 1.3. ĐỐI TƯỢNG VÀ PHẠM VI NGHIÊN CỨU

Để định hướng nghiên cứu tập trung và khả thi, đối tượng và giới hạn phạm vi nghiên cứu được thiết lập rõ ràng thông qua hai bảng phân cấu trúc dưới đây:

**Bảng 1.4: Phân loại đối tượng nghiên cứu sinh trắc học và xử lý tín hiệu**

|                                     |                                                                                        |                                                                                                                                                                                                                                    |
| ----------------------------------- | -------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Đối tượng nghiên cứu**            | **Thành phần kỹ thuật cụ thể**                                                         | **Vai trò trong vận hành hệ thống**                                                                                                                                                                                                |
| **Mô hình học sâu (Deep Learning)** | - Mô hình YuNet<br><br>  <br><br>- Mô hình SFace<br><br>  <br><br>- Mô hình MiniFASNet | - Định vị khuôn mặt và xác định vị trí 5 điểm mốc sinh học.<br><br>  <br><br>- Trích xuất vùng mặt thật thành vector đặc trưng nhúng $128\text{ chiều}$.<br><br>  <br><br>- Phân loại thực thể sống và lọc tấn công giả mạo (FAS). |
| **Thuật toán khoảng cách**          | - Khoảng cách Cosine<br><br>  <br><br>- Khoảng cách Euclid                             | - Đo lường độ tương đồng giữa hai vector đặc trưng khuôn mặt.<br><br>  <br><br>- Cơ sở đưa ra quyết định chấp nhận/từ chối sinh viên.                                                                                              |
| **Xử lý tín hiệu thời gian**        | - Exponential Moving Average (EMA)<br><br>  <br><br>- Ngưỡng trễ kép (Hysteresis)      | - Lọc mượt điểm số liveness biến động qua các khung hình.<br><br>  <br><br>- Tránh việc nhảy trạng thái (REAL $\leftrightarrow$ SPOOF) liên tục do ánh sáng.                                                                       |

**Bảng 1.5: Giới hạn phạm vi triển khai thực tế của đề tài**

|                      |                                                                                                                                                                                                               |                                                                                                                                   |
| -------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------- |
| **Trụ cột phạm vi**  | **Giới hạn triển khai thực tế**                                                                                                                                                                               | **Lý do kỹ thuật và thực tiễn**                                                                                                   |
| **Về mặt Công nghệ** | - Hệ thống hoạt động ngoại tuyến hoàn toàn ($100\%$ Offline).<br><br>  <br><br>- Thực thi suy luận thông qua ONNX Runtime trên CPU.<br><br>  <br><br>- Lưu trữ dữ liệu và vector đặc trưng mẫu trong SQLite3. | Bảo vệ quyền riêng tư dữ liệu cá nhân theo Nghị định 13/2023/NĐ-CP; loại bỏ phụ thuộc vào đường truyền Internet và máy chủ Cloud. |
| **Về mặt Thiết bị**  | - Chỉ sử dụng Webcam RGB thông thường tích hợp sẵn.<br><br>  <br><br>- Không sử dụng cảm biến chiều sâu (IR/Depth Camera).                                                                                    | Tiết kiệm chi phí đầu tư thiết bị đầu cuối cho nhà trường; tăng tính khả thi và phổ quát khi triển khai rộng rãi.                 |
| **Về mặt Quy mô**    | - Áp dụng trong phòng học quy mô nhỏ và vừa ($< 200\text{ sinh viên}$).<br><br>  <br><br>- Chống tấn công dạng phẳng ($2\text{D}$ Print & Replay Attack).                                                     | Đảm bảo hiệu năng tính toán thời gian thực của CPU; giải quyết triệt để các kịch bản gian lận phổ biến nhất trong lớp học.        |

## 1.4. Ý NGHĨA KHOA HỌC VÀ THỰC TIỄN

Đóng góp của đề tài được thể hiện rõ nét trên cả hai khía cạnh nghiên cứu lý thuyết học thuật và ứng dụng thực tiễn trong môi trường giáo dục số hóa:

**Bảng 1.6: Giá trị đóng góp khoa học và thực tiễn của đề tài**

|   |   |
|---|---|
|**Giá trị đóng góp về mặt Khoa học**|**Ý nghĩa ứng dụng về mặt Thực tiễn**|
|- Thử nghiệm và chứng minh tính hiệu quả của các kiến trúc học sâu rút gọn, tối ưu hóa suy luận trực tiếp trên CPU thiết bị biên.<br><br>  <br><br>  <br><br>- Nghiên cứu thành công giải pháp kết hợp bộ lọc EMA và Hysteresis giúp giải quyết triệt để bài toán nhấp nháy trạng thái (state flickering) tín hiệu thời gian thực.<br><br>  <br><br>  <br><br>- Ứng dụng các giao thức mã hóa mật mã hiện đại bảo mật an toàn vector nhúng ($128\text{ chiều}$), ngăn ngừa tuyệt đối nguy cơ đảo ngược dữ liệu tái tạo khuôn mặt gốc.|- **Rút ngắn quy trình hành chính:** Rút ngắn thời gian điểm danh lớp học từ $10 - 15\text{ phút}$ xuống còn vài giây cho mỗi sinh viên.<br><br>  <br><br>  <br><br>- **Minh bạch hóa quản lý trường học:** Ngăn chặn triệt để tình trạng điểm danh hộ, xây dựng dữ liệu điểm danh trung thực, công bằng, nâng cao tự giác học tập.<br><br>  <br><br>  <br><br>- **An toàn dữ liệu tuyệt đối:** Toàn bộ thông tin sinh trắc học của sinh viên được lưu trữ cục bộ, không chia sẻ lên mạng internet, tránh rủi ro rò rỉ dữ liệu cá nhân.|

## 1.5. CÁC NGHIÊN CỨU LIÊN QUAN

### 1.5.1. Các nghiên cứu liên quan đến nhận dạng khuôn mặt (Face Recognition)

Sự phát triển của công nghệ nhận dạng khuôn mặt gắn liền với các cải tiến về hàm mất mát sinh trắc học nhằm kéo dãn khoảng cách giữa các cá thể khác nhau trong không gian vector nhúng:

**Bảng 1.7: Đối chiếu các mô hình nhận dạng khuôn mặt nổi tiếng**

|   |   |   |
|---|---|---|
|**Mô hình & Hàm mất mát**|**Độ chính xác (LFW)**|**Đặc điểm kiến trúc & Khả năng triển khai thực tế trên CPU biên**|
|**FaceNet**<br><br>  <br><br>_(Triplet Loss)_|$99.63\%$|- Ánh xạ ảnh trực tiếp sang không gian Euclid đa chiều.<br><br>  <br><br>- Quá trình huấn luyện đòi hỏi kỹ thuật lọc bộ ba phức tạp.<br><br>  <br><br>- Kích thước mô hình tương đối lớn, tốc độ suy luận chậm trên CPU biên.|
|**ArcFace**<br><br>  <br><br>_(Additive Angular Margin)_|$99.83\%$|- Tích hợp biên góc trực tiếp vào hàm Softmax để tối ưu hóa khoảng cách lớp.<br><br>  <br><br>- Đạt độ chính xác tối ưu nhưng mô hình cồng kềnh, yêu cầu GPU chuyên dụng.|
|**SFace**<br><br>  <br><br>_(Additive Margin + Cosine)_|$99.60\%$|- Tối ưu hóa sâu cấu trúc nhân chập thu gọn kháng nhiễu cực tốt.<br><br>  <br><br>- **Cực kỳ phù hợp cho CPU** ($\approx 10\text{ ms/khung hình}$), tích hợp sẵn trong OpenCV.|

### 1.5.2. Các nghiên cứu liên quan đến phát hiện giả mạo khuôn mặt (Face Anti-Spoofing)

Các nghiên cứu hiện đại tập trung vào phương pháp chống giả mạo thụ động (Passive FAS) nhằm đem lại trải nghiệm rảnh tay cho người dùng. Dưới đây là bảng đánh giá hiệu năng của các kiến trúc chống giả mạo phổ biến dựa trên bộ dữ liệu quốc tế tiêu chuẩn **OULU-NPU (Protocol 1)**:

**Bảng 1.8: So sánh hiệu năng các kiến trúc chống giả mạo khuôn mặt (FAS)**

|   |   |   |   |
|---|---|---|---|
|**Mô hình chống giả mạo**|**Chỉ số sai số phân loại(APCER / BPCER / ACER)**|**Tài nguyên phần cứng(Dung lượng / Tốc độ CPU)**|**Đánh giá khả năng tương thích phần cứng biên**|
|**CDCN**<br><br>  <br><br>_(Yu et al., 2020)_|- APCER: $1.20\%$  <br><br>  <br><br>- BPCER: $1.70\%$  <br><br>  <br><br>- **ACER:** $1.45\%$|- Dung lượng: $\approx 85.2\text{ MB}$  <br><br>  <br><br>- Tốc độ CPU: $\approx 120\text{ ms}$|Sử dụng mạng tích chập vi phân trung tâm. Độ chính xác cực cao nhưng quá nặng, không thể thực thi thời gian thực trên CPU.|
|**MobileNetV3-FAS**<br><br>  <br><br>_(Baseline)_|- APCER: $4.50\%$  <br><br>  <br><br>- BPCER: $5.20\%$  <br><br>  <br><br>- **ACER:** $4.85\%$|- Dung lượng: $\approx 15.2\text{ MB}$  <br><br>  <br><br>- Tốc độ CPU: $\approx 15\text{ ms}$|Dựa trên MobileNetV3 chuẩn. Tốc độ xử lý nhanh nhưng độ chính xác ở mức trung bình, dễ bị vượt qua bởi ảnh in chất lượng cao.|
|**MiniFASNetV1**<br><br>  <br><br>_(Minivision, 2021)_|- APCER: $2.10\%$  <br><br>  <br><br>- BPCER: $2.50\%$  <br><br>  <br><br>- **ACER:** $2.30\%$|- Dung lượng: $\approx 4.1\text{ MB}$  <br><br>  <br><br>- Tốc độ CPU: $\approx 8\text{ ms}$|Tối ưu hóa sâu bằng các khối Depth-wise Convolution siêu nhẹ. Nhận diện rất nhạy đối với các dạng tấn công ảnh in phẳng (Print Attack).|
|**MiniFASNetV2**<br><br>  <br><br>_(Minivision, 2021)_|- APCER: $1.50\%$  <br><br>  <br><br>- BPCER: $1.80\%$  <br><br>  <br><br>- **ACER:** $1.65\%$|- Dung lượng: $\approx 4.5\text{ MB}$  <br><br>  <br><br>- Tốc độ CPU: $\approx 10\text{ ms}$|Cải tiến bằng cách bổ sung kênh phân tích tần số cấu trúc da mặt. Đạt tỷ lệ ACER tiệm cận CDCN nhưng nhanh hơn gấp 12 lần trên CPU.|

Dựa trên bảng phân tích thực nghiệm học thuật trên, dòng mô hình **MiniFASNet** (đặc biệt là MiniFASNetV2) thể hiện sự vượt trội hoàn toàn về mặt tối ưu hóa tài nguyên phần cứng, biến nó thành lựa chọn tối ưu cho hệ thống điểm danh offline thời gian thực chạy trực tiếp trên CPU.

## 1.6. MÔ TẢ BÀI TOÁN VÀ LUỒNG HOẠT ĐỘNG TỔNG QUAN

Hệ thống điểm danh tự động hoạt động dựa trên các thông tin đầu vào và đầu ra chính sau:

- **Đầu vào (Input):** Luồng hình ảnh/video trực tiếp (Real-time Video Stream) từ camera RGB trong phòng học.
    
- **Đầu ra (Output):** Trạng thái ghi nhận lịch sử điểm danh vào SQLite cục bộ; hiển thị thông tin phản hồi trực quan (Tên, Mã số sinh viên, Trạng thái) hoặc phát tín hiệu cảnh báo tức thời trên giao diện nếu phát hiện giả mạo (SPOOF).
    

Hệ thống được thiết kế chia thành hai phân hệ hoạt động độc lập nhưng bổ trợ chặt chẽ cho nhau:

### 1.6.1. Quy trình của phân hệ đăng ký thông tin sinh viên (Enrollment Pipeline)

Quy trình đăng ký dữ liệu sinh học ban đầu của sinh viên được đặc tả chi tiết thông qua các bước xử lý khép kín trong bảng dưới đây:

**Bảng 1.9: Quy trình các bước xử lý của phân hệ Đăng ký thông tin (Enrollment)**

|   |   |   |
|---|---|---|
|**Bước & Hoạt động**|**Giải pháp công nghệ áp dụng**|**Chi tiết xử lý và Kết quả đầu ra (Outputs)**|
|**Bước 1: Phát hiện khuôn mặt**|Mô hình **YuNet**|- Phân tích luồng ảnh từ camera, xác định vị trí và tìm ra 5 điểm mốc khuôn mặt.<br><br>  <br><br>- **Đầu ra:** Khung bao (Bounding Box) và tọa độ các điểm mốc chính xác.|
|**Bước 2: Thử thách tư thế**|Thuật toán **Head Pose Estimation**|- Đo lường các góc xoay đầu thực tế của sinh viên dựa trên điểm mốc khuôn mặt. Hướng dẫn sinh viên hoàn thành lần lượt 5 tư thế: Nhìn thẳng, Xoay trái, Xoay phải, Ngửa mặt, Cúi mặt.<br><br>  <br><br>- **Đầu ra:** Xác nhận góc nghiêng đầu đạt chuẩn chụp mẫu.|
|**Bước 3: Trích xuất đặc trưng**|Mô hình **SFace**|- Khi các tư thế đổi góc đạt yêu cầu, camera tự động chụp và chuyển ảnh khuôn mặt thành vector đặc trưng số thực.<br><br>  <br><br>- **Đầu ra:** Bộ 5 vector nhúng khuôn mặt ($128\text{ chiều}$ cho mỗi góc).|
|**Bước 4: Lưu trữ bảo mật**|Thư viện **Cryptography / SQLite**|- Mã hóa an toàn các dữ liệu nhạy cảm và lưu trữ trực tiếp vào tệp tin cơ sở dữ liệu SQLite3 cục bộ.<br><br>  <br><br>- **Đầu ra:** Bản ghi thông tin sinh viên đã đăng ký hoàn chỉnh.|

> **Cơ chế chống giả mạo chủ động:** Thử thách đổi tư thế (Multi-pose Challenge) đóng vai trò là một lá chắn chủ động hiệu quả, ngăn chặn việc đăng ký thông tin giả mạo ngay từ khâu đầu vào vì ảnh in hay video phẳng không thể mô phỏng đúng sự thay đổi góc Euler trong không gian 3D.

### 1.6.2. Quy trình của phân hệ điểm danh tự động (Attendance Pipeline)

Trong các buổi học, hệ thống liên tục phân tích luồng video camera để nhận diện sinh viên thông qua đường ống AI khép kín dưới đây:

**Bảng 1.10: Quy trình xử lý tuần tự của phân hệ Điểm danh tự động (Attendance)**

|   |   |   |
|---|---|---|
|**Bước & Tác vụ AI**|**Logic xử lý chi tiết trong mã nguồn**|**Phản hồi giao diện & Điều phối dữ liệu**|
|**Bước 1: Face Detection**<br><br>  <br><br>(Mô hình YuNet)|Quét liên tục từng khung hình từ camera đầu vào để định vị khuôn mặt đang xuất hiện.|- Nếu không có mặt: Bỏ qua khung hình.<br><br>  <br><br>- Nếu phát hiện mặt: Cắt vùng ảnh khuôn mặt và chuyển sang Bước 2.|
|**Bước 2: Liveness Detection**<br><br>  <br><br>(Mô hình MiniFASNet)|Phân tích kết cấu da, phản xạ ánh sáng vùng mặt để xác định điểm số thực thể sống.|- **Nếu là giả mạo (SPOOF):** Lập tức cảnh báo viền đỏ trên giao diện, dừng xử lý khung hình đó.<br><br>  <br><br>- **Nếu là người thật (REAL):** Áp dụng bộ lọc mịn thời gian EMA và Hysteresis để giữ trạng thái REAL ổn định trước khi chuyển sang Bước 3.|
|**Bước 3: Feature Extraction**<br><br>  <br><br>(Mô hình SFace)|Trích xuất và chuyển đổi vùng mặt thật thành vector đặc trưng 128 chiều biểu diễn toán học.|Chuyển tiếp vector đặc trưng vừa tính toán sang mô-đun so khớp cơ sở dữ liệu.|
|**Bước 4: Face Matching**<br><br>  <br><br>(Thuật toán so khớp)|Tính toán độ tương đồng Cosine ($Cosine\ Similarity$) giữa vector hiện tại với tập mẫu đã đăng ký trong SQLite3.|- **Nếu độ tương đồng** $> 0.6$**:** Kết luận danh tính sinh viên, ghi nhận điểm danh vào SQLite3 và hiển thị viền xanh lá chúc mừng.<br><br>  <br><br>- **Nếu độ tương đồng** $\le 0.6$**:** Đánh dấu trạng thái không xác định (Unknown).|

## 1.7. BỐ CỤC CỦA ĐỒ ÁN TỐT NGHIỆP

Nội dung đồ án tốt nghiệp được cấu trúc chặt chẽ thành 5 chương chính nhằm phản ánh toàn diện các khía cạnh nghiên cứu lý thuyết và triển khai phần mềm:

**Bảng 1.11: Tóm tắt cấu trúc nội dung các chương trong đồ án tốt nghiệp**

|   |   |
|---|---|
|**Chương nghiên cứu**|**Nội dung nghiên cứu cốt lõi**|
|**Chương 1: Giới thiệu đề tài**|Trình bày lý do chọn đề tài, mục tiêu nghiên cứu, đối tượng, phạm vi nghiên cứu, ý nghĩa khoa học, thực tiễn và luồng hoạt động tổng quan của hệ thống.|
|**Chương 2: Cơ sở lý thuyết**|Nghiên cứu chi tiết cơ sở toán học và kiến trúc của các mô hình học sâu rút gọn được sử dụng bao gồm YuNet, SFace, MiniFASNet cùng các phép đo khoảng cách sinh trắc học.|
|**Chương 3: Thiết kế và Triển khai hệ thống**|Chi tiết hóa kiến trúc phần mềm, sơ đồ thực thể cơ sở dữ liệu SQLite3, thiết kế đường ống xử lý AI Pipeline, cơ chế đa luồng tránh treo giao diện (PyQt5 Threads) và giải pháp mã hóa dữ liệu.|
|**Chương 4: Kết quả thực nghiệm và Thảo luận**|Trình bày các kịch bản kiểm thử, phân tích kết quả định lượng về tốc độ suy luận (FPS) và các sai số sinh trắc học chuẩn hóa (FAR, FRR, ACER) trong môi trường lớp học thực tế.|
|**Chương 5: Kết luận và Hướng phát triển**|Tổng kết các kết quả đạt được của đồ án, đánh giá ưu điểm, chỉ ra những mặt hạn chế còn tồn tại và đề xuất các giải pháp nâng cấp, cải tiến trong tương lai.|