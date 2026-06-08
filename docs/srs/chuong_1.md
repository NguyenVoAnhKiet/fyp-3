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
4. **Đánh giá hiệu năng:** Đánh giá định lượng hiệu năng của hệ thống bao gồm tốc độ suy luận (độ trễ xử lý) và độ chính xác của hệ thống thông qua các chỉ số sinh trắc học chuẩn hóa: tỷ lệ chấp nhận/từ chối sai (FAR, FRR) cho phần nhận diện và tỷ lệ lỗi phân loại giả mạo (APCER, BPCER, ACER) cho phần chống giả mạo, kiểm thử thực tế độ ổn định trong môi trường lớp học.

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

## 1.6. Mô tả bài toán và Luồng hoạt động tổng quan

Để người đọc dễ dàng tiếp cận dự án một cách nhanh chóng nhất, phần này sẽ mô tả bài toán và luồng hoạt động cốt lõi của hệ thống bằng ngôn ngữ tự nhiên, lược bỏ các công thức toán học và chi tiết kỹ thuật phức tạp (các chi tiết này sẽ được trình bày sâu hơn ở Chương 2 và Chương 3).

Về cơ bản, hệ thống điểm danh tự động hoạt động dựa trên các thông tin đầu vào và đầu ra như sau:
*   **Đầu vào (Input):** Luồng hình ảnh/video trực tiếp thu nhận từ camera giám sát trong môi trường lớp học (sử dụng các thiết bị ghi hình thông thường như RGB Webcam).
*   **Đầu ra (Output):** 
    *   Trạng thái điểm danh thành công của từng sinh viên được tự động ghi nhận vào cơ sở dữ liệu.
    *   Phản hồi trực quan trên giao diện màn hình cho người quản lý (bao gồm Tên, Mã số sinh viên, Ảnh đại diện và Trạng thái xác thực).
    *   Cảnh báo tức thời nếu phát hiện hành vi gian lận (giả mạo khuôn mặt).

Hệ thống được thiết kế với hai luồng hoạt động độc lập nhưng bổ trợ chặt chẽ cho nhau:

### 1.6.1. Luồng Đăng ký thông tin (Enrollment Pipeline)

Trước khi hệ thống có thể tiến hành nhận diện điểm danh, dữ liệu sinh học khuôn mặt của sinh viên cần phải được đăng ký trước vào cơ sở dữ liệu mẫu. Quy trình đăng ký được thực hiện qua các bước:

1.  **Phát hiện khuôn mặt:** Camera thu nhận hình ảnh sinh viên, hệ thống tự động xác định vị trí và tìm ra các điểm mốc chính trên khuôn mặt (mắt, mũi, miệng).
2.  **Thử thách đổi tư thế (Multi-pose Challenge):** Phần mềm sẽ hướng dẫn sinh viên thực hiện lần lượt 5 tư thế xoay đầu nhẹ: nhìn thẳng (chính diện), quay trái, quay phải, ngửa đầu lên và cúi đầu xuống.
3.  **Trích xuất và lưu trữ mẫu (Face Embedding):** Khi sinh viên thực hiện đúng góc độ yêu cầu ở mỗi tư thế, hệ thống sẽ tự động chụp lại và chuyển đổi hình ảnh khuôn mặt thành một dãy số đặc trưng (gọi là vector đặc trưng hay "chữ ký số" sinh trắc học của khuôn mặt). Cả 5 chữ ký số ứng với 5 tư thế này sẽ được lưu trữ trực tiếp vào cơ sở dữ liệu.

> **Giải pháp chống giả mạo chủ động:** Việc bắt buộc sinh viên phải xoay đầu theo nhiều hướng khác nhau trong quá trình đăng ký là một giải pháp bảo vệ chủ động. Một bức ảnh in tĩnh hay màn hình điện thoại phẳng sẽ không bao giờ hoàn thành được chuỗi tư thế động này, giúp ngăn ngừa triệt để tình trạng đăng ký thông tin giả mạo ngay từ đầu.

### 1.6.2. Luồng Điểm danh tự động (Attendance Pipeline)

Trong các buổi học, hệ thống sẽ liên tục phân tích luồng video từ camera để điểm danh tự động cho sinh viên. Mỗi khuôn mặt xuất hiện trước camera sẽ được xử lý qua 3 bước:

1.  **Định vị khuôn mặt:** Xác định xem có khuôn mặt nào đang xuất hiện trong tầm quét của camera hay không.
2.  **Kiểm tra chống giả mạo (Liveness Detection):** Đây là chốt chặn quan trọng nhất của hệ thống. Phần mềm phân tích kết cấu da, phản xạ ánh sáng và độ sâu 3D trên khuôn mặt để phân biệt giữa người thật đang đứng trước camera (Real) với các hình thức giả mạo như ảnh in hoặc video phát lại trên điện thoại (Spoof).
    *   *Làm mịn tín hiệu thời gian thực:* Để tránh tình trạng hệ thống đưa ra quyết định sai lệch khi camera bị rung hoặc ánh sáng phòng học thay đổi đột ngột, điểm số chống giả mạo được tính trung bình mịn qua nhiều khung hình liên tiếp. Chỉ khi hệ thống xác nhận chắc chắn khuôn mặt đó là của người thật (REAL), quá trình nhận dạng mới được phép tiếp tục.
3.  **Nhận dạng danh tính (Face Identification):** Hệ thống tiến hành trích xuất "chữ ký số" của khuôn mặt thật hiện tại, sau đó so khớp nó với toàn bộ cơ sở dữ liệu chữ ký số của các sinh viên đã đăng ký trước đó.
    *   Nếu tìm thấy một sinh viên có chữ ký khớp nhất và độ tương đồng vượt qua ngưỡng an toàn quy định, hệ thống sẽ kết luận sinh viên đó là ai, tự động ghi nhận điểm danh thành công và hiển thị thông tin lên màn hình.
    *   Nếu không tìm thấy ai trùng khớp (độ tương đồng dưới ngưỡng an toàn), hệ thống sẽ trả về kết quả là khuôn mặt không xác định (Unknown).

---
*Lưu ý: Toàn bộ mô tả chi tiết về các thuật toán phát hiện khuôn mặt (YuNet), lọc thực thể sống (MiniFASNet), nhận dạng đặc trưng (SFace) cùng với các công thức chứng minh toán học và phép so khớp hình học sẽ được trình bày đầy đủ tại Chương 2 (Cơ sở lý thuyết).*
