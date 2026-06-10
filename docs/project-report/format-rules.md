# Quy tắc định dạng (Format Rules) cho Project Report

Tất cả các file Markdown trong thư mục `docs/project-report` phải tuân thủ các quy tắc sau để đảm bảo khi copy nội dung sang Microsoft Word sẽ giữ được định dạng tốt nhất và ít gặp lỗi nhất:

1. **Heading (Tiêu đề):** Chỉ sử dụng dấu thăng `#` chuẩn của Markdown cho các cấp độ tiêu đề (VD: `# Chương 1`, `## 1.1`, `### 1.1.1`). Word sẽ tự động nhận diện các heading này.
2. **Paragraph (Đoạn văn):** Giữa các đoạn văn phải cách nhau đúng một dòng trống (blank line). Không sử dụng thẻ `<br>` hoặc `<p>` của HTML.
3. **List (Danh sách):**
   - Danh sách không thứ tự: Sử dụng dấu gạch ngang `-` hoặc dấu sao `*` có dấu cách phía sau.
   - Danh sách có thứ tự: Sử dụng số thứ tự kèm dấu chấm `1.`, `2.`, `3.`.
   - Tránh lồng ghép danh sách quá nhiều tầng (tối đa 2 tầng) vì Word dễ bị lỗi thụt lề khi copy.
4. **Định dạng chữ:** Sử dụng `**in đậm**` và `*in nghiêng*`. Tuyệt đối không dùng các thẻ HTML như `<b>`, `<i>`, `<u>`.
5. **Bảng (Table):** Sử dụng bảng Markdown chuẩn. Tránh gộp ô (merge cells) vì Markdown không hỗ trợ tốt và khi dán sang Word sẽ bị vỡ cấu trúc.
6. **Hình ảnh (Images):** Dùng cú pháp `![Mô tả ảnh](đường/dẫn/ảnh)`.
7. **Không dùng HTML/CSS:** Tuyệt đối không nhúng các đoạn mã HTML hoặc CSS nội tuyến (inline CSS) vào file Markdown.
