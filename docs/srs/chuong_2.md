# Chương 2. CƠ SỞ LÝ THUYẾT

## 2.1. Tổng quan về thị giác máy tính

Thị giác máy tính (Computer Vision) là một phân ngành của Trí tuệ nhân tạo (AI) tập trung vào việc nghiên cứu phương pháp giúp máy tính có khả năng "nhìn" và hiểu được nội dung của thế giới số dưới dạng hình ảnh hoặc video tương tự như con người. Bản chất của ảnh kỹ thuật số khi đưa vào máy tính là các ma trận số biểu thị cường độ sáng của các điểm ảnh (pixel). Nhiệm vụ của thị giác máy tính là xây dựng các thuật toán trích xuất các đặc trưng ngữ nghĩa từ các ma trận số thô này.

Sự bứt phá của học sâu (Deep Learning) và các kiến trúc Mạng nơ-ron tích chập (Convolutional Neural Network - CNN) đã thay đổi hoàn toàn cách tiếp cận của thị giác máy tính. Thay vì phải thiết kế thủ công các bộ lọc đặc trưng vật lý (như cạnh, góc, vân bề mặt), mạng CNN có khả năng tự động học các biểu diễn đặc trưng phân cấp từ thấp đến cao (từ các đường nét cơ bản đến các hình khối phức tạp như mắt, mũi, miệng) trực tiếp từ tập dữ liệu huấn luyện lớn.

Trong phạm vi đề tài này, thị giác máy tính đóng vai trò nền tảng cốt lõi được chia nhỏ thành 3 tác vụ chính chạy nối tiếp nhau: phát hiện khuôn mặt trong ảnh, xác minh thực thể sống để chống giả mạo, và trích xuất vector đặc trưng sinh trắc học phục vụ nhận dạng danh tính.

## 2.2. Phát hiện khuôn mặt (Face Detection)

### 2.2.1. Khái niệm
Phát hiện khuôn mặt là bước tiền xử lý bắt buộc trong mọi hệ thống xử lý sinh trắc học khuôn mặt. Nhiệm vụ của tác vụ này là xác định xem trong ảnh đầu vào có sự tồn tại của khuôn mặt người hay không, và nếu có thì trả về vị trí của khuôn mặt đó dưới dạng một hộp giới hạn (Bounding Box) xác định bằng tọa độ điểm góc trên bên trái cùng chiều rộng và chiều cao.

### 2.2.2. Các phương pháp phổ biến và Lựa chọn YuNet
*   **Haar Cascade:** Giải pháp cổ điển sử dụng các đặc trưng dạng khối chữ nhật (Haar-like features) kết hợp thuật toán phân loại Boosting tuần tự. Tốc độ thực thi rất nhanh trên CPU nhưng độ chính xác rất kém trong điều kiện ánh sáng yếu, khuôn mặt bị nghiêng hoặc bị che khuất một phần.
*   **MTCNN (Multi-task Cascaded Convolutional Networks):** Gồm 3 mạng CNN nối tiếp nhau để lọc dần các hộp bao ứng viên và phát hiện điểm mốc khuôn mặt. Độ chính xác cao nhưng cấu trúc mạng phức tạp, tốc độ xử lý chậm khi chạy trên luồng video thời gian thực của thiết bị đầu cuối thông thường.
*   **Mô hình YuNet (Anchor-free Detector):** YuNet là mô hình phát hiện khuôn mặt hiện đại, siêu nhẹ (dung lượng chỉ khoảng vài trăm KB) được tích hợp chính thức trong thư viện OpenCV. 

#### Sự khác biệt về kiến trúc của YuNet (Anchor-free):
Các mô hình phát hiện truyền thống (Anchor-based) yêu cầu tạo trước hàng nghìn hộp neo (anchors) có nhiều kích thước cố định tại mọi vùng trên ảnh rồi tính toán trùng khớp để chọn ra hộp tốt nhất. Quá trình này đòi hỏi tài nguyên tính toán rất lớn. 

Ngược lại, YuNet loại bỏ hoàn toàn các hộp neo này (kiến trúc Anchor-free). Mô hình sử dụng mạng backbone nhẹ để trích xuất các bản đồ đặc trưng (feature maps) có độ phân giải khác nhau, sau đó dự đoán trực tiếp 3 thông số tại từng điểm pixel trên bản đồ đặc trưng:
1.  Khả năng chứa khuôn mặt (Classification score).
2.  Khoảng cách từ điểm đó tới 4 cạnh của hộp giới hạn (Bounding box regression).
3.  Tọa độ dịch chuyển tới 5 điểm mốc chính trên khuôn mặt (Landmarks regression).

Đầu ra của YuNet cho mỗi khuôn mặt phát hiện được là một vector $V \in \mathbb{R}^{15}$ gồm:
$$V = [x, y, w, h, x_{l\_eye}, y_{l\_eye}, x_{r\_eye}, y_{r\_eye}, x_{nose}, y_{nose}, x_{l\_mouth}, y_{l\_mouth}, x_{r\_mouth}, y_{r\_mouth}, score]$$
*   $(x, y)$ và $(w, h)$ xác định tọa độ đỉnh và kích thước hộp giới hạn.
*   5 cặp điểm mốc $(x_{p}, y_{p})$ tương ứng với mắt trái, mắt phải, đỉnh mũi, khóe miệng trái và khóe miệng phải.
*   $score$ là độ tin cậy phát hiện khuôn mặt trong khoảng $[0, 1]$.

Nhờ loại bỏ hộp neo và thiết kế mạng nơ-ron rút gọn tối đa, YuNet đạt tốc độ xử lý vượt trội (dưới 10ms trên CPU văn phòng bình thường), cung cấp tọa độ 5 điểm mốc cực kỳ chuẩn xác làm tiền đề cho bước căn chỉnh ảnh (Face Alignment) trước khi trích xuất vector nhận diện.

## 2.3. Phát hiện giả mạo khuôn mặt (Face Anti-Spoofing)

### 2.3.1. Khái niệm và Các hình thức tấn công
Phát hiện giả mạo khuôn mặt là cơ chế phòng thủ bảo vệ hệ thống nhận diện trước các Presentation Attacks (PA). Có ba hình thức tấn công phổ biến nhất:
*   **Print Attack:** Sử dụng ảnh chân dung in trên giấy phẳng.
*   **Replay Attack:** Phát lại video chân dung của sinh viên đã quay trước đó thông qua màn hình thiết bị kỹ thuật số.
*   **Mask Attack:** Sử dụng mặt nạ 3D (giấy, nhựa, silicon) mô phỏng khuôn mặt thật.

Hệ thống điểm danh này tập trung ngăn chặn Print Attack và Replay Attack vì đây là các hình thức dễ thực hiện nhất của sinh viên.

### 2.3.2. Mô hình MiniFASNet và Cơ chế Squeeze-and-Excitation
Dự án sử dụng mô hình **MiniFASNet V2 SE** – một kiến trúc mạng nơ-ron học sâu siêu nhẹ (dưới 1MB) chuyên biệt cho tác vụ phân loại liveness tức thời. 

#### Kiến trúc Squeeze-and-Excitation (SE) Block:
Trong mạng nơ-ron tích chập thông thường, mỗi kênh đặc trưng (feature channel) được đối xử có vai trò ngang nhau khi truyền qua các lớp. SE Block giúp cải tiến điều này bằng cách tự động gán trọng số ưu tiên cho các kênh chứa thông tin quan trọng. Cụ thể gồm hai bước chính:
1.  **Squeeze (Nén):** Nén thông tin không gian (chiều cao và chiều rộng) của ảnh đặc trưng thành một vector mô tả kênh bằng phép toán Global Average Pooling (Lấy trung bình toàn bộ điểm ảnh trên mỗi kênh).
2.  **Excitation (Kích hoạt):** Đưa vector nén qua các lớp liên kết đầy đủ để học mối quan hệ phi tuyến giữa các kênh, sinh ra các hệ số trọng số nằm trong khoảng $[0, 1]$ thông qua hàm kích hoạt Sigmoid. Trọng số này được nhân ngược lại với ảnh đặc trưng ban đầu.

Đối với bài toán chống giả mạo, SE block giúp mạng tập trung mạnh vào các kênh đặc trưng nhạy cảm với cấu trúc bề mặt vật lý (như sự biến dạng ánh sáng của màn hình LCD, các đường viền mép giấy ảnh in, hiện tượng moire nhiễu sọc tần số cao) giúp phân biệt rõ nét giữa ảnh phẳng 2D và khuôn mặt 3D thực tế của con người.

#### Công thức phân loại Liveness chuyển đổi Logit Space:
Mạng MiniFASNet xuất ra hai giá trị logit thô $z_0$ (đại diện cho nhãn Real - thật) và $z_1$ (đại diện cho nhãn Spoof - giả mạo) tại lớp cuối cùng trước khi đi qua hàm Softmax.

Xác suất để ảnh đầu vào là khuôn mặt thật được tính bằng hàm Softmax:
$$P(\text{real}) = \frac{e^{z_0}}{e^{z_0} + e^{z_1}}$$

Để đưa ra quyết định an toàn, quản trị viên cấu hình một ngưỡng xác suất tối thiểu $p \in (0, 1)$ (ví dụ: $p=0.3$, nghĩa là nếu xác suất thật lớn hơn 30% thì được coi là thật). Việc tính toán hàm số mũ $e^z$ trực tiếp trên CPU cho mỗi khung hình luồng camera là một phép toán tốn kém tài nguyên. Do đó, hệ thống thực hiện chuyển đổi toán học đưa ngưỡng xác suất về không gian logit (Logit Space):
$$P(\text{real}) > p \iff \frac{e^{z_0}}{e^{z_0} + e^{z_1}} > p$$
Chia cả tử và mẫu cho $e^{z_0}$:
$$\iff \frac{1}{1 + e^{-(z_0 - z_1)}} > p$$
$$\iff 1 + e^{-(z_0 - z_1)} < \frac{1}{p}$$
$$\iff e^{-(z_0 - z_1)} < \frac{1 - p}{p}$$
Lấy logarit tự nhiên ($\ln$) hai vế:
$$\iff -(z_0 - z_1) < \ln\left(\frac{1 - p}{p}\right)$$
Nhân hai vế với $-1$ (đảo chiều bất đẳng thức):
$$\iff z_0 - z_1 > \ln\left(\frac{p}{1 - p}\right)$$

Đặt:
$$logit\_diff = z_0 - z_1$$
$$logit\_threshold = \ln\left(\frac{p}{1 - p}\right)$$

*Giải thích công thức:* Ngưỡng biên logit $logit\_threshold$ được tính sẵn duy nhất một lần tại thời điểm khởi động phần mềm từ ngưỡng cấu hình $p$. Tại mỗi khung hình camera, hệ thống chỉ cần lấy phép trừ hiệu số logit thô $logit\_diff = z_0 - z_1$ rồi so sánh trực tiếp với $logit\_threshold$. Nếu $logit\_diff > logit\_threshold$, hệ thống kết luận khuôn mặt là thật. Phép biến đổi này giúp loại bỏ hoàn toàn các phép toán mũ phức tạp, tối ưu hóa tốc độ thực thi của CPU.

## 2.4. Nhận dạng khuôn mặt (Face Recognition)

### 2.4.1. Khái niệm và Quy trình trích xuất đặc trưng (Embedding)
Nhận dạng khuôn mặt là tác vụ so khớp một ảnh khuôn mặt chưa biết danh tính với cơ sở dữ liệu khuôn mặt mẫu để tìm ra người trùng khớp nhất. Quá trình này chuyển đổi dữ liệu ảnh ma trận pixel phức tạp thành một vector số nhiều chiều nằm trong không gian đặc trưng tuyến tính (gọi là Face Embedding). Các khuôn mặt của cùng một người sẽ nằm gần nhau trong không gian này, trong khi các khuôn mặt của các người khác nhau sẽ bị đẩy ra xa nhau.

### 2.4.2. Công thức toán học của các hàm mất mát huấn luyện nổi tiếng

#### 1. Hàm mất mát bộ ba (Triplet Loss) - Sử dụng trong FaceNet:
Mục tiêu của hàm mất mát Triplet Loss là học biểu diễn không gian sao cho khoảng cách giữa ảnh gốc (Anchor - ảnh của người A) và ảnh tích cực (Positive - ảnh khác của người A) là nhỏ nhất, đồng thời khoảng cách giữa ảnh gốc và ảnh tiêu cực (Negative - ảnh của người B) phải lớn hơn một khoảng biên $\alpha$ nhất định.

$$\mathcal{L} = \sum_{i=1}^{N} \max \left( 0, \|f(x_i^a) - f(x_i^p)\|_2^2 - \|f(x_i^a) - f(x_i^n)\|_2^2 + \alpha \right)$$

*Giải thích công thức:*
*   $x_i^a$ (Anchor): Ảnh khuôn mặt mốc của người thứ $i$.
*   $x_i^p$ (Positive): Ảnh khuôn mặt khác của chính người thứ $i$.
*   $x_i^n$ (Negative): Ảnh khuôn mặt của một người khác hoàn toàn.
*   $f(x)$ là hàm trích xuất đặc trưng của mạng nơ-ron, trả về vector đặc trưng của ảnh $x$.
*   $\|f(x_i^a) - f(x_i^p)\|_2^2$ là bình phương khoảng cách Euclid giữa vector đặc trưng ảnh mốc và ảnh cùng một người.
*   $\|f(x_i^a) - f(x_i^n)\|_2^2$ là bình phương khoảng cách Euclid giữa vector đặc trưng ảnh mốc và ảnh người khác.
*   $\alpha$ là tham số biên (margin) bắt buộc khoảng cách giữa ảnh người khác và ảnh mốc phải lớn hơn khoảng cách giữa hai ảnh cùng người một lượng tối thiểu là $\alpha$.
*   Hàm $\max(0, \cdot)$ đảm bảo rằng nếu khoảng cách tiêu cực đã đủ xa khoảng cách tích cực cộng thêm biên $\alpha$, độ mất mát (loss) sẽ bằng 0 (mạng nơ-ron không cần điều chỉnh trọng số cho bộ ba này nữa).

#### 2. Hàm mất mát biên góc cộng thêm (Additive Angular Margin Loss) - Sử dụng trong ArcFace:
Nhược điểm của Triplet Loss là sự bùng nổ số lượng bộ ba khi huấn luyện tập dữ liệu lớn. ArcFace giải quyết bằng cách ánh xạ các đặc trưng lên bề mặt của một siêu cầu đa chiều (bằng cách chuẩn hóa trọng số và đặc trưng đầu ra về độ dài bằng 1) và tối ưu hóa trực tiếp góc giữa vector đặc trưng và vector trọng số của lớp đích.

$$\mathcal{L} = -\frac{1}{N} \sum_{i=1}^{N} \log \frac{e^{s(\cos(\theta_{y_i} + m))}}{e^{s(\cos(\theta_{y_i} + m))} + \sum_{j \neq y_i} e^{s \cos \theta_j}}$$

*Giải thích công thức:*
*   $N$ là số lượng mẫu huấn luyện trong một lượt (batch).
*   $\theta_{y_i}$ là góc giữa vector đặc trưng trích xuất từ ảnh đầu vào và vector trọng số của lớp đích $y_i$ tương ứng với nhãn đúng của sinh viên đó.
*   $m$ là tham số biên góc cộng thêm (Additive angular margin). Bằng cách cộng thêm $m$ trực tiếp vào góc $\theta_{y_i}$ bên trong hàm Cosine, mạng buộc phải kéo góc $\theta_{y_i}$ thực tế nhỏ hơn nữa để vượt qua ngưỡng huấn luyện, từ đó làm nén chặt các vector đặc trưng của cùng một người lại với nhau trên mặt cầu.
*   $s$ là tham số tỉ lệ đặc trưng (Feature scale). Vì các đặc trưng được chuẩn hóa trên mặt cầu nên giá trị rất bé, hệ số $s$ giúp nhân phóng đại giá trị đầu ra của hàm cos để tránh hiện tượng triệt tiêu đạo hàm trong quá trình lan truyền ngược.
*   $\sum_{j \neq y_i} e^{s \cos \theta_j}$ là tổng điểm số của tất cả các lớp sai lệch khác (người khác).

### 2.4.3. Mô hình nhận diện SFace
Hệ thống sử dụng mô hình **SFace** chạy trực tiếp qua hàm `cv2.FaceRecognizerSF` của OpenCV. SFace kế thừa thuật toán tối ưu của hàm mất mát ArcFace nhưng được tinh chỉnh cấu trúc mạng siêu nhẹ. Mô hình trích xuất ra một vector đặc trưng sinh trắc học có kích thước cố định là 128 chiều:
$$e \in \mathbb{R}^{128}$$
Các vector đặc trưng này được chuẩn hóa tự động về độ dài bằng $1.0$ (tức $\|e\|_2 = 1.0$). Điều này mang lại sự thuận tiện rất lớn vì việc tính toán độ tương đồng giữa hai khuôn mặt trong không gian đa chiều thực chất chỉ là phép tính tích vô hướng của hai vector, giúp thực thi siêu tốc trên CPU.

## 2.5. Cơ sở dữ liệu và kỹ thuật so khớp

Để xác định danh tính sinh viên, vector đặc trưng $e_{live}$ trích xuất từ luồng camera sẽ được so khớp lần lượt với các vector đặc trưng mẫu $e_{stored}$ lưu trữ trong cơ sở dữ liệu SQLite thông qua hai công cụ đo khoảng cách toán học sau:

### 2.5.1. Độ tương đồng Cosine (Cosine Similarity)
Độ tương đồng Cosine đo góc giữa hai vector đặc trưng trong không gian đa chiều mà không phụ thuộc vào độ dài vật lý của chúng:
$$\text{CosineSimilarity}(A, B) = \cos(\theta) = \frac{A \cdot B}{\|A\|_2 \|B\|_2} = \frac{\sum_{i=1}^{d} A_i B_i}{\sqrt{\sum_{i=1}^{d} A_i^2} \sqrt{\sum_{i=1}^{d} B_i^2}}$$

*Giải thích công thức:*
*   $A$ và $B$ là hai vector đặc trưng 128 chiều đại diện cho khuôn mặt cần so sánh.
*   $A_i, B_i$ lần lượt là giá trị tọa độ tại chiều thứ $i$ của hai vector.
*   $A \cdot B = \sum_{i=1}^{d} A_i B_i$ là tích vô hướng của hai vector.
*   $\|A\|_2 = \sqrt{\sum_{i=1}^{d} A_i^2}$ là chuẩn L2 (độ dài Euclid) của vector $A$.
*   Giá trị Cosine Similarity nằm trong khoảng $[-1, 1]$. Giá trị bằng $1$ nghĩa là hai vector trùng hướng hoàn toàn (hai khuôn mặt cực kỳ giống nhau), bằng $0$ thể hiện hai vector vuông góc (không liên quan), và bằng $-1$ thể hiện hai vector đối ngược hướng hoàn toàn.
*   *Lưu ý thực tế:* Do mô hình SFace đã chuẩn hóa các vector đặc trưng về chuẩn L2 bằng $1.0$ ($\|A\|_2 = \|B\|_2 = 1.0$), công thức thực tế rút gọn tối giản thành:
    $$\text{CosineSimilarity}(A, B) = A \cdot B = \sum_{i=1}^{128} A_i B_i$$
    Phép tính tích vô hướng rút gọn này được CPU tính toán cực kỳ nhanh dưới dạng phép toán nhân cộng tích lũy cơ bản.

### 2.5.2. Khoảng cách Euclid (Euclidean Distance)
Khoảng cách Euclid đo khoảng cách đường thẳng vật lý ngắn nhất nối giữa hai điểm đầu mút vector trong không gian đa chiều:
$$\text{EuclideanDistance}(A, B) = \|A - B\|_2 = \sqrt{\sum_{i=1}^{d} (A_i - B_i)^2}$$

*Giải thích công thức:*
*   Phép toán tính tổng bình phương hiệu số tọa độ tại từng chiều giữa hai vector rồi lấy căn bậc hai.
*   Khoảng cách Euclid luôn là một số không âm $\ge 0$. Khoảng cách càng nhỏ (gần về $0$) thể hiện hai khuôn mặt càng giống nhau.

*So sánh lựa chọn:* Trong các bài toán nhận diện sinh trắc học đã chuẩn hóa vector đặc trưng lên mặt cầu, độ tương đồng Cosine và khoảng cách Euclid tỷ lệ nghịch chặt chẽ với nhau thông qua hệ thức hình học:
$$\|A - B\|_2^2 = \|A\|_2^2 + \|B\|_2^2 - 2(A \cdot B) = 2 - 2\text{CosineSimilarity}(A, B)$$
Dự án ưu tiên sử dụng độ tương đồng Cosine vì tính trực quan của điểm số (thường nằm trong khoảng $[0.5, 1.0]$ cho ảnh người thật) dễ thiết lập các ngưỡng an toàn điểm danh trực quan cho người dùng.

## 2.6. Làm mịn theo thời gian (Temporal Smoothing)

Trong luồng camera thời gian thực, hình ảnh khuôn mặt thu nhận được thường bị nhiễu do rung động vật lý của camera, thay đổi góc chiếu sáng hoặc bóng đổ tức thời. Điều này khiến điểm số liveness thô từ mô hình MiniFASNet dao động liên tục quanh ngưỡng quyết định, gây ra hiện tượng nhấp nháy trạng thái (state flickering) - khuôn mặt bị chuyển đổi liên tục giữa Real và Spoof trong khoảng thời gian rất ngắn. Để khắc phục hiện tượng này, dự án triển khai bộ lọc làm mịn theo thời gian `LivenessTracker` sử dụng 3 giải pháp toán học bổ trợ:

### 2.6.1. Thuật toán Trung bình trượt lũy thừa (Exponential Moving Average - EMA)
Bộ theo dõi liveness không sử dụng trực tiếp điểm số tức thời $X_t$ của khung hình hiện tại mà tính toán điểm số liveness làm mịn tích lũy $S_t$:
$$S_t = \alpha \cdot X_t + (1 - \alpha) \cdot S_{t-1}$$

*Giải thích công thức:*
*   $S_t$ là điểm số liveness đã được làm mịn ở khung hình hiện tại $t$.
*   $X_t$ là điểm số liveness thô do MiniFASNet dự đoán tại khung hình hiện tại $t$.
*   $S_{t-1}$ là điểm số liveness làm mịn tích lũy từ khung hình trước $t-1$.
*   $\alpha \in [0, 1]$ là hệ số làm mịn (dự án thiết lập mặc định $\alpha = 0.4$). Hệ số $\alpha$ đại diện cho tốc độ cập nhật của bộ lọc. Với $\alpha=0.4$, hệ thống dành $40\%$ sự tin tưởng cho khung hình mới và giữ lại $60\%$ quán tính thông tin lịch sử từ quá khứ. Điều này giúp triệt tiêu hoàn toàn các đột biến điểm số bất thường (như một khung hình liveness bị sụt giảm bất chợt do góc khuất sáng).

### 2.6.2. Cơ chế trễ kép Hysteresis (Ngưỡng kép)
Để đưa ra quyết định phân loại trạng thái liveness cuối cùng, hệ thống áp dụng cơ chế trễ ngưỡng kép (Hysteresis) thay vì sử dụng một ngưỡng duy nhất. Hệ thống định nghĩa hai ngưỡng phân biệt:
*   Ngưỡng trên (High Threshold): $T_{high} = 0.65$
*   Ngưỡng dưới (Low Threshold): $T_{low} = 0.45$

Trạng thái quyết định của hệ thống được cập nhật theo máy trạng thái sau:
*   Nếu trạng thái hiện tại đang là **SPOOF (Giả mạo)**: Chỉ cho phép chuyển đổi trạng thái sang **REAL (Thật)** khi điểm số làm mịn $S_t \ge T_{high} = 0.65$.
*   Nếu trạng thái hiện tại đang là **REAL (Thật)**: Chỉ cho phép chuyển đổi trạng thái sang **SPOOF (Giả mạo)** khi điểm số làm mịn $S_t \le T_{low} = 0.45$.
*   Nếu điểm số $S_t$ dao động trong khoảng giữa $(T_{low}, T_{high})$: Hệ thống giữ nguyên trạng thái cũ mà không thay đổi.

*Giải thích trực quan:* Cơ chế này tạo ra một vùng đệm an toàn nằm giữa $[0.45, 0.65]$. Trạng thái hệ thống chỉ thay đổi khi có sự biến động thực sự lớn và nhất quán qua nhiều khung hình liên tiếp. Nó triệt tiêu hoàn toàn sự dao động nhấp nháy tại biên quyết định, giúp trải nghiệm người dùng mượt mà và ổn định.

### 2.6.3. Chỉ số đo độ trùng khớp vị trí IoU (Intersection over Union)
Để đảm bảo lịch sử điểm số tích lũy EMA của khuôn mặt được cập nhật chính xác cho cùng một người qua các khung hình, hệ thống cần theo dõi (tracking) vị trí khuôn mặt. Sử dụng chỉ số trùng khớp hộp bao IoU:
$$\text{IoU}(A, B) = \frac{\text{Area}(A \cap B)}{\text{Area}(A \cup B)} = \frac{\text{Diện tích vùng giao nhau}}{\text{Diện tích vùng hợp nhau}}$$

*Giải thích công thức:*
*   $A$ là tọa độ hộp bao khuôn mặt ở khung hình trước.
*   $B$ là tọa độ hộp bao khuôn mặt ở khung hình hiện tại.
*   Nếu chỉ số $\text{IoU}(A, B)$ vượt qua ngưỡng định sẵn (ví dụ: $0.5$), hệ thống xác nhận khuôn mặt ở hai khung hình là của cùng một đối tượng đang di chuyển nhẹ và tiếp tục cập nhật công thức EMA. Ngược lại, nếu IoU nhỏ hơn ngưỡng, nghĩa là đối tượng cũ đã rời đi hoặc có đối tượng mới xen vào vị trí đó, hệ thống sẽ tự động khởi tạo lại bộ tích lũy EMA liveness từ đầu cho đối tượng mới này.

## 2.7. Tổng kết chương

Chương 2 đã trình bày chi tiết và hệ thống hóa toàn bộ cơ sở lý thuyết toán học và mô hình học sâu cốt lõi phục vụ xây dựng hệ thống điểm danh, bao gồm:
1.  Nền tảng thị giác máy tính và học sâu tích chập.
2.  Mô hình phát hiện khuôn mặt Anchor-free YuNet với khả năng trích xuất 5 điểm mốc đặc trưng hỗ trợ căn chỉnh ảnh cực nhanh trên CPU.
3.  Bộ lọc thực thể sống MiniFASNet kết hợp cơ chế Squeeze-and-Excitation cùng phép biến đổi tối ưu hóa không gian Logit để phân loại thật/giả.
4.  Lý thuyết biểu diễn đặc trưng (Embedding) và các hàm mất mát nổi tiếng (Triplet Loss, ArcFace Loss) giúp mô hình SFace trích xuất vector đặc trưng 128 chiều chuẩn hóa.
5.  Các độ đo khoảng cách hình học Cosine Similarity và Euclidean Distance phục vụ so khớp danh tính.
6.  Các giải pháp ổn định tín hiệu thời gian thực bao gồm EMA, Hysteresis và IoU Tracking.

Những nền tảng toán học và giải pháp mô hình này đóng vai trò là kim chỉ nam định hướng trực tiếp cho việc thiết kế kiến trúc phần mềm, cấu trúc cơ sở dữ liệu và triển khai lập trình thực tế ở Chương 3.
