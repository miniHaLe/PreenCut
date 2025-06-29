# 📱 Social Media Download Feature

## Tổng quan

Tính năng **Social Media Download** cho phép người dùng tải xuống các clip video đã được tối ưu hóa cho các nền tảng mạng xã hội như TikTok, Instagram Reels, và YouTube Shorts.

## 🚀 Tính năng chính

### 1. Tối ưu hóa cho từng nền tảng
- **TikTok**: Clip 15-180s với viral hooks
- **Instagram Reels**: Clip 15-90s tập trung vào thẩm mỹ
- **YouTube Shorts**: Clip 15-60s tối ưu cho retention
- **Universal**: Tối ưu chung cho tất cả nền tảng

### 2. Phân tích AI thông minh
- **Engagement Scoring**: Đánh giá tiềm năng tương tác (1-10)
- **Viral Potential**: Phân loại thành Thấp/Trung bình/Cao
- **Hook Generation**: Tạo câu mở đầu thu hút
- **Hashtag Suggestions**: Gợi ý hashtag phù hợp

### 3. Tùy chọn download linh hoạt
- **Zip Archive**: Tất cả clip trong một file zip
- **Platform Folders**: Mỗi nền tảng một folder riêng
- **Metadata Files**: Thông tin chi tiết cho mỗi clip

## 🎯 Cách sử dụng

### Bước 1: Tạo nội dung viral
1. Chọn nền tảng mục tiêu (TikTok/Instagram/YouTube/Universal)
2. Nhập chủ đề hoặc xu hướng muốn tạo nội dung
3. Chọn phong cách nội dung (Giáo dục/Giải trí/Cảm hứng/etc.)
4. Đặt số lượng clip tối đa (3-10)
5. Nhấn "🎯 Tạo nội dung viral"

### Bước 2: Xem và chọn clip
- Xem danh sách clip được tối ưu theo điểm engagement
- Kiểm tra thumbnail, thời lượng, và tiềm năng viral
- Chọn các clip muốn tải xuống bằng checkbox

### Bước 3: Tải xuống
1. Chọn chế độ download:
   - **Zip**: Tất cả clip trong một file
   - **Platform folders**: Riêng lẻ theo nền tảng
2. Nhấn "📱 Tải xuống clip viral"
3. Nhận file kết quả với clip và metadata

## 📊 Thông tin metadata

Mỗi clip được tải xuống đi kèm file metadata chứa:
- Nền tảng mục tiêu
- Tiêu đề viral được tạo
- Hook câu mở đầu
- Hashtags được đề xuất
- Điểm engagement
- Viral potential
- Thời gian trong video gốc

## 🔧 Thông tin kỹ thuật

### Cấu trúc file output
```
social_media_[task_id]/
├── viral_clips.zip (nếu chọn zip mode)
├── tiktok_clips/
│   ├── tiktok_amazing_content.mp4
│   └── tiktok_amazing_content_metadata.txt
├── instagram_clips/
│   ├── instagram_reel_content.mp4
│   └── instagram_reel_content_metadata.txt
└── youtube_clips/
    ├── youtube_shorts_content.mp4
    └── youtube_shorts_content_metadata.txt
```

### Định dạng metadata
```
Nền tảng: TikTok
Tiêu đề viral: Amazing Content Goes Viral
Hook: Bạn có biết điều này?
Hashtags: #viral #tiktok #amazing
Điểm engagement: 8.5/10 ⭐
Viral potential: 🔴 Cao
Thời gian: 00:00:10 - 00:00:25
```

## ⚡ Tối ưu hóa hiệu suất

### Platform-specific optimization
- **TikTok**: Focus vào hook mạnh, trending sounds, quick cuts
- **Instagram**: Tập trung vào visual appeal, aesthetic, stories
- **YouTube**: Retention-focused, clear titles, strong thumbnails

### AI Scoring Algorithm
```python
composite_score = (
    relevance_score * 0.3 +
    engagement_score * 0.4 +
    platform_fit_score * 0.2 +
    viral_potential_score * 0.1
)
```

## 🐛 Troubleshooting

### Lỗi thường gặp

1. **"Không có tác vụ xử lý nào"**
   - Đảm bảo đã xử lý video trước khi tối ưu
   - Kiểm tra task ID có hợp lệ

2. **"Chưa có kết quả tối ưu hóa nào"**
   - Chạy tối ưu hóa social media trước
   - Đợi quá trình phân tích hoàn tất

3. **"Vui lòng chọn ít nhất một clip"**
   - Check các checkbox ở cột đầu tiên
   - Sử dụng nút "Chọn tất cả" nếu cần

4. **"FFmpeg error"**
   - Kiểm tra FFmpeg đã cài đặt
   - Đảm bảo file video gốc còn tồn tại

### Performance tips
- Giới hạn số lượng clip để tăng tốc xử lý
- Sử dụng prompt cụ thể để có kết quả tốt hơn
- Chọn mô hình AI phù hợp với nhu cầu

## 🔄 Integration với workflow

### Quy trình làm việc khuyến nghị
1. **Upload & Analysis**: Tải video và phân tích cơ bản
2. **Topic Extraction**: Trích xuất theo chủ đề cụ thể (tùy chọn)
3. **Social Optimization**: Tối ưu cho nền tảng mạng xã hội
4. **Review & Select**: Xem và chọn clip tốt nhất
5. **Download & Deploy**: Tải và triển khai lên các nền tảng

### Best practices
- Sử dụng video chất lượng cao làm input
- Prompt cụ thể sẽ cho kết quả tốt hơn
- Kiểm tra thumbnail trước khi download
- Test với nhiều nền tảng để tối ưu reach
