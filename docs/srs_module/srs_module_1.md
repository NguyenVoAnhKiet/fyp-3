# TÀI LIỆU PHÂN RÃ KIẾN TRÚC MODULE DỰ ÁN

**Dự án:** Hệ thống điểm danh sử dụng nhận diện khuôn mặt và chống giả mạo

**Tham chiếu:** Phân rã từ tài liệu SRS v2.0

Tài liệu này định nghĩa cấu trúc phân rã của dự án thành 6 module độc lập. Mỗi module đại diện cho một ranh giới trách nhiệm rõ ràng trong hệ thống, cho phép phát triển, kiểm thử và tích hợp một cách riêng biệt nhằm kiểm soát chặt chẽ chất lượng đầu ra.

## Module 1: Cốt lõi Dữ liệu và Lưu trữ (Database & Storage Core)

Module này chịu trách nhiệm xây dựng nền tảng lưu trữ toàn bộ thông tin cục bộ của hệ thống bằng SQLite3. Trọng tâm của module là việc khởi tạo, quản lý và kết nối năm bảng dữ liệu chính bao gồm: thông tin người dùng, mảng vector đặc trưng khuôn mặt (embeddings), thông tin các phiên điểm danh, lịch sử nhận diện chi tiết và bảng cài đặt cấu hình hệ thống. Yêu cầu đầu ra của phân hệ này là một tập hợp các lớp (classes) xử lý cơ sở dữ liệu hoàn chỉnh, cung cấp các hàm tương tác (CRUD) hoạt động độc lập và an toàn để không làm nghẽn các luồng xử lý chính của ứng dụng.

## Module 2: Động cơ AI và Xử lý Luồng hình ảnh (AI Engine & Vision Pipeline)

Đây là trái tim tính toán của hệ thống điểm danh. Module này đóng gói toàn bộ các tác vụ nặng liên quan đến thị giác máy tính và học sâu, được thiết kế để chạy trên một luồng (thread) hoàn toàn tách biệt với giao diện. Nhiệm vụ của nó là tiếp nhận luồng video liên tục từ camera, thực hiện phát hiện khuôn mặt, sau đó chuyển qua mô hình MiniFASNet để chấm điểm độ thực tế (Liveness Score). Nếu vượt qua bài kiểm tra chống giả mạo, hình ảnh tiếp tục được đưa qua DeepFace để trích xuất vector đặc trưng và đối chiếu với cơ sở dữ liệu. Kết quả cuối cùng sẽ được trả về dưới dạng sự kiện (event) để các module khác tiếp nhận.

## Module 3: Phân hệ Quản trị Người dùng và Đăng ký Sinh trắc học

Dành riêng cho quyền Quản trị viên (Admin), phân hệ này giải quyết bài toán nhập liệu và khởi tạo danh tính ban đầu. Logic cốt lõi bao gồm việc cung cấp luồng thao tác để thu thập hình ảnh người dùng mới. Khi hệ thống kích hoạt chế độ đăng ký, nó sẽ tự động hướng dẫn người dùng, trích xuất hình ảnh đạt chuẩn, tính toán vector embedding trung bình và lưu trực tiếp mảng dữ liệu số này vào cơ sở dữ liệu. Đặc tả bảo mật khắt khe yêu cầu module này phải hủy bỏ toàn bộ dữ liệu ảnh thô ngay sau khi quá trình trích xuất hoàn tất nhằm tuân thủ quyền riêng tư.

## Module 4: Phân hệ Điểm danh và Xử lý Phiên học

Module này phục vụ trực tiếp cho người dùng cuối (Giảng viên) với mục tiêu vận hành buổi học một cách trơn tru nhất. Khởi đầu bằng việc tạo lập một phiên điểm danh mới gắn liền với tên môn học và lớp học cụ thể, hệ thống sẽ chuyển sang trạng thái hoạt động (ACTIVE). Trong suốt quá trình này, module sẽ liên tục lắng nghe kết quả trả về từ Động cơ AI, đối chiếu dữ liệu để ngăn chặn việc ghi nhận trùng lặp cho một sinh viên, đồng thời cập nhật trạng thái (Thành công hoặc Cảnh báo giả mạo) vào thẳng cơ sở dữ liệu lịch sử theo thời gian thực.

## Module 5: Kiến trúc Giao diện và Điều hướng (UI/UX Architecture)

Sử dụng PyQt5 hoặc Tkinter, module này đóng vai trò lớp vỏ thị giác bao bọc toàn bộ hệ thống. Nội dung triển khai bao gồm việc xây dựng khung ứng dụng chính, quản lý các trạng thái màn hình (từ màn hình chờ IDLE sang màn hình điểm danh trực tiếp). Yêu cầu kỹ thuật trọng tâm là hiển thị luồng video từ camera một cách mượt mà, duy trì tốc độ khung hình trên 24 FPS. Phân hệ này cũng chịu trách nhiệm tiếp nhận các lệnh từ phím tắt (S, E, Q) và cung cấp các phản hồi thị giác rõ ràng bằng mã màu (Xanh, Vàng, Đỏ) dựa trên trạng thái điểm danh.

## Module 6: Tiện ích Báo cáo và Cấu hình Hệ thống

Module cuối cùng tập trung vào việc khai thác dữ liệu đã thu thập và tinh chỉnh hệ thống cho phù hợp với môi trường thực tế. Tính năng cấu hình cung cấp một giao diện cho phép quản trị viên hoặc người dùng lựa chọn thiết bị camera đầu vào và cân chỉnh linh hoạt các thông số như ngưỡng Liveness hay ngưỡng Similarity thông qua thanh trượt. Tính năng báo cáo đảm nhiệm việc truy vấn toàn bộ dữ liệu của một phiên học đã kết thúc, định dạng lại và trích xuất thành tệp Excel (.xlsx) hoặc CSV, cung cấp công cụ đắc lực cho việc đánh giá điểm chuyên cần.