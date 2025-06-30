# 🎬 PreenCut - AI-Powered Video Intelligence Platform

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Gradio Interface](https://img.shields.io/badge/Web%20UI-Gradio-FF4B4B.svg)](https://gradio.app/)
[![Production Ready](https://img.shields.io/badge/Production-Ready-green.svg)](#production-deployment)

PreenCut is an intelligent video editing tool that automatically analyzes audio/video content using advanced speech recognition and large language models. It helps you quickly find and extract relevant segments from media files using natural language queries, with enterprise-grade architecture for production deployment.

![Giao diện Gradio](docs/screenshot.png)

## 🎉 What's New - Production Ready!

PreenCut has been **completely refactored** for enterprise production use while maintaining all original functionality:

- **🏗️ Clean Architecture**: Service-oriented design with dependency injection
- **⚙️ Environment Configuration**: Professional `.env`-based configuration system
- **📊 Structured Logging**: JSON logging with performance metrics and context
- **🛡️ Robust Error Handling**: Custom exceptions with clear error codes and suggestions
- **🔧 Developer Experience**: Full type hints, comprehensive docs, and testing support
- **🚀 Production Deployment**: Docker support, health checks, and monitoring
- **🔄 Backwards Compatibility**: Gradual migration path for existing code

## ✨ Key Features

### Core AI Capabilities
- **🎙️ Advanced Speech Recognition**: WhisperX integration for accurate transcription
- **🧠 LLM-Powered Analysis**: Large language model content segmentation and summarization
- **💬 Natural Language Queries**: Find video segments using descriptive commands like "Find all product introduction segments"
- **✂️ Smart Cutting**: Select and export segments as individual files or merged videos
- **📚 Batch Processing**: Find specific topics across multiple files
- **🔄 Re-analysis**: Experiment with different prompts without reprocessing audio
- **🎯 Topic Extraction**: Extract contextually complete segments around specific topics with precise timestamps

### Social Media Optimization
- **📱 Platform Optimization**: Create viral clips for TikTok, Instagram Reels, YouTube Shorts
- **📊 Smart Scoring**: Relevancy, engagement, and viral potential assessment
- **📥 Flexible Downloads**: Multiple download options optimized for each platform
- **🎵 Viral Content Detection**: AI-powered analysis of content virality potential

### Production Features
- **🌍 Multi-Environment**: Development, staging, and production configurations
- **📈 Performance Monitoring**: Built-in metrics and health checks
- **🔒 Security**: Environment-based secrets and secure file handling
- **🐳 Docker Support**: Containerized deployment with Docker Compose
- **📊 Structured Logs**: JSON formatted logs for production monitoring
- **🔧 Service Architecture**: Modular, testable service interfaces

## 📁 Project Structure

```
PreenCut/
├── 🏗️ config/                     # Configuration management
│   ├── __init__.py                # Legacy compatibility exports
│   └── settings.py                # Environment-based configuration
├── 🔧 core/                       # Core infrastructure
│   ├── __init__.py
│   ├── logging.py                 # Structured JSON logging
│   ├── exceptions.py              # Custom exception system
│   └── dependency_injection.py    # DI container for services
├── 🎯 services/                   # Business logic services
│   ├── __init__.py
│   ├── interfaces.py              # Service contracts
│   ├── video_service.py           # Video processing service
│   ├── file_service.py            # File management service
│   ├── llm_service.py             # LLM integration service
│   └── speech_recognition_service.py
├── 🛠️ utils/                      # Organized utilities
│   ├── __init__.py
│   ├── file_utils.py              # File operations
│   ├── time_utils.py              # Time utilities
│   └── media_utils.py             # Media processing
├── 🌐 web/                        # Web interface
│   └── gradio_ui.py               # Gradio web UI
├── 📦 modules/                    # Core processing modules
│   ├── video_processor.py         # Legacy video processor
│   ├── video_processor_refactored.py  # Refactored processor
│   ├── llm_processor.py           # Legacy LLM processor
│   ├── llm_processor_refactored.py    # Refactored LLM
│   ├── text_aligner.py            # Text alignment
│   ├── processing_queue.py        # Task queue management
│   └── speech_recognizers/        # Speech recognition implementations
├── 🧪 tests/                      # Comprehensive test suite
│   ├── run_all_tests.py           # Test runner
│   ├── test_enhanced_features.py  # Feature tests
│   └── ...                        # Additional test files
├── 📚 docs/                       # Documentation
│   ├── PRODUCTION_DEPLOYMENT.md   # Production deployment guide
│   ├── REFACTORING_SUMMARY.md     # Refactoring documentation
│   └── ...                        # Additional documentation
├── 📊 logs/                       # Application logs
├── 🗂️ temp/                       # Temporary processing files
├── 📤 output/                     # Output files
├── .env.example                   # Environment template
├── config.py                      # Legacy config (deprecated)
├── utils.py                       # Legacy utils (deprecated)
├── main.py                        # Application entry point
└── requirements.txt               # Python dependencies
```

## 🚀 Quick Start

### 1. Environment Setup

```bash
# Clone the repository
git clone https://github.com/roothch/PreenCut.git
cd PreenCut

# Copy environment template
cp .env.example .env

# Edit .env with your settings
nano .env
```

### 2. Install Dependencies

```bash
# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows

# Install requirements
pip install -r requirements.txt
```

### 3. Install FFmpeg

```bash
# Ubuntu/Debian
sudo apt install ffmpeg

# CentOS/RHEL
sudo yum install ffmpeg

# macOS (using Homebrew)
brew install ffmpeg

# Windows: Download from https://ffmpeg.org/
```

### 4. Configure LLM Services

Set up your LLM API keys in the `.env` file:

```bash
# Example for DeepSeek and DouBao
DEEPSEEK_V3_API_KEY=your_deepseek_api_key
DOUBAO_1_5_PRO_API_KEY=your_doubao_api_key
```

### 5. Run Application

```bash
# Start the application
python main.py

# Access the web interface at:
# http://localhost:8860/web
```

## 🔧 Configuration

### Environment Variables (`.env`)

```env
# Application Settings
APP_ENV=development
DEBUG=true
PORT=8860

# GPU Configuration
WHISPER_DEVICE=cuda
WHISPER_BATCH_SIZE=16
WHISPER_MODEL_SIZE=large-v3
WHISPER_GPU_IDS=0,1

# File Processing
MAX_FILE_SIZE=10737418240  # 10GB
MAX_FILE_NUMBERS=10
TEMP_FOLDER=./temp
OUTPUT_FOLDER=./output

# Ollama Configuration
OLLAMA_HOST=localhost
OLLAMA_PORT=11434
OLLAMA_TIMEOUT=300
OLLAMA_KEEP_ALIVE=5m

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
LOG_FILE=logs/app.log

# API Keys (set your actual keys)
DEEPSEEK_V3_API_KEY=your_api_key_here
DOUBAO_1_5_PRO_API_KEY=your_api_key_here
```

### Legacy Configuration Support

Existing `config.py` imports continue to work with deprecation warnings:

```python
# Legacy (still works)
from config import TEMP_FOLDER, WHISPER_MODEL_SIZE

# New recommended approach
from config import get_config
config = get_config()
temp_folder = config.file.temp_folder
```

## 📖 Usage Guide

### Web Interface

1. **Start Application**: `python main.py`
2. **Open Browser**: Navigate to `http://localhost:8860/web`
3. **Upload Files**: Support for mp4, avi, mov, mkv, ts, mxf, mp3, wav, flac
4. **Configure Options**:
   - Select LLM model
   - Choose Whisper model size (tiny → large-v3)
   - Add custom analysis prompts (optional)
5. **Process**: Click "Start Processing" to analyze content
6. **Review Results**: View segments with timestamps, summaries, and AI-generated tags
7. **Topic Extraction**: Use "Extract segments by topic" tab for specific queries
8. **Export**: Use "Cutting Options" tab to select segments and export as ZIP or merged video

### RESTful API

#### Upload File
```bash
POST /api/upload
Content-Type: multipart/form-data

# Response
{
  "file_path": "/path/to/uploaded/file.mp4"
}
```

#### Create Task
```bash
POST /api/tasks
Content-Type: application/json

{
  "file_path": "/path/to/uploaded/file.mp4",
  "llm_model": "DeepSeek-V3-0324",
  "whisper_model_size": "large-v2",
  "prompt": "Extract important information, control time to 10s"
}

# Response
{
  "task_id": "unique_task_id"
}
```

#### Query Task Results
```bash
GET /api/tasks/{task_id}

# Response
{
  "status": "completed",
  "files": ["/path/to/processed/file.wav"],
  "result": [
    {
      "filename": "file.wav",
      "segments": [
        {
          "start": 1.145,
          "end": 9.329,
          "summary": "Content summary",
          "tags": ["tag1", "tag2"]
        }
      ]
    }
  ]
}
```

## 🎯 Topic Extraction Feature

The topic extraction feature leverages structured output capabilities of modern LLMs:

- **Complete Context**: Finds entire contextual segments where topics are discussed
- **Precise Timestamps**: Ensures accurate start/end times to capture complete narratives
- **Multiple Occurrences**: Identifies all instances of a topic throughout the video
- **Relevance Scoring**: Evaluates how relevant each segment is to your query
- **Structured Output**: Uses JSON schema functions for consistent, reliable results

### Using Topic Extraction:

1. Process your video files using "Start Processing"
2. Go to "Extract segments by topic" tab
3. Enter specific topic or prompt (e.g., "Find all discussions about renewable energy")
4. Select your preferred LLM model
5. Click "Extract segments by topic"
6. Go to "Cutting Options" tab to select and export identified segments

## 🏭 Production Deployment

### Docker (Recommended)

```bash
# Build and run with Docker Compose
docker-compose up -d

# View logs
docker-compose logs -f

# Scale services
docker-compose up -d --scale app=3
```

### Manual Deployment

1. **Server Setup**: Ubuntu 20.04+ or similar
2. **System Dependencies**: Python 3.8+, FFmpeg, CUDA drivers (for GPU)
3. **Application Setup**: Clone repo, configure environment, install dependencies
4. **Process Management**: Use systemd, supervisor, or PM2
5. **Reverse Proxy**: Nginx or Apache for production traffic
6. **Monitoring**: Set up log aggregation and health checks

See [`docs/PRODUCTION_DEPLOYMENT.md`](docs/PRODUCTION_DEPLOYMENT.md) for detailed instructions.

## 🔄 Migration from Legacy Code

### Gradual Migration Strategy

The refactoring maintains backwards compatibility while providing a migration path:

**Phase 1**: Update configuration (immediate)
```python
# Replace direct config imports with get_config()
from config import get_config
config = get_config()
```

**Phase 2**: Adopt new utilities (short-term)
```python
# Use organized utility modules
from utils.file_utils import generate_safe_filename
from utils.time_utils import seconds_to_hhmmss
```

**Phase 3**: Service architecture (long-term)
```python
# Use dependency injection for services
from core.dependency_injection import get_container
container = get_container()
video_service = container.get_video_service()
```

## 📊 Monitoring and Health Checks

### Health Endpoint
```bash
curl http://localhost:8860/health
```

### Log Analysis
```bash
# View real-time structured logs
tail -f logs/app.log | jq .

# Filter by log level
grep '"level":"ERROR"' logs/app.log | jq .

# Performance metrics
grep '"type":"performance"' logs/app.log | jq .
```

### GPU Monitoring
```bash
# Monitor GPU usage
nvidia-smi

# Watch GPU utilization
watch -n 1 nvidia-smi
```

## 🧪 Testing

### Run All Tests
```bash
# Comprehensive validation
python final_validation.py

# Service integration tests
python test_service_integration.py

# Refactoring validation
python test_refactoring.py

# Run existing test suite
cd tests
python run_all_tests.py
```

### Test Individual Components
```bash
python tests/test_enhanced_features.py
python tests/test_social_media_download.py
python tests/test_utils.py
```

## ⚡ Performance Optimization

### GPU Acceleration
- **CUDA Support**: Automatic GPU detection and utilization
- **Batch Processing**: Configurable batch sizes for optimal GPU memory usage
- **Mixed Precision**: Faster processing with maintained accuracy

### Configuration Tuning
```env
# For high-end GPUs (RTX 4090, A100)
WHISPER_BATCH_SIZE=32
WHISPER_MODEL_SIZE=large-v3

# For mid-range GPUs (RTX 3070, 4070)
WHISPER_BATCH_SIZE=16
WHISPER_MODEL_SIZE=large-v2

# For CPU-only systems
WHISPER_DEVICE=cpu
WHISPER_BATCH_SIZE=4
WHISPER_MODEL_SIZE=base
```

### Tips for Better Performance
- Use WhisperX for faster processing vs faster-whisper for shorter segments
- Adjust `WHISPER_BATCH_SIZE` based on available VRAM
- Use smaller model sizes for CPU-only systems
- Enable SSD storage for temp files when processing large videos

## 🛡️ Security Considerations

### Production Security
- **Environment Variables**: All secrets stored in environment files
- **File Upload Validation**: Strict file type and size validation
- **CORS Configuration**: Configurable cross-origin request handling
- **Rate Limiting**: Built-in protection against abuse
- **Input Sanitization**: Comprehensive input validation
- **Secure File Handling**: Safe temporary file management

### Best Practices
```env
# Production environment variables
APP_ENV=production
DEBUG=false
ALLOWED_ORIGINS=["https://yourdomain.com"]
MAX_FILE_SIZE=5368709120  # 5GB for production
ENABLE_RATE_LIMITING=true
```

## 🔮 Future Roadmap

### Planned Enhancements
1. **Database Integration**: PostgreSQL/MySQL for persistent task storage
2. **Message Queue**: Redis/RabbitMQ for horizontal scaling
3. **API Versioning**: RESTful API with proper versioning
4. **Microservices**: Split into smaller, focused services
5. **Kubernetes**: Container orchestration for cloud deployment
6. **Real-time Processing**: WebSocket support for live video analysis
7. **Advanced Analytics**: User behavior tracking and optimization

### Community Contributions
- Model optimization and fine-tuning
- Additional language support
- New export formats and integrations
- Performance benchmarking and optimization

## 📚 Documentation

- [`docs/REFACTORING_SUMMARY.md`](docs/REFACTORING_SUMMARY.md) - Detailed refactoring changes
- [`docs/PRODUCTION_DEPLOYMENT.md`](docs/PRODUCTION_DEPLOYMENT.md) - Production setup guide
- [`docs/REFACTORING_COMPLETION_SUMMARY.md`](docs/REFACTORING_COMPLETION_SUMMARY.md) - Migration completion guide

## 🤝 Contributing

### Development Setup
```bash
# Fork and clone the repository
git clone https://github.com/yourusername/PreenCut.git
cd PreenCut

# Create development environment
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Create feature branch
git checkout -b feature/your-feature-name
```

### Code Quality Standards
- **Type Hints**: All new code must include type annotations
- **Error Handling**: Comprehensive exception handling with custom error types
- **Logging**: Structured logging for all operations
- **Testing**: Unit tests for new functionality
- **Documentation**: Update documentation for new features

### Development Workflow
1. Create feature branch from main
2. Implement changes with tests
3. Ensure type safety with mypy
4. Update documentation
5. Submit pull request with detailed description

## 📞 Support

### Getting Help
- **Documentation**: Check existing documentation first
- **Error Messages**: Review error suggestions and context
- **Logs**: Check `logs/app.log` for detailed information
- **GitHub Issues**: Create issues for bugs or feature requests

### Performance Issues
- Monitor GPU usage with `nvidia-smi`
- Check disk space and I/O performance
- Review log files for bottlenecks
- Adjust batch sizes for your hardware configuration

### Common Issues
- **CUDA Out of Memory**: Reduce `WHISPER_BATCH_SIZE`
- **File Upload Errors**: Check `MAX_FILE_SIZE` configuration
- **LLM API Errors**: Verify API keys and service availability
- **Import Errors**: Ensure all dependencies are installed

## 📜 License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## ⭐ Star History

[![Star History Chart](https://api.star-history.com/svg?repos=roothch/preencut&type=Date)](https://star-history.com/#roothch/preencut&Date)

---

## 🎉 Production Ready!

PreenCut is now enterprise-ready with:
- ✅ **Clean Architecture**: Service-oriented design with dependency injection
- ✅ **Professional Logging**: Structured JSON logs with performance metrics
- ✅ **Environment Configuration**: Production-ready configuration system
- ✅ **Docker Support**: Containerized deployment with health checks
- ✅ **Comprehensive Documentation**: Complete setup and migration guides
- ✅ **Backwards Compatibility**: Gradual migration path for existing code
- ✅ **Type Safety**: Full type hints throughout the codebase
- ✅ **Error Handling**: Custom exceptions with clear error messages
- ✅ **Testing Support**: Comprehensive test suite and validation

The application maintains all original AI-powered video processing capabilities while providing enterprise-grade reliability, maintainability, and scalability.

**Ready for production deployment! 🚀**
