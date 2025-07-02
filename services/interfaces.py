"""
Service interfaces for PreenCut application.
Defines contracts for business logic services.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path

from core.exceptions import PreenCutException


@dataclass
class ProcessingTask:
    """Represents a file processing task."""
    task_id: str
    files: List[str]
    llm_model: str
    prompt: Optional[str] = None
    whisper_model_size: Optional[str] = None
    status: str = "pending"
    progress: float = 0.0
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


@dataclass
class SegmentInfo:
    """Information about a video/audio segment."""
    filename: str
    start_time: float
    end_time: float
    duration: float
    summary: str
    tags: List[str]
    thumbnail_path: Optional[str] = None
    relevance_score: Optional[float] = None
    engagement_score: Optional[float] = None


class IFileValidationService(ABC):
    """Service for validating uploaded files."""
    
    @abstractmethod
    def validate_files(self, files: List[Any]) -> List[str]:
        """Validate uploaded files and return saved paths."""
        pass
    
    @abstractmethod
    def check_file_size(self, file_path: str) -> bool:
        """Check if file size is within limits."""
        pass
    
    @abstractmethod
    def check_file_format(self, file_path: str) -> bool:
        """Check if file format is supported."""
        pass


class ISpeechRecognitionService(ABC):
    """Service for speech recognition."""
    
    @abstractmethod
    def transcribe_audio(self, audio_path: str) -> Dict[str, Any]:
        """Transcribe audio to text with timestamps."""
        pass
    
    @abstractmethod
    def align_text(self, segments: List[Dict], audio_path: str, language: str) -> Dict[str, Any]:
        """Align transcribed text with audio timestamps."""
        pass


class IVideoProcessingService(ABC):
    """Service for video processing operations."""
    
    @abstractmethod
    def extract_audio(self, video_path: str, task_id: str) -> str:
        """Extract audio from video file."""
        pass
    
    @abstractmethod
    def clip_video(self, input_path: str, segments: List[Dict], output_folder: str, ext: str = '.mp4') -> List[str]:
        """Clip video into segments."""
        pass
    
    @abstractmethod
    def extract_thumbnail(self, video_path: str, timestamp: float, output_path: str) -> str:
        """Extract thumbnail from video at specific timestamp."""
        pass
    
    @abstractmethod
    def get_video_info(self, video_path: str) -> Dict:
        """Get video file information."""
        pass
    
    @abstractmethod
    def validate_video_file(self, file_path: str) -> bool:
        """Validate video file format."""
        pass


class ILLMService(ABC):
    """Service for Large Language Model operations."""
    
    @abstractmethod
    def segment_content(self, subtitles: List[Dict], prompt: Optional[str] = None) -> List[SegmentInfo]:
        """Segment content using LLM analysis."""
        pass
    
    @abstractmethod
    def extract_topic_segments(self, subtitles: List[Dict], topic: str) -> List[SegmentInfo]:
        """Extract segments related to specific topic."""
        pass
    
class ITaskManagementService(ABC):
    """Service for managing processing tasks."""
    
    @abstractmethod
    def create_task(self, files: List[str], llm_model: str, prompt: Optional[str] = None,
                   whisper_model_size: Optional[str] = None) -> str:
        """Create a new processing task."""
        pass
    
    @abstractmethod
    def get_task(self, task_id: str) -> Optional[ProcessingTask]:
        """Get task by ID."""
        pass
    
    @abstractmethod
    def update_task_progress(self, task_id: str, progress: float, status: str = None):
        """Update task progress."""
        pass
    
    @abstractmethod
    def complete_task(self, task_id: str, result: Dict[str, Any]):
        """Mark task as completed with results."""
        pass
    
    @abstractmethod
    def fail_task(self, task_id: str, error: str):
        """Mark task as failed with error message."""
        pass


class IFileProcessingService(ABC):
    """Main service for processing uploaded files."""
    
    @abstractmethod
    def process_files(self, files: List[Any], llm_model: str, prompt: Optional[str] = None,
                     whisper_model_size: Optional[str] = None) -> Tuple[str, Dict[str, Any]]:
        """Process uploaded files and return task ID and initial status."""
        pass
    
    @abstractmethod
    def reanalyze_with_prompt(self, task_id: str, llm_model: str, new_prompt: str) -> List[SegmentInfo]:
        """Reanalyze existing results with new prompt."""
        pass
    
    @abstractmethod
    def get_processing_status(self, task_id: str) -> Dict[str, Any]:
        """Get current processing status."""
        pass


class IDownloadService(ABC):
    """Service for handling file downloads."""
    
    @abstractmethod
    def create_clips_archive(self, task_id: str, selected_segments: List[Dict], 
                           download_mode: str) -> str:
        """Create archive of selected clips."""
        pass
    
class ICacheService(ABC):
    """Service for caching frequently accessed data."""
    
    @abstractmethod
    def get(self, key: str) -> Optional[Any]:
        """Get cached value."""
        pass
    
    @abstractmethod
    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """Set cached value with optional TTL."""
        pass
    
    @abstractmethod
    def delete(self, key: str):
        """Delete cached value."""
        pass
    
    @abstractmethod
    def clear(self):
        """Clear all cached values."""
        pass


class IHealthCheckService(ABC):
    """Service for health checks and monitoring."""
    
    @abstractmethod
    def check_gpu_status(self) -> Dict[str, Any]:
        """Check GPU availability and status."""
        pass
    
    @abstractmethod
    def check_ollama_connection(self) -> Dict[str, Any]:
        """Check Ollama server connection."""
        pass
    
    @abstractmethod
    def check_disk_space(self) -> Dict[str, Any]:
        """Check available disk space."""
        pass
    
    @abstractmethod
    def get_system_info(self) -> Dict[str, Any]:
        """Get general system information."""
        pass


# New service interfaces for refactored architecture
class VideoServiceInterface(ABC):
    """Interface for video processing operations."""
    
    @abstractmethod
    def extract_audio(self, video_path: str, task_id: str) -> str:
        """Extract audio from video file."""
        pass
    
    @abstractmethod
    def clip_video(self, input_path: str, segments: List[Dict], output_folder: str, ext: str = '.mp4') -> List[str]:
        """Clip video into segments."""
        pass
    
    @abstractmethod
    def extract_thumbnail(self, video_path: str, timestamp: float, output_path: str) -> str:
        """Extract thumbnail from video at timestamp."""
        pass
    
    @abstractmethod
    def get_video_info(self, video_path: str) -> Dict:
        """Get video file information."""
        pass
    
    @abstractmethod
    def validate_video_file(self, file_path: str) -> bool:
        """Validate video file format."""
        pass


class SpeechRecognitionServiceInterface(ABC):
    """Interface for speech recognition operations."""
    
    @abstractmethod
    def transcribe_audio(self, audio_path: str, language: str = None) -> Dict[str, Any]:
        """Transcribe audio file to text."""
        pass
    
    @abstractmethod
    def get_supported_languages(self) -> List[str]:
        """Get list of supported languages."""
        pass
    
    @abstractmethod
    def validate_language(self, language: str) -> bool:
        """Validate if language is supported."""
        pass
    
    @abstractmethod
    def get_recognizer_info(self) -> Dict[str, Any]:
        """Get recognizer configuration info."""
        pass


class LLMServiceInterface(ABC):
    """Interface for LLM processing operations."""
    
    @abstractmethod
    def process_transcript(self, transcript_text: str, processing_type: str = "summarize") -> str:
        """Process transcript with specified type."""
        pass
    
    @abstractmethod
    def analyze_segments(self, segments: List[Dict], analysis_type: str = "importance") -> List[Dict]:
        """Analyze video segments."""
        pass
    
    @abstractmethod
    def generate_highlights(self, transcript_data: Dict, max_highlights: int = 5) -> List[Dict]:
        """Generate highlight segments."""
        pass


class FileServiceInterface(ABC):
    """Interface for file management operations."""
    
    @abstractmethod
    def validate_upload(self, file_path: str, max_size: int = None) -> Dict[str, Any]:
        """Validate uploaded file."""
        pass
    
    @abstractmethod
    def save_uploaded_file(self, source_path: str, task_id: str, filename: str = None) -> str:
        """Save uploaded file to task directory."""
        pass
    
    @abstractmethod
    def create_task_directory(self, task_id: str = None) -> str:
        """Create task directory."""
        pass
    
    @abstractmethod
    def cleanup_task_directory(self, task_id: str, force: bool = False) -> bool:
        """Clean up task directory."""
        pass
    
    @abstractmethod
    def create_output_package(self, task_id: str, files: List[str], package_name: str = None) -> str:
        """Create output package from files."""
        pass
    
    @abstractmethod
    def get_disk_usage(self, path: str = None) -> Dict[str, Any]:
        """Get disk usage information."""
        pass
