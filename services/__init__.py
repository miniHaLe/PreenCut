"""
Services package for PreenCut application.
Contains business logic and service implementations.
"""

from .interfaces import (
    # Data classes
    ProcessingTask,
    SegmentInfo,
    SocialMediaClip,
    
    # Service interfaces
    IFileValidationService,
    ISpeechRecognitionService,
    IVideoProcessingService,
    ILLMService,
    ITaskManagementService,
    IFileProcessingService,
    IDownloadService,
    ICacheService,
    IHealthCheckService,
    
    # New service interfaces
    VideoServiceInterface,
    SpeechRecognitionServiceInterface,
    LLMServiceInterface,
    FileServiceInterface,
)

# Service implementations
from .video_service import VideoService
from .speech_recognition_service import SpeechRecognitionService
from .llm_service import LLMService
from .file_service import FileService


__all__ = [
    # Data classes
    'ProcessingTask',
    'SegmentInfo',
    'SocialMediaClip',
    
    # Service interfaces
    'IFileValidationService',
    'ISpeechRecognitionService',
    'IVideoProcessingService',
    'ILLMService',
    'ITaskManagementService',
    'IFileProcessingService',
    'IDownloadService',
    'ICacheService',
    'IHealthCheckService',
    
    # New service interfaces
    'VideoServiceInterface',
    'SpeechRecognitionServiceInterface',
    'LLMServiceInterface',
    'FileServiceInterface',
    
    # Service implementations
    'VideoService',
    'SpeechRecognitionService',
    'LLMService',
    'FileService',
]
