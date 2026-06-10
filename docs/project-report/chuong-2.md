# Chương 2. CƠ SỞ LÝ THUYẾT

## 2.1. Tổng quan về bài toán nhận diện khuôn mặt

### 2.1.1. Bài toán phát hiện khuôn mặt (Face Detection)

Phát hiện khuôn mặt (Face Detection) là bước đầu tiên và quan trọng nhất trong bất kỳ hệ thống nhận dạng khuôn mặt nào. Mục tiêu của bài toán này là quét toàn bộ bức ảnh đầu vào, xác định xem có khuôn mặt người xuất hiện hay không, và nếu có thì trả về vị trí của khuôn mặt đó dưới dạng một khung giới hạn (Bounding Box). Tọa độ của khung giới hạn này sẽ được dùng để cắt riêng vùng khuôn mặt ra khỏi khung cảnh xung quanh.

Trong hệ thống của đồ án, mô hình **YuNet** được lựa chọn để giải quyết bài toán này. YuNet là một mạng nơ-ron tích chập (CNN) được thiết kế đặc biệt theo tiêu chí siêu nhẹ (lightweight). Các ưu điểm nổi bật của YuNet bao gồm:

- **Tốc độ xử lý cao:** YuNet có khả năng phát hiện khuôn mặt theo thời gian thực (real-time) ngay cả khi chỉ chạy trên phần cứng máy tính thông thường (CPU) mà không cần đến sự hỗ trợ của Card đồ họa (GPU).
- **Độ chính xác:** So với các phương pháp truyền thống như Haar-Cascade hay HOG, YuNet có độ chính xác cao hơn rất nhiều, đặc biệt là trong các điều kiện ánh sáng yếu hoặc khuôn mặt bị che khuất một phần.
- **Tích hợp Landmark:** Ngoài việc xác định Bounding Box, YuNet còn dự đoán được các điểm mốc (landmarks) quan trọng trên khuôn mặt (ví dụ: mắt, mũi, khóe miệng). Các điểm mốc này đóng vai trò rất lớn trong việc căn chỉnh khuôn mặt thẳng lại trước khi đưa vào bước nhận diện tiếp theo.

### 2.1.2. Bài toán nhận diện khuôn mặt (Face Recognition)

Sau khi khuôn mặt đã được phát hiện và cắt ra, hệ thống cần xác định danh tính của người đó. Bài toán này bao gồm hai quy trình chính: Rút trích đặc trưng (Feature Extraction) và So khớp khoảng cách.

**Quá trình rút trích đặc trưng (Feature Extraction)**
Bức ảnh khuôn mặt (sau khi đã căn chỉnh bằng các điểm landmarks) sẽ được đưa qua một mô hình học sâu. Mô hình này không trả về trực tiếp tên người, mà thay vào đó sẽ trích xuất ra một tập hợp các con số được gọi là vector đặc trưng (Embedding vector). Đây có thể xem như một "chữ ký số" sinh trắc học đại diện cho những nét độc bản của khuôn mặt người đó. Các góc chụp khác nhau của cùng một người sẽ cho ra các vector rất gần nhau trong không gian nhiều chiều.

Trong dự án này, mô hình **SFace** được sử dụng làm lõi rút trích đặc trưng. SFace là thuật toán nhận diện được thiết kế để cân bằng tối ưu giữa độ chính xác nhận diện và chi phí tính toán, rất phù hợp để nhúng vào các ứng dụng Desktop offline.

**Độ đo khoảng cách Cosine (Cosine Similarity)**
Để quyết định xem khuôn mặt thu được từ camera (live embedding) và khuôn mặt đã lưu trữ trong cơ sở dữ liệu (stored embedding) có phải là của cùng một người hay không, hệ thống tiến hành tính toán mức độ giống nhau giữa hai vector đặc trưng.

Phương pháp phổ biến và hiệu quả nhất cho bài toán này là Độ tương đồng Cosine (Cosine Similarity). Khác với việc tính khoảng cách hình học thông thường (Khoảng cách Euclidean), Cosine Similarity đo lường góc giữa hai vector. 

Công thức tính độ tương đồng Cosine giữa vector A và vector B được định nghĩa là:

Cosine(A, B) = (A . B) / (|A| * |B|)

Trong đó:
- (A . B) là tích vô hướng của hai vector A và B.
- |A| và |B| là độ dài (chuẩn) của vector A và B.

Kết quả của phép tính này sẽ nằm trong khoảng từ -1 đến 1. Nếu hai vector hoàn toàn giống nhau (góc giữa chúng là 0), độ tương đồng Cosine sẽ bằng 1. Dựa trên kết quả này, hệ thống áp dụng một ngưỡng (threshold) nhất định (ví dụ ngưỡng 0.6). Nếu kết quả đo lường lớn hơn 0.6, hệ thống xác nhận đó là cùng một người; ngược lại, hệ thống từ chối quyền truy cập do không đủ độ tin cậy.

## 2.2. Bài toán chống giả mạo khuôn mặt (Face Anti-Spoofing)

### 2.2.1. Khái niệm và phân loại

Trong các hệ thống nhận diện khuôn mặt truyền thống, một lỗ hổng bảo mật lớn thường xuyên gặp phải là các cuộc tấn công đánh lừa (Spoofing attacks). Kẻ gian có thể sử dụng ảnh in trên giấy, video phát lại trên điện thoại hoặc thậm chí là mặt nạ 3D để vượt qua bước nhận diện. Do đó, bài toán chống giả mạo khuôn mặt (Face Anti-Spoofing hay Liveness Detection) ra đời để đảm bảo khuôn mặt đang đứng trước camera là khuôn mặt thực thể sống, chứ không phải là một vật liệu giả mạo.

Có hai phương pháp tiếp cận chính cho bài toán này:
- Liveness 3D: Sử dụng các cảm biến phần cứng chuyên dụng như camera hồng ngoại (IR) hoặc cảm biến chiều sâu (Depth Sensor) để đo đạc độ lồi lõm thực tế của khuôn mặt. Phương pháp này có độ chính xác gần như tuyệt đối nhưng lại đòi hỏi chi phí phần cứng cao.
- Liveness 2D: Chỉ sử dụng dữ liệu từ camera RGB thông thường để phân tích kết cấu (texture) của bức ảnh. Thuật toán sẽ tìm kiếm các dấu hiệu bất thường như vết lóa sáng từ màn hình điện thoại, viền màn hình, hoặc chất lượng in ấn kém trên ảnh giấy. Hệ thống trong đồ án lựa chọn Liveness 2D để đảm bảo tính phổ thông, cho phép triển khai ứng dụng trên hầu hết các máy tính thông thường được trang bị webcam cơ bản.

### 2.2.2. Mô hình MiniFASNet V2 SE và kỹ thuật Lượng tử hóa

Để xử lý bài toán Liveness 2D, đồ án sử dụng kiến trúc mô hình MiniFASNet V2 SE. Đây là một mạng nơ-ron tích chập được tinh chỉnh đặc biệt để phân tích kết cấu chi tiết nhằm phát hiện dấu hiệu giả mạo mà không đòi hỏi tài nguyên hệ thống quá lớn.

Tuy nhiên, các mô hình học sâu mặc định thường sử dụng kiểu dữ liệu số thực có độ chính xác động (Floating Point 32-bit hay FP32) để lưu trữ trọng số (weights). Điều này làm tăng kích thước mô hình và làm chậm quá trình tính toán trên CPU. Để giải quyết vấn đề này, một kỹ thuật gọi là Lượng tử hóa (Quantization) được áp dụng.

Lượng tử hóa là quá trình chuyển đổi các trọng số của mạng nơ-ron từ định dạng FP32 sang các định dạng có độ chính xác thấp hơn, ví dụ như số nguyên 8-bit (INT8). Việc áp dụng mô hình MiniFASNet V2 SE đã qua lượng tử hóa (quantized model) mang lại hai lợi ích vô cùng quan trọng:
- Giảm thiểu dung lượng lưu trữ của mô hình, giúp ứng dụng nhẹ hơn.
- Tăng tốc độ tính toán (Inference speed) đáng kể khi chạy trên kiến trúc tập lệnh của CPU mà chỉ làm giảm một phần vô cùng nhỏ độ chính xác của mô hình.

### 2.2.3. Các kỹ thuật ổn định kết quả (Temporal Smoothing)

Trong điều kiện ánh sáng thực tế, kết quả phân tích Liveness từ mô hình ở từng khung hình (frame) riêng lẻ có thể bị dao động do hiện tượng nhiễu ảnh, gây ra hiện tượng lật trạng thái liên tục giữa Thật (Real) và Giả (Spoof). Để giải quyết vấn đề này, hệ thống áp dụng kỹ thuật làm mượt theo thời gian (Temporal Smoothing) bằng Toán học nhằm tạo ra một "bộ lọc triệt tiêu nhiễu".

**Trung bình động hàm mũ (Exponential Moving Average - EMA)**
EMA hoạt động như một "bộ giảm xóc". Thay vì chỉ lấy điểm số ở đúng khung hình hiện tại, EMA sẽ tính trung bình có trọng số của các khung hình trong quá khứ. Nhờ vậy, nếu camera đột nhiên bị lóa sáng trong 1 giây khiến mô hình bị nhầm lẫn, lịch sử ổn định trước đó sẽ "kéo" điểm số lại để hệ thống không bị báo động sai.

Minh họa sự hiệu quả của EMA:
```text
Trường hợp KHÔNG CÓ EMA:
Khung 1: Thật (0.9) -> Khung 2: Thật (0.8) -> Lóa sáng! Giả (0.1) => HỆ THỐNG BÁO ĐỘNG SAI!

Trường hợp CÓ ÁP DỤNG EMA:
Khung 1: Thật (0.9) -> Khung 2: Thật (0.8) -> Lóa sáng! Giả (0.1) => EMA dập tắt nhiễu, điểm kéo lại thành Thật (0.6) => HỆ THỐNG VẪN ỔN ĐỊNH.
```

Công thức tính EMA tại bước thời gian t là:
EMA(t) = a * S(t) + (1 - a) * EMA(t-1)
Trong đó: S(t) là điểm đánh giá thực tế ở khung hình hiện tại, a là hệ số làm mượt (0 < a < 1).

**Hệ số giao nhau (Intersection over Union - IoU)**
Để bộ lọc EMA hoạt động chính xác, hệ thống cần biết chắc chắn khuôn mặt ở khung hình hiện hành có đúng là khuôn mặt đang được theo dõi ở khung hình trước đó hay không (tránh cộng dồn điểm của hai người khác nhau đi ngang qua màn hình).

Hệ thống sử dụng công thức IoU để đo lường "tỷ lệ phần diện tích chồng lấp" giữa vị trí khuôn mặt cũ và mới:
IoU = Diện tích phần Giao (chồng lấp) / Tổng diện tích phần Hợp

Sơ đồ minh họa hệ số giao nhau (IoU):
```text
  +---------+
  | Khung 1 |
  |    +====|====+
  |    |GIAO|    | 
  +====|====+    |
       | Khung 2 |
       +---------+
```
*Ghi chú:*
- **Phần GIAO (Intersection):** Là diện tích phần hình chữ nhật nhỏ (nằm lồng bên trong) nơi hai khung đè lên nhau.
- **Phần HỢP (Union):** Là **tổng toàn bộ diện tích** của cả Khung 1 và Khung 2 gộp lại (sau khi đã trừ đi phần GIAO bị tính trùng). Nói cách khác, phần HỢP chính là toàn bộ không gian bị bao phủ bởi vùng viền ngoài cùng của cả hai khung hình.

Nếu chỉ số IoU vượt qua một ngưỡng quy định (tức là phần Giao chiếm tỷ lệ đủ lớn so với phần Hợp), hệ thống xác nhận đây vẫn là cùng một người đang di chuyển một chút, và tiếp tục quá trình duy trì bộ lọc EMA.

## 2.3. Công nghệ và công cụ phát triển

### 2.3.1. Ngôn ngữ Python và Framework PyQt5

Python hiện tại là ngôn ngữ thống trị trong lĩnh vực Trí tuệ nhân tạo (AI) và Xử lý ảnh (Computer Vision) nhờ vào hệ sinh thái thư viện khổng lồ và cộng đồng hỗ trợ mạnh mẽ. Việc sử dụng Python cho phép tích hợp liền mạch các mô hình học sâu phức tạp vào một ứng dụng hoàn chỉnh.

Để xây dựng giao diện người dùng (GUI) cho ứng dụng Desktop, đồ án lựa chọn framework PyQt5. Điểm cốt lõi khi xây dựng các ứng dụng tích hợp AI là bài toán Xử lý đa luồng (Multithreading). Nếu toàn bộ ứng dụng (bao gồm việc đọc khung hình từ camera, xử lý mô hình học sâu, và vẽ giao diện) đều chạy trên cùng một luồng duy nhất (Main Thread), ứng dụng sẽ gặp phải hiện tượng "đóng băng" (UI freeze) và giật lag nghiêm trọng mỗi khi CPU phải tập trung tính toán.

PyQt5 giải quyết vấn đề này thông qua cơ chế QThread. Bằng cách thiết lập cấu trúc đa luồng, toàn bộ các tác vụ nặng (như truy xuất camera và chạy mô hình ONNX) được đưa xuống các luồng chạy ngầm (Worker Threads). Luồng chính (Main Thread) chỉ chuyên tâm vào việc cập nhật hình ảnh hiển thị và phản hồi lại thao tác click chuột của người dùng, đảm bảo trải nghiệm ứng dụng luôn mượt mà.

Sơ đồ minh họa kiến trúc Đa luồng (Multithreading) trong PyQt5:
```text
[ Main Thread ] (Luồng giao diện chính)
       |
       |-- Vẽ nút bấm, thanh cuộn, cập nhật khung hình
       |-- KHÔNG chạy các tính toán nặng => Giao diện luôn mượt mà, không bị "đơ"
       |
  (Gửi khung hình gốc)
       |
       v
[ Worker Thread ] (Luồng xử lý ngầm)
       |
       |-- Phát hiện khuôn mặt (YuNet)
       |-- Chống giả mạo (Liveness)
       |-- Rút trích đặc trưng & Nhận diện (SFace)
       |
  (Trả kết quả: Tên người, Điểm liveness...)
       |
       v
[ Main Thread ] (Luồng giao diện chính)
       |-- Nhận kết quả và hiển thị chữ lên màn hình
```

### 2.3.2. Nền tảng thực thi ONNX Runtime

Để đưa một hệ thống AI vào hoạt động thực tế, quy trình phát triển trải qua hai bước chính. Có thể ví von quá trình này giống như việc "tạo và đọc một tài liệu điện tử":

1. **Giai đoạn Huấn luyện (Training):** Giống như việc bạn đang soạn thảo một tài liệu phức tạp bằng phần mềm chuyên nghiệp như Adobe InDesign hay Microsoft Word. Quá trình này đòi hỏi máy tính cấu hình cực mạnh (tương đương với các máy chủ dùng Card đồ họa GPU đắt tiền và các phần mềm lập trình AI nặng nề như PyTorch hay TensorFlow).
2. **Giai đoạn Thực thi (Inference):** Khi tài liệu đã soạn xong, bạn muốn phân phối cho người dùng cuối đọc. Rõ ràng, ta không thể bắt tất cả khách hàng phải cài phần mềm InDesign đắt tiền và nặng nề chỉ để xem nội dung. Tương tự, ta không thể bắt người dùng phổ thông tải thư viện PyTorch khổng lồ vào máy tính chỉ để chạy mô hình AI điểm danh.

**Giải pháp với ONNX và ONNX Runtime:**
Hệ thống trong đồ án sử dụng định dạng ONNX và nền tảng ONNX Runtime để giải quyết vấn đề trên:
- **Định dạng ONNX:** Đóng vai trò như **định dạng file PDF**. Dù mô hình AI ban đầu được tạo ra bằng bất kỳ công cụ phức tạp nào, nó đều có thể được xuất ra dưới dạng một file duy nhất, chuẩn hóa và gọn nhẹ là ONNX. Tính chất của nó y hệt như việc bạn xuất file Word/InDesign sang file PDF để ai cũng có thể mở được.
- **Lõi thực thi ONNX Runtime:** Đóng vai trò như một **phần mềm đọc PDF** siêu nhẹ (ví dụ: Foxit Reader). Đây là phần mềm chuyên dụng chỉ để "đọc" và chạy các file ONNX. Nó được tối ưu hóa cực kỳ tốt để xử lý mô hình AI trực tiếp trên vi xử lý thông thường (CPU) với tốc độ rất nhanh.

Sự kết hợp này giúp phần mềm điểm danh giải phóng hoàn toàn khỏi các môi trường lập trình AI cồng kềnh, có thể cài đặt dễ dàng và chạy mượt mà trên bất kỳ máy tính bàn hay laptop nào mà không cần đến Card đồ họa (GPU).

### 2.3.3. Cơ sở dữ liệu SQLite và cơ chế WAL (Write-Ahead Logging)

Để phục vụ cho mô hình hoạt động offline, toàn bộ dữ liệu người dùng, cấu hình và lịch sử điểm danh được lưu trữ cục bộ bằng hệ quản trị cơ sở dữ liệu SQLite. Sự gọn nhẹ, không cần cài đặt máy chủ (Serverless) và dữ liệu được đóng gói trong một file duy nhất khiến SQLite trở thành lựa chọn hoàn hảo cho các phần mềm Desktop.

Tuy nhiên, như đã phân tích ở tiểu mục 2.3.1, ứng dụng này hoạt động dựa trên cấu trúc đa luồng. Một nhược điểm kinh điển của SQLite khi chạy đa luồng là lỗi "Database is locked" (Bị khóa CSDL). Lỗi này xảy ra do mặc định SQLite sẽ khóa toàn bộ file dữ liệu mỗi khi có một luồng thực hiện thao tác Ghi (Write), làm cho các luồng Đọc (Read) khác bị chặn lại (Ví dụ: Luồng Camera đang ghi thông tin nhận diện vào CSDL, thì cùng lúc đó luồng Giao diện lại yêu cầu lấy dữ liệu để hiển thị lên bảng thống kê).

Để giải quyết triệt để rào cản này, hệ thống kích hoạt cơ chế WAL (Write-Ahead Logging) của SQLite. Thay vì ghi đè trực tiếp vào file CSDL chính, cơ chế WAL ghi các thay đổi vào một file nhật ký tạm thời (WAL file). Phương pháp này mang lại khả năng Đọc và Ghi đồng thời (Concurrency): các luồng giao diện UI hoàn toàn có thể đọc dữ liệu từ CSDL chính một cách độc lập ngay cả khi luồng AI đang bận rộn ghi nhận sự kiện điểm danh mới. Sự kết hợp giữa PyQt5 Đa luồng và SQLite WAL tạo nên một kiến trúc phần mềm cục bộ vô cùng vững chắc và đáng tin cậy.

Sơ đồ minh họa cơ chế hoạt động của SQLite WAL:
```text
[1] TRƯỚC KHI BẬT WAL (Dễ bị lỗi "Database is locked"):
Luồng Camera (Ghi) ---------(Khóa toàn bộ file)---------> [ File CSDL chính ]
                                                                |
Luồng Giao diện (Đọc) ----(Cố gắng lấy dữ liệu)------ X (BỊ CHẶN LẠI GÂY LỖI)

[2] SAU KHI BẬT WAL (Cho phép Đọc/Ghi đồng thời):
Luồng Camera (Ghi) ---------(Chỉ ghi vào file nhật ký)-> [ File tạm (.wal) ]
                                                                | (Đồng bộ ngầm)
                                                                v
Luồng Giao diện (Đọc) ----(Lấy dữ liệu thoải mái)--------> [ File CSDL chính ]
```
