"""Speech recognition service implementation with GPU load balancing."""

import os
import time
from typing import Dict, List, Optional, Any
from abc import ABC, abstractmethod

from core.logging import get_logger
from core.exceptions import SpeechRecognitionError, FileNotFoundError as CustomFileNotFoundError, ConfigurationError
from services.interfaces import SpeechRecognitionServiceInterface
from config.settings import get_settings
from services.whisper_gpu_load_balancer import get_whisper_gpu_load_balancer


class BaseSpeechRecognizer(ABC):
    """Base class for speech recognizers with standardized interface."""
    
    def __init__(self, model_size: str, device: str, device_index: List[int], 
                 compute_type: str, batch_size: int, language: str, opts: Dict = None):
        self.logger = get_logger(__name__)
        self.model_size = model_size
        self.device = device
        self.device_index = device_index or []
        self.compute_type = compute_type
        self.batch_size = batch_size
        self.language = language
        self.opts = opts or {}
        
        self.logger.info("Speech recognizer initialized", {
            "model_size": model_size,
            "device": device,
            "language": language,
            "compute_type": compute_type
        })
    
    def validate_audio_file(self, audio_path: str) -> None:
        """Validate audio file exists and is accessible."""
        if not os.path.exists(audio_path):
            raise CustomFileNotFoundError(f"Audio file not found: {audio_path}")
        
        # Check file size
        file_size = os.path.getsize(audio_path)
        if file_size == 0:
            raise SpeechRecognitionError(f"Audio file is empty: {audio_path}")
        
        self.logger.debug("Audio file validated", {
            "audio_path": audio_path,
            "file_size": file_size
        })
    
    @abstractmethod
    def transcribe(self, audio_path: str) -> Dict[str, Any]:
        """Transcribe audio file and return structured result."""
        pass


class SpeechRecognitionService(SpeechRecognitionServiceInterface):
    """Production-ready speech recognition service with GPU load balancing."""
    
    def __init__(self, recognizer_type: str = None):
        self.logger = get_logger(__name__)
        self.settings = get_settings()
        self.recognizer_type = recognizer_type or self.settings.speech_recognizer_type
        self._recognizer = None
        self._use_gpu_load_balancer = False
        self._gpu_load_balancer = None
        self._initialize_recognizer()
    
    def _initialize_recognizer(self) -> None:
        """Initialize the appropriate speech recognizer."""
        try:
            self.logger.info("Initializing speech recognizer", {
                "recognizer_type": self.recognizer_type
            })
            
            # Check if we should use GPU load balancer
            gpu_ids = self.settings.gpu.whisper_gpu_ids
            if len(gpu_ids) > 1 and self.settings.gpu.whisper_device == "cuda":
                self._use_gpu_load_balancer = True
                self._gpu_load_balancer = get_whisper_gpu_load_balancer()
                
                self.logger.info("Using GPU load balancer for Whisper", {
                    "gpu_ids": gpu_ids,
                    "num_gpus": len(gpu_ids)
                })
            else:
                # Fallback to single GPU/CPU recognizer
                if self.recognizer_type == "faster_whisper":
                    self._recognizer = self._create_faster_whisper_recognizer()
                elif self.recognizer_type == "whisperx":
                    self._recognizer = self._create_whisperx_recognizer()
                else:
                    available_types = ["faster_whisper", "whisperx"]
                    raise ConfigurationError(
                        f"Unsupported recognizer type: {self.recognizer_type}. "
                        f"Available: {', '.join(available_types)}"
                    )
            
            self.logger.info("Speech recognizer initialized successfully", {
                "recognizer_type": self.recognizer_type,
                "model_size": self.settings.model.whisper_model_size,
                "use_gpu_load_balancer": self._use_gpu_load_balancer
            })
            
        except Exception as e:
            self.logger.error("Failed to initialize speech recognizer", {
                "recognizer_type": self.recognizer_type,
                "error": str(e)
            })
            from core.exceptions import ErrorDetails, ErrorCode
            error_details = ErrorDetails(
                code=ErrorCode.CONFIGURATION_ERROR,
                message=f"Speech recognizer initialization failed: {str(e)}",
                details={"recognizer_type": self.recognizer_type, "error": str(e)}
            )
            raise ConfigurationError(error_details) from e
    
    def _create_faster_whisper_recognizer(self) -> BaseSpeechRecognizer:
        """Create FasterWhisper recognizer instance."""
        try:
            from modules.speech_recognizers.faster_whisper_speech_recognizer import FasterWhisperSpeechRecognizer
            
            return FasterWhisperSpeechRecognizer(
                model_size=self.settings.model.whisper_model_size,
                device=self.settings.gpu.whisper_device,
                device_index=self.settings.gpu.whisper_gpu_ids,
                compute_type=self.settings.gpu.whisper_compute_type,
                batch_size=self.settings.gpu.whisper_batch_size,
                language=self.settings.model.whisper_language
            )
        except ImportError as e:
            raise ConfigurationError(f"FasterWhisper not available: {str(e)}") from e
    
    def _create_whisperx_recognizer(self) -> BaseSpeechRecognizer:
        """Create WhisperX recognizer instance."""
        try:
            from modules.speech_recognizers.whisperx_speech_recognizer import WhisperXSpeechRecognizer
            
            return WhisperXSpeechRecognizer(
                model_size=self.settings.model.whisper_model_size,
                device=self.settings.gpu.whisper_device,
                device_index=self.settings.gpu.whisper_gpu_ids,
                compute_type=self.settings.gpu.whisper_compute_type,
                batch_size=self.settings.gpu.whisper_batch_size,
                language=self.settings.model.whisper_language
            )
        except ImportError as e:
            raise ConfigurationError(f"WhisperX not available: {str(e)}") from e

    def transcribe(self, audio_path: str) -> Dict[str, Any]:
        """Transcribe audio file and return structured result."""
        return self.transcribe_audio(audio_path)

    def transcribe_audio(self, audio_path: str, language: str = None) -> Dict[str, Any]:
        """Transcribe audio file with comprehensive error handling and GPU load balancing."""
        try:
            self.logger.info("Starting audio transcription", {
                "audio_path": audio_path,
                "language": language or self.settings.model.whisper_language,
                "recognizer_type": self.recognizer_type,
                "use_gpu_load_balancer": self._use_gpu_load_balancer
            })
            
            # Use GPU load balancer if available
            if self._use_gpu_load_balancer and self._gpu_load_balancer:
                start_time = time.time()
                result = self._gpu_load_balancer.transcribe_audio(
                    audio_path, 
                    language or self.settings.model.whisper_language
                )
                processing_time = time.time() - start_time
                
                self.logger.info("GPU load balancer transcription completed", {
                    "audio_path": audio_path,
                    "processing_time": processing_time,
                    "gpu_status": self._gpu_load_balancer.get_gpu_status()
                })
                
                return result
            
            # Fallback to single recognizer
            if not self._recognizer:
                raise SpeechRecognitionError("Speech recognizer not initialized")
            
            # Validate audio file at service level
            self.validate_audio_file(audio_path)
            
            # Update language if specified
            original_language = self._recognizer.language
            if language and language != original_language:
                self._recognizer.language = language
                self.logger.debug("Language updated for transcription", {
                    "original": original_language,
                    "new": language
                })
            
            # Perform transcription
            start_time = time.time()
            result = self._recognizer.transcribe(audio_path)
            processing_time = time.time() - start_time
            
            # Restore original language
            if language and language != original_language:
                self._recognizer.language = original_language
            
            # Validate result
            if not result or not isinstance(result, dict):
                raise SpeechRecognitionError("Invalid transcription result")
            
            # Standardize result format
            standardized_result = self._standardize_result(result)
            
            self.logger.info("Audio transcription completed successfully", {
                "audio_path": audio_path,
                "processing_time": processing_time,
                "segments_count": len(standardized_result.get("segments", []))
            })
            
            return standardized_result
            
        except Exception as e:
            self.logger.error("Audio transcription failed", {
                "audio_path": audio_path,
                "error": str(e)
            })
            raise SpeechRecognitionError(f"Transcription failed: {str(e)}") from e

    def _standardize_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Standardize result format from different recognizers."""
        # This method should standardize the result format
        # For now, return as-is but could be enhanced to normalize
        # different recognizer outputs
        return result

    def get_supported_languages(self) -> List[str]:
        """Get list of supported languages for speech recognition."""
        try:
            # Common Whisper supported languages
            supported_languages = [
                "en", "es", "vi", "de", "it", "pt", "ru", "ja", "ko", "zh",
                "ar", "tr", "pl", "nl", "sv", "da", "no", "fi", "hu", "cs",
                "sk", "uk", "bg", "hr", "sl", "et", "lv", "lt", "vi", "th",
                "hi", "bn", "ta", "te", "ml", "kn", "gu", "mr", "ne", "si",
                "my", "km", "lo", "ka", "am", "sw", "zu", "af", "sq", "az",
                "be", "bs", "eu", "gl", "is", "ga", "cy", "mt", "mk", "ro",
                "sr", "he", "ur", "fa", "ps", "sd", "hy", "ka", "mn", "bo",
                "br", "fo", "ht", "la", "mi", "oc", "tt", "tk", "uz", "ky"
            ]
            
            self.logger.debug("Retrieved supported languages", {
                "count": len(supported_languages),
                "current_language": self.settings.model.whisper_language
            })
            
            return supported_languages
            
        except Exception as e:
            self.logger.error("Failed to get supported languages", {"error": str(e)})
            # Fallback to basic set
            return ["en", "es", "fr", "de", "zh", "ja", "ko"]
    
    def validate_language(self, language: str) -> bool:
        """Validate if language is supported."""
        try:
            supported = self.get_supported_languages()
            is_valid = language in supported
            
            self.logger.debug("Language validation", {
                "language": language,
                "is_valid": is_valid
            })
            
            return is_valid
            
        except Exception as e:
            self.logger.error("Language validation failed", {
                "language": language,
                "error": str(e)
            })
            return False
    
    def get_recognizer_info(self) -> Dict[str, Any]:
        """Get information about the current recognizer configuration."""
        try:
            info = {
                "recognizer_type": self.recognizer_type,
                "model_size": self.settings.model.whisper_model_size,
                "device": self.settings.gpu.whisper_device,
                "language": self.settings.model.whisper_language,
                "compute_type": self.settings.gpu.whisper_compute_type,
                "batch_size": self.settings.gpu.whisper_batch_size,
                "is_initialized": self._recognizer is not None,
                "supported_languages_count": len(self.get_supported_languages()),
                "use_gpu_load_balancer": self._use_gpu_load_balancer
            }
            
            if hasattr(self._recognizer, 'opts'):
                info["options"] = self._recognizer.opts
            
            self.logger.debug("Retrieved recognizer info", info)
            return info
            
        except Exception as e:
            self.logger.error("Failed to get recognizer info", {"error": str(e)})
            return {
                "recognizer_type": self.recognizer_type,
                "error": str(e),
                "is_initialized": False
            }
    
    def health_check(self) -> Dict[str, Any]:
        """Check if the speech recognition service is healthy."""
        try:
            self.logger.debug("Performing speech recognition health check")
            
            health_status = {
                "status": "healthy" if self._recognizer else "unhealthy",
                "recognizer_type": self.recognizer_type,
                "model_size": self.settings.model.whisper_model_size,
                "device": self.settings.gpu.whisper_device,
                "language": self.settings.model.whisper_language,
                "is_initialized": self._recognizer is not None,
                "use_gpu_load_balancer": self._use_gpu_load_balancer
            }
            
            # Additional checks
            if self._recognizer:
                try:
                    # Check if we can access supported languages
                    languages = self.get_supported_languages()
                    health_status["supported_languages_count"] = len(languages)
                    health_status["current_language_supported"] = self.settings.model.whisper_language in languages
                except Exception as e:
                    health_status["status"] = "degraded"
                    health_status["warning"] = f"Cannot access language info: {str(e)}"
            else:
                health_status["error"] = "Recognizer not initialized"
            
            self.logger.info("Speech recognition health check completed", health_status)
            return health_status
            
        except Exception as e:
            health_status = {
                "status": "unhealthy",
                "recognizer_type": self.recognizer_type,
                "error": str(e)
            }
            
            self.logger.error("Speech recognition health check failed", health_status)
            return health_status
        
    def validate_audio_file(self, audio_path: str) -> None:
        """Validate audio file exists and is accessible."""
        if not os.path.exists(audio_path):
            raise CustomFileNotFoundError(f"Audio file not found: {audio_path}")
        
        # Check file size
        file_size = os.path.getsize(audio_path)
        if file_size == 0:
            raise SpeechRecognitionError(f"Audio file is empty: {audio_path}")
        
        self.logger.debug("Audio file validated", {
            "audio_path": audio_path,
            "file_size": file_size
        })
