# PreenCut Tests

Thư mục này chứa tất cả các file test cho dự án PreenCut.

## Cấu trúc Test

### 🧪 Test Files

- `test_enhanced_features.py` - Test các tính năng cải tiến
- `test_gradio_fix.py` - Test các sửa lỗi Gradio UI
- `test_progress.py` - Test thanh tiến trình real-time
- `test_timestamp_fix.py` - Test tính chính xác của timestamp
- `test_social_media_download.py` - Test tính năng download social media
- `test_simple_social_download.py` - Test đơn giản cho social media download

### 🚀 Chạy Tests

#### Chạy tất cả tests:
```bash
python tests/run_all_tests.py
```

#### Chạy test riêng lẻ:
```bash
# Test enhanced features
python tests/test_enhanced_features.py

# Test social media download
python tests/test_social_media_download.py

# Test timestamp accuracy
python tests/test_timestamp_fix.py
```

### 📋 Test Categories

#### Core Functionality Tests
- **Enhanced Features**: Test các tính năng mới như word count, relevancy scoring
- **Timestamp Accuracy**: Test độ chính xác của việc cắt video theo timestamp

#### UI/UX Tests
- **Gradio Interface**: Test giao diện Gradio và event bindings
- **Progress Indicators**: Test thanh tiến trình real-time

#### Social Media Tests
- **Optimization**: Test tối ưu hóa cho TikTok, Instagram, YouTube
- **Download**: Test tính năng download clip viral

### 🔍 Test Requirements

Các test cần các dependency sau:
- Python 3.8+
- Gradio
- All PreenCut modules
- FFmpeg (cho video processing tests)

### 📝 Notes

- Một số test có thể báo lỗi do thiếu file video thật - đây là hành vi mong đợi
- Test focus vào logic validation và error handling
- Các test integration cần environment setup đầy đủ
