"""Video processing service implementation."""

import os
import subprocess
from typing import List, Dict, Optional

from core.logging import get_logger
from core.exceptions import VideoProcessingError, FileNotFoundError as CustomFileNotFoundError
from services.interfaces import VideoServiceInterface
from utils.file_utils import generate_safe_filename, ensure_directory_exists
from utils.media_utils import get_media_duration, get_media_info
from config.settings import get_settings


class VideoService(VideoServiceInterface):
    """Production-ready video processing service."""
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self.settings = get_settings()
    
    def extract_audio(self, video_path: str, task_id: str) -> str:
        """Extract audio from video with comprehensive error handling."""
        try:
            self.logger.info("Starting audio extraction", {
                "video_path": video_path,
                "task_id": task_id
            })
            
            # Validate input
            if not os.path.exists(video_path):
                raise CustomFileNotFoundError(f"Video file not found: {video_path}")
            
            # Create task temp directory
            task_temp_dir = os.path.join(self.settings.file.temp_folder, task_id)
            ensure_directory_exists(task_temp_dir)
            
            # Generate output path
            base_name = os.path.splitext(os.path.basename(video_path))[0]
            audio_path = os.path.join(task_temp_dir, f"{base_name}.wav")
            
            # Build FFmpeg command
            cmd = [
                'ffmpeg', '-i', video_path,
                '-vn', '-acodec', 'pcm_s16le', '-ar', '16000', '-ac', '1',
                '-y', audio_path
            ]
            
            # Execute command
            result = subprocess.run(
                cmd,
                check=True,
                capture_output=True,
                text=True,
                timeout=self.settings.processing_timeout
            )
            
            # Validate output
            if not os.path.exists(audio_path):
                raise VideoProcessingError("Audio extraction failed - output file not created")
            
            self.logger.info("Audio extraction completed successfully", {
                "output_path": audio_path,
                "task_id": task_id
            })
            
            return audio_path
            
        except subprocess.CalledProcessError as e:
            error_msg = f"FFmpeg audio extraction failed: {e.stderr}"
            self.logger.error(error_msg, {
                "video_path": video_path,
                "task_id": task_id,
                "stderr": e.stderr
            })
            raise VideoProcessingError(error_msg) from e
        
        except subprocess.TimeoutExpired as e:
            error_msg = f"Audio extraction timed out after {self.settings.processing_timeout}s"
            self.logger.error(error_msg, {
                "video_path": video_path,
                "task_id": task_id
            })
            raise VideoProcessingError(error_msg) from e
        
        except Exception as e:
            self.logger.error("Unexpected error during audio extraction", {
                "video_path": video_path,
                "task_id": task_id,
                "error": str(e)
            })
            raise VideoProcessingError(f"Audio extraction failed: {str(e)}") from e
    
    def clip_video(self, input_path: str, segments: List[Dict], output_folder: str,
                   ext: str = '.mp4') -> List[str]:
        """Clip videos by segments with enhanced error handling."""
        try:
            self.logger.info("Starting video clipping", {
                "input_path": input_path,
                "segments_count": len(segments),
                "output_folder": output_folder
            })
            
            # Validate input
            if not os.path.exists(input_path):
                raise CustomFileNotFoundError(f"Input video not found: {input_path}")
            
            if not segments:
                raise VideoProcessingError("No segments provided for clipping")
            
            # Ensure output directory exists
            ensure_directory_exists(output_folder)
            
            # Generate safe filename base
            base_name = os.path.splitext(os.path.basename(input_path))[0]
            safe_filename = generate_safe_filename(base_name, max_length=100)
            
            clip_list = []
            
            for i, seg in enumerate(segments):
                try:
                    # Validate segment
                    if 'start' not in seg or 'end' not in seg:
                        raise VideoProcessingError(f"Segment {i} missing start or end time")
                    
                    if seg['start'] >= seg['end']:
                        raise VideoProcessingError(f"Segment {i} has invalid time range: {seg['start']} >= {seg['end']}")
                    
                    # Generate output path
                    clip_path = os.path.join(output_folder, f"{safe_filename}_clip_{i}{ext}")
                    
                    # Build FFmpeg command
                    cmd = [
                        'ffmpeg', '-i', input_path,
                        '-ss', str(seg['start']),
                        '-to', str(seg['end']),
                        '-c:v', 'libx264',
                        '-c:a', 'copy',
                        '-avoid_negative_ts', 'make_zero',
                        '-y', clip_path
                    ]
                    
                    # Execute command
                    result = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        timeout=self.settings.processing_timeout
                    )
                    
                    if result.returncode != 0:
                        error_msg = f"FFmpeg error for segment {i}: {result.stderr}"
                        self.logger.error(error_msg, {
                            "segment": seg,
                            "clip_index": i,
                            "stderr": result.stderr
                        })
                        raise VideoProcessingError(error_msg)
                    
                    # Validate output
                    if not os.path.exists(clip_path):
                        raise VideoProcessingError(f"Clip {i} was not created successfully")
                    
                    clip_list.append(clip_path)
                    
                    self.logger.debug("Video clip created successfully", {
                        "clip_index": i,
                        "output_path": clip_path,
                        "segment": seg
                    })
                    
                except Exception as e:
                    self.logger.error(f"Failed to create clip {i}", {
                        "segment": seg,
                        "error": str(e)
                    })
                    # Continue with other clips unless it's a critical error
                    if isinstance(e, (subprocess.TimeoutExpired, VideoProcessingError)):
                        raise
                    continue
            
            self.logger.info("Video clipping completed", {
                "input_path": input_path,
                "clips_created": len(clip_list),
                "output_folder": output_folder
            })
            
            return clip_list
            
        except Exception as e:
            self.logger.error("Video clipping failed", {
                "input_path": input_path,
                "error": str(e)
            })
            if isinstance(e, VideoProcessingError):
                raise
            raise VideoProcessingError(f"Video clipping failed: {str(e)}") from e
    
    def extract_thumbnail(self, video_path: str, timestamp: float, output_path: str) -> str:
        """Extract a thumbnail from video at specified timestamp."""
        try:
            self.logger.info("Starting thumbnail extraction", {
                "video_path": video_path,
                "timestamp": timestamp,
                "output_path": output_path
            })
            
            # Validate input
            if not os.path.exists(video_path):
                raise CustomFileNotFoundError(f"Video file not found: {video_path}")
            
            if timestamp < 0:
                raise VideoProcessingError("Timestamp cannot be negative")
            
            # Ensure output directory exists
            ensure_directory_exists(os.path.dirname(output_path))
            
            # Build FFmpeg command
            cmd = [
                'ffmpeg',
                '-ss', str(timestamp),
                '-i', video_path,
                '-vframes', '1',
                '-q:v', '2',
                '-y',  # Overwrite output file
                output_path
            ]
            
            # Execute command
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.settings.processing_timeout
            )
            
            if result.returncode != 0:
                error_msg = f"FFmpeg thumbnail extraction failed: {result.stderr}"
                self.logger.error(error_msg, {
                    "video_path": video_path,
                    "timestamp": timestamp,
                    "stderr": result.stderr
                })
                raise VideoProcessingError(error_msg)
            
            # Validate output
            if not os.path.exists(output_path):
                raise VideoProcessingError("Thumbnail was not created successfully")
            
            self.logger.info("Thumbnail extraction completed successfully", {
                "output_path": output_path,
                "timestamp": timestamp
            })
            
            return output_path
            
        except subprocess.TimeoutExpired as e:
            error_msg = f"Thumbnail extraction timed out after {self.settings.processing_timeout}s"
            self.logger.error(error_msg, {
                "video_path": video_path,
                "timestamp": timestamp
            })
            raise VideoProcessingError(error_msg) from e
        
        except Exception as e:
            self.logger.error("Thumbnail extraction failed", {
                "video_path": video_path,
                "timestamp": timestamp,
                "error": str(e)
            })
            if isinstance(e, VideoProcessingError):
                raise
            raise VideoProcessingError(f"Thumbnail extraction failed: {str(e)}") from e
    
    def get_video_info(self, video_path: str) -> Dict:
        """Get comprehensive video information."""
        try:
            self.logger.info("Getting video information", {"video_path": video_path})
            
            if not os.path.exists(video_path):
                raise CustomFileNotFoundError(f"Video file not found: {video_path}")
            
            info = get_media_info(video_path)
            
            self.logger.debug("Video information retrieved", {
                "video_path": video_path,
                "duration": info.get('duration'),
                "resolution": f"{info.get('width')}x{info.get('height')}"
            })
            
            return info
            
        except Exception as e:
            self.logger.error("Failed to get video information", {
                "video_path": video_path,
                "error": str(e)
            })
            raise VideoProcessingError(f"Failed to get video info: {str(e)}") from e
    
    def validate_video_file(self, file_path: str) -> bool:
        """Validate if file is a supported video format."""
        try:
            if not os.path.exists(file_path):
                return False
            
            # Check file extension
            ext = os.path.splitext(file_path)[1].lower()
            if ext not in self.settings.allowed_extensions:
                return False
            
            # Try to get video info to validate it's a proper video file
            try:
                get_media_info(file_path)
                return True
            except Exception:
                return False
                
        except Exception as e:
            self.logger.error("Video validation failed", {
                "file_path": file_path,
                "error": str(e)
            })
            return False
