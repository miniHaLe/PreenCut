"""
Configuration management for PreenCut application.
Handles environment variables, validation, and provides centralized config access.
"""

import os
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
import threading

import torch


class Environment(Enum):
    """Application environment types."""
    DEVELOPMENT = "development"
    PRODUCTION = "production"
    TESTING = "testing"


class LogLevel(Enum):
    """Logging levels."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


@dataclass
class DatabaseConfig:
    """Database configuration (if needed in future)."""
    url: Optional[str] = None
    pool_size: int = 5
    max_overflow: int = 10


@dataclass
class SecurityConfig:
    """Security configuration."""
    secret_key: str = "dev-secret-key"
    cors_origins: List[str] = field(default_factory=lambda: ["*"])
    rate_limit_enabled: bool = False
    rate_limit_per_minute: int = 60


@dataclass
class PerformanceConfig:
    """Performance optimization configuration."""
    enable_caching: bool = True
    cache_ttl: int = 3600
    worker_processes: int = 1
    processing_timeout: int = 300  # 5 minutes default
    llm_timeout: int = 60  # 1 minute default


@dataclass
class GPUConfig:
    """GPU and hardware configuration."""
    device_type: str = "cpu"
    available_gpus: List[int] = field(default_factory=list)
    whisper_device: str = "cpu"
    whisper_gpu_ids: List[int] = field(default_factory=list)
    whisper_compute_type: str = "float32"
    whisper_batch_size: int = 16


@dataclass
class ModelConfig:
    """AI Model configuration."""
    whisper_model_size: str = "large-v3"
    speech_recognizer_type: str = "whisperx"
    whisper_language: str = "vi"
    whisper_auto_detect_language: bool = False
    enable_alignment: bool = True
    alignment_model: str = "whisperx"  # Model used for text alignment
    faster_whisper_beam_size: int = 10


@dataclass
class OllamaConfig:
    """Ollama LLM configuration."""
    host: str = "localhost"
    port: int = 11434
    timeout: int = 120
    keep_alive: str = "1m"
    default_model: str = "llama3.1:latest"
    
    @property
    def base_url(self) -> str:
        """Get the base URL for Ollama API."""
        return f"http://{self.host}:{self.port}"


@dataclass
class FileConfig:
    """File processing configuration."""
    allowed_extensions: List[str] = field(default_factory=lambda: [
        '.mp4', '.avi', '.mov', '.mkv', '.ts', '.mxf', '.mp3', '.wav', '.flac'
    ])
    max_file_size: int = 10 * 1024 * 1024 * 1024  # 10GB
    max_file_numbers: int = 10
    temp_folder: str = "./temp"
    output_folder: str = "./output"


@dataclass
class ApplicationConfig:
    """Main application configuration."""
    name: str = "PreenCut"
    version: str = "1.0.0"
    environment: Environment = Environment.DEVELOPMENT
    debug: bool = True
    host: str = "0.0.0.0"
    port: int = 8860
    log_level: LogLevel = LogLevel.INFO
    log_format: str = "json"
    log_file: str = "logs/app.log"
    
    # Sub-configurations
    security: SecurityConfig = field(default_factory=SecurityConfig)
    performance: PerformanceConfig = field(default_factory=PerformanceConfig)
    gpu: GPUConfig = field(default_factory=GPUConfig)
    model: ModelConfig = field(default_factory=ModelConfig)
    ollama: OllamaConfig = field(default_factory=OllamaConfig)
    file: FileConfig = field(default_factory=FileConfig)
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    
    # Convenience properties for backward compatibility and ease of access
    @property
    def temp_folder(self) -> str:
        """Get temp folder path."""
        return self.file.temp_folder
    
    @property
    def output_folder(self) -> str:
        """Get output folder path."""
        return self.file.output_folder
    
    @property
    def allowed_extensions(self) -> List[str]:
        """Get allowed file extensions."""
        return self.file.allowed_extensions
    
    @property
    def max_file_size(self) -> int:
        """Get maximum file size."""
        return self.file.max_file_size
    
    @property
    def speech_recognizer_type(self) -> str:
        """Get speech recognizer type."""
        return self.model.speech_recognizer_type
    
    @property
    def whisper_model_size(self) -> str:
        """Get Whisper model size."""
        return self.model.whisper_model_size
    
    @property
    def language(self) -> str:
        """Get default language."""
        return self.model.whisper_language
    
    @property
    def device(self) -> str:
        """Get device type."""
        return self.gpu.device_type
    
    @property
    def device_index(self) -> List[int]:
        """Get device indices."""
        return self.gpu.whisper_gpu_ids
    
    @property
    def compute_type(self) -> str:
        """Get compute type."""
        return self.gpu.whisper_compute_type
    
    @property
    def batch_size(self) -> int:
        """Get batch size."""
        return self.gpu.whisper_batch_size
    
    @property
    def processing_timeout(self) -> int:
        """Get processing timeout."""
        return self.performance.processing_timeout
    
    @property
    def llm_timeout(self) -> int:
        """Get LLM timeout."""
        return self.performance.llm_timeout
    
    @property
    def llm_model_options(self) -> List[Dict]:
        """Get LLM model options."""
        return get_llm_model_options()


class ConfigManager:
    """Centralized configuration manager."""
    
    def __init__(self, env_file: Optional[str] = None):
        """Initialize configuration manager."""
        self._config: Optional[ApplicationConfig] = None
        self._env_file = env_file or ".env"
        self._load_environment()
        
    def _load_environment(self) -> None:
        """Load environment variables from .env file if it exists."""
        env_path = Path(self._env_file)
        if env_path.exists():
            try:
                with open(env_path) as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            key, value = line.split('=', 1)
                            os.environ.setdefault(key.strip(), value.strip())
            except Exception as e:
                logging.warning(f"Failed to load environment file {env_path}: {e}")
    
    def _get_env_bool(self, key: str, default: bool = False) -> bool:
        """Get boolean environment variable."""
        value = os.getenv(key, str(default)).lower()
        return value in ('true', '1', 'yes', 'on')
    
    def _get_env_int(self, key: str, default: int = 0) -> int:
        """Get integer environment variable."""
        try:
            return int(os.getenv(key, str(default)))
        except ValueError:
            return default
    
    def _get_env_list(self, key: str, default: List[str] = None) -> List[str]:
        """Get list environment variable."""
        if default is None:
            default = []
        value = os.getenv(key, '')
        if not value:
            return default
        return [item.strip() for item in value.split(',') if item.strip()]
    
    def _get_gpu_config(self) -> GPUConfig:
        """Configure GPU settings."""
        # Check CUDA availability
        device_type = "cpu"
        available_gpus = []
        
        if torch.cuda.is_available():
            available_gpus = list(range(torch.cuda.device_count()))
            device_type = "cuda"
        
        # Check environment variables
        cuda_visible = os.getenv('CUDA_VISIBLE_DEVICES', '')
        if cuda_visible:
            try:
                selected_gpus = [int(x.strip()) for x in cuda_visible.split(',') if x.strip()]
                return GPUConfig(
                    device_type="cuda",
                    available_gpus=available_gpus,
                    whisper_device="cuda",
                    whisper_gpu_ids=selected_gpus,
                    whisper_compute_type=os.getenv('WHISPER_COMPUTE_TYPE', 'float16'),
                    whisper_batch_size=self._get_env_int('WHISPER_BATCH_SIZE', 16)
                )
            except ValueError:
                pass
        
        # Default GPU configuration
        if available_gpus:
            restricted_gpus = [gpu for gpu in available_gpus if gpu < 1]  # Only use GPU 0
            return GPUConfig(
                device_type="cuda",
                available_gpus=available_gpus,
                whisper_device="cuda",
                whisper_gpu_ids=restricted_gpus,
                whisper_compute_type=os.getenv('WHISPER_COMPUTE_TYPE', 'float16'),
                whisper_batch_size=self._get_env_int('WHISPER_BATCH_SIZE', 16)
            )
        
        return GPUConfig(
            device_type="cpu",
            available_gpus=[],
            whisper_device="cpu",
            whisper_gpu_ids=[],
            whisper_compute_type=os.getenv('WHISPER_COMPUTE_TYPE', 'float32'),
            whisper_batch_size=self._get_env_int('WHISPER_BATCH_SIZE', 16)
        )
    
    def _create_directories(self) -> None:
        """Create necessary directories."""
        directories = [
            self._config.file.temp_folder,
            self._config.file.output_folder,
            "logs",
            os.path.join(self._config.file.temp_folder, "thumbnails"),
        ]
        
        for directory in directories:
            Path(directory).mkdir(parents=True, exist_ok=True)
    
    @property
    def config(self) -> ApplicationConfig:
        """Get the application configuration."""
        if self._config is None:
            self._config = self._build_config()
            self._create_directories()
        return self._config
    
    def _build_config(self) -> ApplicationConfig:
        """Build configuration from environment variables."""
        # GPU configuration
        gpu_config = self._get_gpu_config()
        
        # Security configuration
        security_config = SecurityConfig(
            secret_key=os.getenv('SECRET_KEY', 'dev-secret-key'),
            cors_origins=self._get_env_list('CORS_ORIGINS', ['*']),
            rate_limit_enabled=self._get_env_bool('RATE_LIMIT_ENABLED', False),
            rate_limit_per_minute=self._get_env_int('RATE_LIMIT_PER_MINUTE', 60)
        )
        
        # Performance configuration
        performance_config = PerformanceConfig(
            enable_caching=self._get_env_bool('ENABLE_CACHING', True),
            cache_ttl=self._get_env_int('CACHE_TTL', 3600),
            worker_processes=self._get_env_int('WORKER_PROCESSES', 1)
        )
        
        # Model configuration
        model_config = ModelConfig(
            whisper_model_size=os.getenv('WHISPER_MODEL_SIZE', 'large-v3'),
            speech_recognizer_type=os.getenv('SPEECH_RECOGNIZER_TYPE', 'whisperx'),
            whisper_language=os.getenv('WHISPER_LANGUAGE', 'vi'),
            whisper_auto_detect_language=self._get_env_bool('WHISPER_AUTO_DETECT_LANGUAGE', False),
            enable_alignment=self._get_env_bool('ENABLE_ALIGNMENT', True),
            faster_whisper_beam_size=self._get_env_int('FASTER_WHISPER_BEAM_SIZE', 10)
        )
        
        # Ollama configuration
        ollama_config = OllamaConfig(
            host=os.getenv('OLLAMA_HOST', 'localhost'),
            port=self._get_env_int('OLLAMA_PORT', 11434),
            timeout=self._get_env_int('OLLAMA_TIMEOUT', 120),
            keep_alive=os.getenv('OLLAMA_KEEP_ALIVE', '1m'),
            default_model=os.getenv('OLLAMA_DEFAULT_MODEL', 'llama3.1:latest')
        )
        
        # File configuration
        file_config = FileConfig(
            max_file_size=self._get_env_int('MAX_FILE_SIZE', 10 * 1024 * 1024 * 1024),
            max_file_numbers=self._get_env_int('MAX_FILE_NUMBERS', 10),
            temp_folder=os.getenv('TEMP_FOLDER', './temp'),
            output_folder=os.getenv('OUTPUT_FOLDER', './output')
        )
        
        # Environment handling
        env_str = os.getenv('APP_ENV', 'development').lower()
        try:
            environment = Environment(env_str)
        except ValueError:
            environment = Environment.DEVELOPMENT
        
        # Log level handling
        log_level_str = os.getenv('LOG_LEVEL', 'INFO').upper()
        try:
            log_level = LogLevel(log_level_str)
        except ValueError:
            log_level = LogLevel.INFO
        
        return ApplicationConfig(
            name=os.getenv('APP_NAME', 'PreenCut'),
            version=os.getenv('APP_VERSION', '1.0.0'),
            environment=environment,
            debug=self._get_env_bool('DEBUG', True),
            host=os.getenv('HOST', '0.0.0.0'),
            port=self._get_env_int('PORT', 8860),
            log_level=log_level,
            log_format=os.getenv('LOG_FORMAT', 'json'),
            log_file=os.getenv('LOG_FILE', 'logs/app.log'),
            security=security_config,
            performance=performance_config,
            gpu=gpu_config,
            model=model_config,
            ollama=ollama_config,
            file=file_config
        )
    
    def get_llm_model_options(self) -> List[Dict[str, Any]]:
        """Get LLM model options."""
        return [
            {
                "model": self.config.ollama.default_model,
                "base_url": self.config.ollama.base_url,
                "label": "llama3.1",
                "max_tokens": 4096,
                "temperature": 0.6,
                "supports_structured_output": True,
            }
        ]
    
    def validate_config(self) -> List[str]:
        """Validate configuration and return any errors."""
        errors = []
        
        # Check required directories
        if not os.path.exists(self.config.file.temp_folder):
            errors.append(f"Temp folder does not exist: {self.config.file.temp_folder}")
        
        if not os.path.exists(self.config.file.output_folder):
            errors.append(f"Output folder does not exist: {self.config.file.output_folder}")
        
        # Check GPU configuration
        if self.config.gpu.whisper_device == "cuda" and not torch.cuda.is_available():
            errors.append("CUDA is not available but GPU device is specified")
        
        # Check file size limits
        if self.config.file.max_file_size <= 0:
            errors.append("Max file size must be positive")
        
        if self.config.file.max_file_numbers <= 0:
            errors.append("Max file numbers must be positive")
        
        return errors


# Global configuration instance
_config_manager = ConfigManager()


def get_config() -> ApplicationConfig:
    """Get the global application configuration."""
    return _config_manager.config


def get_llm_model_options() -> List[Dict[str, Any]]:
    """Get LLM model options."""
    return _config_manager.get_llm_model_options()


def validate_config() -> List[str]:
    """Validate the configuration."""
    return _config_manager.validate_config()


# Set Gradio temp directory
os.environ['GRADIO_TEMP_DIR'] = os.path.join(get_config().file.temp_folder, 'gradio')


# Legacy compatibility - gradually replace these with get_config() calls
config = get_config()

# Backwards compatibility exports
ALLOWED_EXTENSIONS = config.file.allowed_extensions
MAX_FILE_SIZE = config.file.max_file_size
MAX_FILE_NUMBERS = config.file.max_file_numbers
TEMP_FOLDER = config.file.temp_folder
OUTPUT_FOLDER = config.file.output_folder

SPEECH_RECOGNIZER_TYPE = config.model.speech_recognizer_type
WHISPER_MODEL_SIZE = config.model.whisper_model_size
WHISPER_DEVICE = config.gpu.whisper_device
WHISPER_GPU_IDS = config.gpu.whisper_gpu_ids
WHISPER_COMPUTE_TYPE = config.gpu.whisper_compute_type
WHISPER_BATCH_SIZE = config.gpu.whisper_batch_size
WHISPER_LANGUAGE = config.model.whisper_language
WHISPER_AUTO_DETECT_LANGUAGE = config.model.whisper_auto_detect_language
FASTER_WHISPER_BEAM_SIZE = config.model.faster_whisper_beam_size
ENABLE_ALIGNMENT = config.model.enable_alignment
ALIGNMENT_MODEL = config.model.alignment_model

LLM_MODEL_OPTIONS = get_llm_model_options()
OLLAMA_DEFAULT_HOST = config.ollama.host
OLLAMA_DEFAULT_PORT = config.ollama.port
OLLAMA_TIMEOUT = config.ollama.timeout
OLLAMA_KEEP_ALIVE = config.ollama.keep_alive


def get_ollama_url(host=None, port=None):
    """Generate Ollama API base URL."""
    host = host or config.ollama.host
    port = port or config.ollama.port
    return f"http://{host}:{port}"


def check_ollama_model_availability():
    """Check which models are actually available in your Ollama installation."""
    import requests
    try:
        url = get_ollama_url()
        response = requests.get(f"{url}/api/tags", timeout=5)
        if response.status_code == 200:
            models = response.json().get("models", [])
            available_models = [model["name"] for model in models]
            print(f"Available Ollama models: {available_models}")
            return available_models
        else:
            print(f"Failed to connect to Ollama: HTTP {response.status_code}")
            return []
    except Exception as e:
        print(f"Error checking Ollama models: {e}")
        return []


# Global settings instance cache
_settings_instance: Optional[ApplicationConfig] = None
_settings_lock = threading.Lock()


def get_settings() -> ApplicationConfig:
    """Get the global application settings instance."""
    global _settings_instance
    
    if _settings_instance is None:
        with _settings_lock:
            if _settings_instance is None:
                _settings_instance = get_config()
    
    return _settings_instance


def reload_settings() -> ApplicationConfig:
    """Reload settings from environment (useful for testing)."""
    global _settings_instance
    
    with _settings_lock:
        _settings_instance = None
        return get_settings()


# Import threading for the lock
import threading
