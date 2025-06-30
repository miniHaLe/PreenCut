"""
Exception handling and error management for PreenCut application.
Provides custom exceptions, error codes, and standardized error responses.
"""

from enum import Enum
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import traceback


class ErrorCode(Enum):
    """Standardized error codes."""
    
    # General errors
    UNKNOWN_ERROR = "UNKNOWN_ERROR"
    INVALID_INPUT = "INVALID_INPUT"
    CONFIGURATION_ERROR = "CONFIGURATION_ERROR"
    
    # File handling errors
    FILE_NOT_FOUND = "FILE_NOT_FOUND"
    FILE_TOO_LARGE = "FILE_TOO_LARGE"
    INVALID_FILE_FORMAT = "INVALID_FILE_FORMAT"
    FILE_PROCESSING_ERROR = "FILE_PROCESSING_ERROR"
    
    # Model and AI errors
    MODEL_NOT_AVAILABLE = "MODEL_NOT_AVAILABLE"
    MODEL_LOADING_ERROR = "MODEL_LOADING_ERROR"
    SPEECH_RECOGNITION_ERROR = "SPEECH_RECOGNITION_ERROR"
    LLM_PROCESSING_ERROR = "LLM_PROCESSING_ERROR"
    
    # Hardware errors
    GPU_NOT_AVAILABLE = "GPU_NOT_AVAILABLE"
    INSUFFICIENT_MEMORY = "INSUFFICIENT_MEMORY"
    
    # Network errors
    OLLAMA_CONNECTION_ERROR = "OLLAMA_CONNECTION_ERROR"
    API_TIMEOUT = "API_TIMEOUT"
    
    # Business logic errors
    TASK_NOT_FOUND = "TASK_NOT_FOUND"
    INVALID_OPERATION = "INVALID_OPERATION"
    PROCESSING_QUEUE_FULL = "PROCESSING_QUEUE_FULL"


@dataclass
class ErrorDetails:
    """Detailed error information."""
    code: ErrorCode
    message: str
    details: Optional[str] = None
    suggestions: Optional[List[str]] = None
    context: Optional[Dict[str, Any]] = None


class PreenCutException(Exception):
    """Base exception for PreenCut application."""
    
    def __init__(
        self, 
        error_details: ErrorDetails, 
        cause: Optional[Exception] = None
    ):
        self.error_details = error_details
        self.cause = cause
        super().__init__(error_details.message)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for API responses."""
        return {
            'error_code': self.error_details.code.value,
            'message': self.error_details.message,
            'details': self.error_details.details,
            'suggestions': self.error_details.suggestions,
            'context': self.error_details.context,
            'caused_by': str(self.cause) if self.cause else None
        }


class FileProcessingError(PreenCutException):
    """Exception for file processing errors."""
    pass


class ModelError(PreenCutException):
    """Exception for AI model related errors."""
    pass


class ConfigurationError(PreenCutException):
    """Exception for configuration errors."""
    pass


class HardwareError(PreenCutException):
    """Exception for hardware related errors."""
    pass


class NetworkError(PreenCutException):
    """Exception for network related errors."""
    pass


class BusinessLogicError(PreenCutException):
    """Exception for business logic errors."""
    pass


# Specific exception classes for different domains
class VideoProcessingError(FileProcessingError):
    """Exception for video processing operations."""
    
    def __init__(self, message: str, error_code: ErrorCode = ErrorCode.FILE_PROCESSING_ERROR, **kwargs):
        error_details = ErrorDetails(
            code=error_code,
            message=message,
            context=kwargs
        )
        super().__init__(error_details)
        self.error_code = error_code  # Expose for compatibility


class SpeechRecognitionError(ModelError):
    """Exception for speech recognition operations."""
    
    def __init__(self, message: str, error_code: ErrorCode = ErrorCode.SPEECH_RECOGNITION_ERROR, **kwargs):
        error_details = ErrorDetails(
            code=error_code,
            message=message,
            context=kwargs
        )
        super().__init__(error_details)


class LLMProcessingError(ModelError):
    """Exception for LLM processing operations."""
    
    def __init__(self, message: str, error_code: ErrorCode = ErrorCode.LLM_PROCESSING_ERROR, **kwargs):
        error_details = ErrorDetails(
            code=error_code,
            message=message,
            context=kwargs
        )
        super().__init__(error_details)


class FileOperationError(FileProcessingError):
    """Exception for file operations."""
    
    def __init__(self, message: str, error_code: ErrorCode = ErrorCode.FILE_PROCESSING_ERROR, **kwargs):
        error_details = ErrorDetails(
            code=error_code,
            message=message,
            context=kwargs
        )
        super().__init__(error_details)


class ValidationError(PreenCutException):
    """Exception for validation errors."""
    
    def __init__(self, message: str, validation_errors: List[str] = None, **kwargs):
        context = kwargs.copy()
        context['validation_errors'] = validation_errors or []
        error_details = ErrorDetails(
            code=ErrorCode.INVALID_INPUT,
            message=message,
            context=context
        )
        super().__init__(error_details)
        self.validation_errors = validation_errors or []


class FileNotFoundError(FileProcessingError):
    """Exception for file not found errors."""
    
    def __init__(self, message: str, file_path: str = None, **kwargs):
        context = kwargs.copy()
        context['file_path'] = file_path
        error_details = ErrorDetails(
            code=ErrorCode.FILE_NOT_FOUND,
            message=message,
            context=context
        )
        super().__init__(error_details)
        self.file_path = file_path


class ErrorHandler:
    """Centralized error handling and reporting."""
    
    @staticmethod
    def create_file_not_found_error(file_path: str) -> FileProcessingError:
        """Create file not found error."""
        return FileProcessingError(
            ErrorDetails(
                code=ErrorCode.FILE_NOT_FOUND,
                message=f"File not found: {file_path}",
                details=f"The specified file '{file_path}' does not exist or is not accessible.",
                suggestions=[
                    "Check if the file path is correct",
                    "Ensure the file exists and is readable",
                    "Verify file permissions"
                ],
                context={'file_path': file_path}
            )
        )
    
    @staticmethod
    def create_file_too_large_error(file_size: int, max_size: int) -> FileProcessingError:
        """Create file too large error."""
        return FileProcessingError(
            ErrorDetails(
                code=ErrorCode.FILE_TOO_LARGE,
                message=f"File size exceeds maximum limit",
                details=f"File size is {file_size} bytes, but maximum allowed is {max_size} bytes.",
                suggestions=[
                    "Compress the file before uploading",
                    "Split large files into smaller chunks",
                    "Contact administrator to increase file size limit"
                ],
                context={'file_size': file_size, 'max_size': max_size}
            )
        )
    
    @staticmethod
    def create_invalid_file_format_error(file_extension: str, allowed: List[str]) -> FileProcessingError:
        """Create invalid file format error."""
        return FileProcessingError(
            ErrorDetails(
                code=ErrorCode.INVALID_FILE_FORMAT,
                message=f"Unsupported file format: {file_extension}",
                details=f"File extension '{file_extension}' is not supported.",
                suggestions=[
                    f"Use one of the supported formats: {', '.join(allowed)}",
                    "Convert the file to a supported format",
                    "Check if the file extension is correct"
                ],
                context={'file_extension': file_extension, 'allowed_formats': allowed}
            )
        )
    
    @staticmethod
    def create_model_loading_error(model_name: str, cause: Exception) -> ModelError:
        """Create model loading error."""
        return ModelError(
            ErrorDetails(
                code=ErrorCode.MODEL_LOADING_ERROR,
                message=f"Failed to load model: {model_name}",
                details=f"Model '{model_name}' could not be loaded: {str(cause)}",
                suggestions=[
                    "Check if the model is properly installed",
                    "Verify GPU/CPU compatibility",
                    "Check available memory",
                    "Try a smaller model size"
                ],
                context={'model_name': model_name}
            ),
            cause=cause
        )
    
    @staticmethod
    def create_gpu_not_available_error() -> HardwareError:
        """Create GPU not available error."""
        return HardwareError(
            ErrorDetails(
                code=ErrorCode.GPU_NOT_AVAILABLE,
                message="GPU is not available",
                details="CUDA is not available or no compatible GPU found.",
                suggestions=[
                    "Install CUDA drivers",
                    "Check GPU compatibility",
                    "Use CPU processing instead",
                    "Verify GPU is not being used by other processes"
                ]
            )
        )
    
    @staticmethod
    def create_ollama_connection_error(host: str, port: int, cause: Exception) -> NetworkError:
        """Create Ollama connection error."""
        return NetworkError(
            ErrorDetails(
                code=ErrorCode.OLLAMA_CONNECTION_ERROR,
                message=f"Cannot connect to Ollama server",
                details=f"Failed to connect to Ollama at {host}:{port}: {str(cause)}",
                suggestions=[
                    "Check if Ollama server is running",
                    f"Verify connection to {host}:{port}",
                    "Check firewall settings",
                    "Verify Ollama configuration"
                ],
                context={'host': host, 'port': port}
            ),
            cause=cause
        )
    
    @staticmethod
    def create_task_not_found_error(task_id: str) -> BusinessLogicError:
        """Create task not found error."""
        return BusinessLogicError(
            ErrorDetails(
                code=ErrorCode.TASK_NOT_FOUND,
                message=f"Task not found: {task_id}",
                details=f"No task found with ID '{task_id}'.",
                suggestions=[
                    "Check if the task ID is correct",
                    "Verify the task hasn't expired",
                    "Start a new processing task"
                ],
                context={'task_id': task_id}
            )
        )
    
    @staticmethod
    def create_speech_recognition_error(file_path: str, cause: Exception) -> ModelError:
        """Create speech recognition error."""
        return ModelError(
            ErrorDetails(
                code=ErrorCode.SPEECH_RECOGNITION_ERROR,
                message="Speech recognition failed",
                details=f"Failed to process audio from '{file_path}': {str(cause)}",
                suggestions=[
                    "Check if the audio file is valid",
                    "Try a different model size",
                    "Verify audio format compatibility",
                    "Check available memory"
                ],
                context={'file_path': file_path}
            ),
            cause=cause
        )
    
    @staticmethod
    def create_llm_processing_error(prompt: str, cause: Exception) -> ModelError:
        """Create LLM processing error."""
        return ModelError(
            ErrorDetails(
                code=ErrorCode.LLM_PROCESSING_ERROR,
                message="LLM processing failed",
                details=f"Failed to process prompt: {str(cause)}",
                suggestions=[
                    "Check Ollama server status",
                    "Verify model availability",
                    "Try a simpler prompt",
                    "Check network connectivity"
                ],
                context={'prompt_length': len(prompt)}
            ),
            cause=cause
        )
    
    @staticmethod
    def handle_unexpected_error(error: Exception, context: Optional[Dict[str, Any]] = None) -> PreenCutException:
        """Handle unexpected errors by wrapping them."""
        return PreenCutException(
            ErrorDetails(
                code=ErrorCode.UNKNOWN_ERROR,
                message=f"An unexpected error occurred: {type(error).__name__}",
                details=str(error),
                suggestions=[
                    "Try the operation again",
                    "Check application logs for more details",
                    "Contact support if the issue persists"
                ],
                context=context or {}
            ),
            cause=error
        )
    
    @staticmethod
    def log_error(error: PreenCutException, logger):
        """Log error with full context."""
        logger.error(
            f"Error {error.error_details.code.value}: {error.error_details.message}",
            extra={
                'error_code': error.error_details.code.value,
                'error_details': error.error_details.details,
                'error_context': error.error_details.context,
                'caused_by': str(error.cause) if error.cause else None,
                'traceback': traceback.format_exc() if error.cause else None
            }
        )


def handle_exceptions(logger_name: str = None):
    """Decorator to handle exceptions and convert them to PreenCutException."""
    from core.logging import get_logger
    import functools
    
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            logger = get_logger(logger_name or func.__module__)
            try:
                return func(*args, **kwargs)
            except PreenCutException:
                # Re-raise our custom exceptions
                raise
            except Exception as e:
                # Convert unexpected exceptions
                context = {
                    'function': func.__name__,
                    'module': func.__module__,
                    'args_count': len(args),
                    'kwargs_keys': list(kwargs.keys())
                }
                preencut_error = ErrorHandler.handle_unexpected_error(e, context)
                ErrorHandler.log_error(preencut_error, logger)
                raise preencut_error
        
        return wrapper
    return decorator
