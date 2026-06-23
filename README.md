# Face Attendance System — Offline Anti-Spoofing Desktop App

**Hệ thống điểm danh khuôn mặt offline chống giả mạo** — Ứng dụng Desktop Python tự động hóa điểm danh bằng nhận diện khuôn mặt với phát hiện thực thể sống (liveness detection).

## Overview / Tổng quan
Offline face-attendance system with anti-spoofing (MiniFASNet V2 SE). PyQt5 UI, SQLite/WAL, ONNX Runtime. Runs on CPU, no internet required.

Hệ thống điểm danh khuôn mặt hoạt động hoàn toàn offline, tích hợp chống giả mạo 2D (MiniFASNet V2 SE). Giao diện PyQt5, cơ sở dữ liệu SQLite WAL, suy luận ONNX Runtime. Chạy trên CPU, không cần Internet.

## Quick Start / Khởi động nhanh
```bash
pip install -e .
cp .env.example .env   # configure / cấu hình
attendance-storage-init
attendance-app
```

## Documentation / Tài liệu
- **Architecture / Kiến trúc:** `docs/architecture.md`
- **AI Pipeline / Đường ống AI:** `docs/ai-pipeline.md`
- **Database / Cơ sở dữ liệu:** `docs/database.md`
- **Code Map / Bản đồ mã nguồn:** `codemap.md`
- **Thesis Report / Báo cáo luận văn:** `docs/project-report/`

## Known Limitations / Hạn chế đã biết
- 2D liveness model: sensitive to lighting, vulnerable to 3D masks / Mô hình liveness 2D: nhạy cảm với ánh sáng, dễ bị đánh lừa bởi mặt nạ 3D
- CPU-intensive on low-end hardware / Tiêu thụ CPU cao trên máy cấu hình thấp
- Single-face only (no multi-face tracking) / Chỉ nhận diện đơn lẻ (chưa hỗ trợ đa khuôn mặt)
- UI strings hardcoded in Vietnamese (no i18n) / Chuỗi giao diện mã cứng bằng tiếng Việt (chưa hỗ trợ đa ngôn ngữ)

## License
MIT — Academic thesis project / Dự án luận văn học thuật.
