# Chương 1. GIỚI THIỆU ĐỀ TÀI

## 1.1. Lý do chọn đề tài

_Trong bối cảnh cách mạng công nghiệp 4.0 và xu hướng chuyển đổi số mạnh mẽ, việc ứng dụng trí tuệ nhân tạo (AI) vào quản lý giáo dục đã trở thành giải pháp thiết yếu giúp tinh gọn bộ máy vận hành và tối ưu hóa thời gian. Một trong những nhiệm vụ hành chính quan trọng nhưng tốn nhiều thời gian nhất của giảng viên trong mỗi buổi học chính là hoạt động điểm danh sinh viên.

Hiện nay, phần lớn các cơ sở đào tạo vẫn áp dụng phương pháp điểm danh truyền thống như gọi tên trực tiếp hoặc ký danh sách. Các phương pháp này bộc lộ nhiều hạn chế rõ rệt: tốn thời gian (chiếm từ 10% đến 15% thời lượng tiết học), dễ sai sót và đặc biệt là không thể ngăn chặn triệt để tình trạng gian lận như điểm danh hộ. Một số đơn vị đã áp dụng các giải pháp công nghệ như thẻ từ (RFID) hoặc dấu vân tay. Tuy nhiên, việc quét vân tay gây lo ngại về vệ sinh dịch tễ khi nhiều người tiếp xúc chung một bề mặt cảm biến, trong khi thẻ từ lại dễ dàng được trao đổi để điểm danh hộ một cách đơn giản.

Sự phát triển vượt bậc của lĩnh vực Thị giác máy tính (Computer Vision) và Học sâu (Deep Learning) đã mở ra hướng đi mới thông qua công nghệ nhận diện khuôn mặt (Face Recognition). Nhận diện khuôn mặt cung cấp một giải pháp không tiếp xúc, tốc độ xử lý nhanh, tự động hóa hoàn toàn và có tính cá nhân hóa cao, ngăn chặn việc trao đổi "thông tin xác thực" như thẻ từ.

Tuy nhiên, các hệ thống nhận diện khuôn mặt thông thường rất dễ bị tấn công giả mạo (Presentation Attacks - PA) bằng cách sử dụng ảnh in chân dung 2D, hiển thị video trên màn hình điện thoại/máy tính bảng hoặc sử dụng mặt nạ. Nếu không có cơ chế tự vệ, hệ thống điểm danh sẽ mất đi tính chính xác và minh bạch vốn có. Do đó, việc kết hợp kỹ thuật phát hiện giả mạo khuôn mặt (Face Anti-Spoofing hay Liveness Detection) để phân biệt giữa thực thể sống (khuôn mặt thật) và các dạng biểu diễn giả mạo là điều kiện tiên quyết.

Xuất phát từ nhu cầu thực tiễn đó, đề tài **"Xây Dựng Hệ Thống Điểm Danh Sử Dụng Nhận Diện Khuôn Mặt Và Chống Giả Mạo"** được lựa chọn thực hiện nhằm nghiên cứu sâu các thuật toán thị giác máy tính hiện đại và phát triển một ứng dụng điểm danh ngoại tuyến có độ tin cậy cao, tốc độ đáp ứng thời gian thực và đảm bảo tính minh bạch tối đa.

## 1.2. Mục tiêu nghiên cứu

Mục tiêu chung của đề tài là xây dựng hoàn chỉnh một ứng dụng điểm danh tự động, hoạt động cục bộ (offline) có khả năng nhận diện danh tính sinh viên thông qua camera giám sát và ngăn chặn các hành vi điểm danh giả mạo bằng ảnh in hoặc video tái phát.

Cụ thể, đề tài hướng tới các mục tiêu thành phần sau:
1. **Nghiên cứu lý thuyết:** Tìm hiểu sâu về các phương pháp phát hiện khuôn mặt, trích xuất đặc trưng sinh trắc học và các mô hình phát hiện giả mạo khuôn mặt dựa trên mạng nơ-ron tích chập (CNN).
2. **Xây dựng đường ống xử lý (AI Pipeline):** Thiết kế luồng xử lý khép kín từ khâu nhận luồng video đầu vào, phát hiện khuôn mặt thời gian thực, lọc giả mạo và định danh sinh viên dựa trên cơ sở dữ liệu có sẵn.
3. **Phát triển ứng dụng hoàn chỉnh:** Xây dựng phần mềm desktop sử dụng ngôn ngữ Python, framework giao diện PyQt5, hệ quản trị cơ sở dữ liệu SQLite và tích hợp các mô hình AI định dạng ONNX chạy trực tiếp trên CPU.
4. **Đánh giá hiệu năng:** Thử nghiệm độ chính xác của hệ thống chống giả mạo, tốc độ nhận diện và độ ổn định của hệ thống trong môi trường lớp học thực tế.

## 1.3. Đối tượng và phạm vi nghiên cứu

*   **Đối tượng nghiên cứu:** 
    *   Các thuật toán và mô hình học sâu phục vụ phát hiện khuôn mặt (YuNet), nhận dạng khuôn mặt (SFace) và phát hiện giả mạo khuôn mặt (MiniFASNet).
    *   Các phương pháp đo lường khoảng cách toán học để so khớp đặc trưng (Cosine Similarity và Euclidean Distance).
    *   Các kỹ thuật xử lý tín hiệu theo thời gian (EMA, Hysteresis) để tăng tính ổn định của luồng nhận diện.
*   **Phạm vi nghiên cứu:**
    *   **Công nghệ:** Hệ thống hoạt động offline hoàn toàn, chạy trực tiếp trên thiết bị đầu cuối thông qua môi trường suy luận ONNX Runtime nhằm bảo vệ quyền riêng tư dữ liệu khuôn mặt và giảm chi phí hạ tầng.
    *   **Thiết bị:** Sử dụng webcam thông thường (RGB) làm cảm biến thu hình hình ảnh.
    *   **Quy mô triển khai:** Hệ thống được thiết kế phù hợp với môi trường lớp học (quy mô dưới 200 sinh viên đã đăng ký dữ liệu trước đó). Các nỗ lực chống giả mạo tập trung vào tấn công dạng phẳng (ảnh in 2D chất lượng cao và video phát lại qua màn hình kỹ thuật số).

## 1.4. Ý nghĩa khoa học và thực tiễn

*   **Ý nghĩa khoa học:** Đề tài ứng dụng và kiểm chứng hiệu quả của các kiến trúc mạng nơ-ron tích chập (CNN) hiện đại, gọn nhẹ trong việc giải quyết bài toán thị giác máy tính phức tạp trên thiết bị biên có tài nguyên hạn chế. Việc kết hợp kỹ thuật lọc nhiễu tín hiệu thời gian (EMA và Hysteresis) vào luồng suy luận của AI đóng góp một giải pháp thực tiễn để giải quyết bài toán nhấp nháy trạng thái (state flickering) trong hệ thống nhận diện thực tế.
*   **Ý nghĩa thực tiễn:** Mang lại giải pháp điểm danh thông minh, giảm thời gian điểm danh có thể lên đến 10 phút xuống còn vài giây cho mỗi sinh viên. Hệ thống giúp ngăn chặn gian lận điểm danh hộ, cung cấp nhật ký kiểm toán trực quan cho người quản lý, đồng thời nâng cao ý thức tự giác và tính kỷ luật của người học trong môi trường giáo dục số hóa.

## 1.5. Các nghiên cứu liên quan

Trong những năm gần đây, bài toán nhận dạng khuôn mặt đã đạt được bước nhảy vọt nhờ học sâu. Các nghiên cứu nổi bật tập trung vào cải tiến cấu trúc mạng và hàm mất mát để tăng cường khả năng phân tách đặc trưng giữa các cá thể khác nhau:

| Mô hình                              | Hàm mất mát (Loss Function)                      | Độ chính xác (LFW) | Đặc trưng kiến trúc và Phân tích kỹ thuật                                                                                                                              | Khả năng triển khai thực tế                                                                                                      |
| :----------------------------------- | :----------------------------------------------- | :----------------- | :--------------------------------------------------------------------------------------------------------------------------------------------------------------------- | :------------------------------------------------------------------------------------------------------------------------------- |
| **FaceNet** *(Schroff et al., 2015)* | Triplet Loss                                     | 99.63%             | Ánh xạ ảnh khuôn mặt trực tiếp sang không gian Euclid đa chiều. Quá trình huấn luyện đòi hỏi kỹ thuật lọc bộ ba (Triplet Selection) rất phức tạp để tránh hội tụ chậm. | Mô hình có kích thước tương đối lớn, tốc độ suy luận trung bình nếu chạy trên CPU không có GPU hỗ trợ.                           |
| **ArcFace** *(Deng et al., 2019)*    | Additive Angular Margin Loss                     | 99.83%             | Tích hợp thêm một lượng biên góc (angular margin) trực tiếp vào hàm mất mát Softmax để thu hẹp khoảng cách nội lớp và kéo giãn khoảng cách giữa các lớp trên mặt cầu.  | Đạt độ chính xác tối đa nhưng cấu trúc mô hình cồng kềnh, yêu cầu phần cứng mạnh (GPU chuyên dụng) để đạt tốc độ thời gian thực. |
| **SFace** *(Zhong et al., 2021)*     | Additive Angular Margin Loss + Cosine Similarity | 99.60%             | Được thiết kế tối ưu hóa cấu trúc để chạy trên các thiết bị biên. Mô hình trích xuất đặc trưng kháng nhiễu cực tốt mà vẫn giữ kích thước file nhỏ gọn.                 | **Cực kỳ phù hợp cho CPU** (~10ms/khung hình), được hỗ trợ sẵn trong mô-đun OpenCV DNN thông qua lớp `cv2.FaceRecognizerSF`.     |

Đối với bài toán phát hiện giả mạo khuôn mặt (Face Anti-Spoofing), các nghiên cứu ban đầu thường dựa trên chuyển động chủ động (Active Liveness) như yêu cầu người dùng nháy mắt, nghiêng đầu hoặc đọc chữ. Phương pháp này làm chậm trải nghiệm của người dùng. Xu hướng hiện đại chuyển sang phát hiện giả mạo thụ động (Passive Liveness) sử dụng mạng CNN phân tích các chi tiết kết cấu siêu nhỏ (micro-texture) như vân ảnh in, phản xạ ánh sáng màn hình và độ sâu 3D của khuôn mặt thật so với cấu trúc phẳng của ảnh/video giả mạo. Các mô hình như **MiniFASNet** ra đời giúp thực hiện tác vụ này với độ trễ cực thấp (dưới 50ms) trên các cấu hình máy tính văn phòng thông thường.

## 1.6. Đặc tả bài toán

Bài toán của đề tài được định nghĩa chính thức bằng ngôn ngữ toán học như sau:

Gọi $U = \{u_1, u_2, ..., u_N\}$ là tập hợp gồm $N$ sinh viên đã đăng ký thông tin trong hệ thống. Với mỗi sinh viên $u_i$, hệ thống lưu trữ một tập hợp các vector đặc trưng khuôn mặt mẫu đã đăng ký:
$$E_i = \{e_{i, 1}, e_{i, 2}, ..., e_{i, k}\} \subset \mathbb{R}^{128}$$
trong đó $e_{i, j}$ là vector đặc trưng 128 chiều biểu diễn khuôn mặt mẫu thứ $j$ của sinh viên $u_i$.

Gọi $I$ là khung hình ảnh đầu vào định dạng BGR thu nhận từ camera tại thời điểm $t$. Luồng xử lý của hệ thống được mô tả qua các hàm ánh xạ toán học sau:

### Bước 1: Phát hiện khuôn mặt (Face Detection)
Mô hình phát hiện khuôn mặt YuNet (ký hiệu là hàm $D$) nhận đầu vào là ảnh $I$ và trả về danh sách các khuôn mặt được phát hiện:
$$D(I) = \{ (B_m, L_m) \}_{m=1}^{M}$$
*   Trong đó $M$ là số khuôn mặt phát hiện được trong khung hình.
*   $B_m = (x_m, y_m, w_m, h_m) \in \mathbb{Z}^4$ là hộp giới hạn (Bounding Box) xác định tọa độ và kích thước khuôn mặt thứ $m$.
*   $L_m = \{(x_{m,p}, y_{m,p})\}_{p=1}^{5}$ là tập hợp tọa độ của 5 điểm mốc đặc trưng (mắt trái, mắt phải, mũi, khóe miệng trái, khóe miệng phải) phục vụ căn chỉnh ảnh.

### Bước 2: Kiểm tra chống giả mạo (Liveness Detection)
Với khuôn mặt chính diện lớn nhất phát hiện được, mô hình MiniFASNet (ký hiệu là hàm $F$) nhận ảnh cắt khuôn mặt $I_{crop}$ và trả về vector logit hai chiều đại diện cho độ tin cậy của thực thể sống:
$$F(I_{crop}) = [z_0, z_1] \in \mathbb{R}^2$$
*   Trong đó $z_0$ là điểm số (logit) của lớp khuôn mặt thật (Real Class).
*   $z_1$ là điểm số (logit) của lớp khuôn mặt giả mạo (Spoof Class).

Hiệu số logit đại diện cho độ lệch tin cậy được tính bằng công thức:
$$logit\_diff = z_0 - z_1$$
Với ngưỡng xác suất an toàn $p \in (0, 1)$ do quản trị viên thiết lập, hệ thống xác định ngưỡng logit biên:
$$logit\_threshold = \ln\left(\frac{p}{1-p}\right)$$
Trạng thái liveness tức thời của khuôn mặt tại khung hình được phân loại là:
$$\text{Liveness}(I_{crop}) = \begin{cases} \text{REAL} & \text{nếu } logit\_diff > logit\_threshold \\ \text{SPOOF} & \text{ngược lại} \end{cases}$$

### Bước 3: Nhận dạng danh tính (Face Identification)
Nếu trạng thái liveness (sau khi làm mịn theo thời gian) được xác nhận là $\text{REAL}$, hệ thống tiến hành cắt và căn chỉnh khuôn mặt dựa trên các điểm mốc $L_m$ để tạo ra ảnh căn chỉnh $I_{aligned}$. 

Mô hình SFace (ký hiệu là hàm $G$) tiến hành ánh xạ ảnh $I_{aligned}$ thành một vector đặc trưng sinh trắc học mới:
$$e_{live} = G(I_{aligned}) \in \mathbb{R}^{128}$$
với điều kiện vector đã được chuẩn hóa $\|e_{live}\|_2 = 1$.

Hệ thống so khớp vector đặc trưng $e_{live}$ với toàn bộ các vector mẫu lưu trữ trong cơ sở dữ liệu để tìm ra độ tương đồng lớn nhất:
$$Sim(e_{live}, E) = \max_{u_i \in U, e_{i,j} \in E_i} \text{CosineSimilarity}(e_{live}, e_{i,j})$$

Kết quả định danh cuối cùng của hệ thống được xác định bởi:
$$\text{Identity}(e_{live}) = \begin{cases} u_i & \text{nếu } Sim(e_{live}, E) \ge \theta_{sim} \\ \text{unknown} & \text{ngược lại} \end{cases}$$
*   Trong đó $\theta_{sim}$ là ngưỡng tương đồng tối thiểu được cấu hình trước (ví dụ: $0.6$). Nếu độ tương đồng cao nhất vượt qua ngưỡng này, hệ thống tự động ghi nhận điểm danh thành công cho sinh viên $u_i$. Ngược lại, hệ thống trả về kết quả chưa nhận diện được (`unknown`).
