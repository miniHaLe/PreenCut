"""Refactored video processor using the new service architecture."""

import os
from typing import List, Dict, Optional

from core.logging import get_logger
from core.dependency_injection import get_container
from core.exceptions import VideoProcessingError, ConfigurationError
from services.interfaces import VideoServiceInterface, FileServiceInterface
from utils.time_utils import seconds_to_hhmmss, hhmmss_to_seconds


class VideoProcessorRefactored:
    """Refactored video processor using dependency injection and new architecture."""
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self.container = get_container()
        
        try:
            self.video_service = self.container.get_service(VideoServiceInterface)
            self.file_service = self.container.get_service(FileServiceInterface)
        except Exception as e:
            self.logger.error("Failed to initialize video processor services", {"error": str(e)})
            raise ConfigurationError(f"Video processor initialization failed: {str(e)}") from e
    
    def extract_audio(self, video_path: str, task_id: str) -> str:
        """Extract audio from video using the new service architecture."""
        try:
            self.logger.info("Extracting audio from video", {
                "video_path": video_path,
                "task_id": task_id
            })
            
            # Validate input file
            validation = self.file_service.validate_upload(video_path)
            if not validation["is_valid"]:
                errors = ", ".join(validation["errors"])
                raise VideoProcessingError(f"Video validation failed: {errors}")
            
            # Use video service to extract audio
            audio_path = self.video_service.extract_audio(video_path, task_id)
            
            self.logger.info("Audio extraction completed successfully", {
                "video_path": video_path,
                "audio_path": audio_path,
                "task_id": task_id
            })
            
            return audio_path
            
        except Exception as e:
            self.logger.error("Audio extraction failed", {
                "video_path": video_path,
                "task_id": task_id,
                "error": str(e)
            })
            if isinstance(e, VideoProcessingError):
                raise
            raise VideoProcessingError(f"Audio extraction failed: {str(e)}") from e
    
    def clip_video(self, input_path: str, segments: List[Dict], output_folder: str,
                   ext: str = '.mp4') -> List[str]:
        """Clip videos by segments using the new service architecture."""
        try:
            self.logger.info("Clipping video into segments", {
                "input_path": input_path,
                "segments_count": len(segments),
                "output_folder": output_folder,
                "extension": ext
            })
            
            # Validate input file
            validation = self.file_service.validate_upload(input_path)
            if not validation["is_valid"]:
                errors = ", ".join(validation["errors"])
                raise VideoProcessingError(f"Video validation failed: {errors}")
            
            # Validate segments format
            self._validate_segments(segments)
            
            # Use video service to clip video
            clip_paths = self.video_service.clip_video(input_path, segments, output_folder, ext)
            
            self.logger.info("Video clipping completed successfully", {
                "input_path": input_path,
                "clips_created": len(clip_paths),
                "output_folder": output_folder
            })
            
            return clip_paths
            
        except Exception as e:
            self.logger.error("Video clipping failed", {
                "input_path": input_path,
                "segments_count": len(segments),
                "error": str(e)
            })
            if isinstance(e, VideoProcessingError):
                raise
            raise VideoProcessingError(f"Video clipping failed: {str(e)}") from e
    
    def extract_thumbnail(self, video_path: str, timestamp: float, output_path: str) -> str:
        """Extract thumbnail using the new service architecture."""
        try:
            self.logger.info("Extracting thumbnail from video", {
                "video_path": video_path,
                "timestamp": timestamp,
                "output_path": output_path
            })
            
            # Validate input file
            validation = self.file_service.validate_upload(video_path)
            if not validation["is_valid"]:
                errors = ", ".join(validation["errors"])
                raise VideoProcessingError(f"Video validation failed: {errors}")
            
            # Use video service to extract thumbnail
            result_path = self.video_service.extract_thumbnail(video_path, timestamp, output_path)
            
            self.logger.info("Thumbnail extraction completed successfully", {
                "video_path": video_path,
                "timestamp": timestamp,
                "result_path": result_path
            })
            
            return result_path
            
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
        """Get video information using the new service architecture."""
        try:
            self.logger.info("Getting video information", {"video_path": video_path})
            
            # Validate input file
            if not self.video_service.validate_video_file(video_path):
                raise VideoProcessingError(f"Invalid or unsupported video file: {video_path}")
            
            # Get video info
            info = self.video_service.get_video_info(video_path)
            
            # Enhance with additional information
            enhanced_info = {
                **info,
                "file_size": os.path.getsize(video_path),
                "file_path": video_path,
                "duration_formatted": seconds_to_hhmmss(info.get('duration', 0))
            }
            
            self.logger.debug("Video information retrieved", {
                "video_path": video_path,
                "duration": info.get('duration'),
                "resolution": f"{info.get('width')}x{info.get('height')}"
            })
            
            return enhanced_info
            
        except Exception as e:
            self.logger.error("Failed to get video information", {
                "video_path": video_path,
                "error": str(e)
            })
            if isinstance(e, VideoProcessingError):
                raise
            raise VideoProcessingError(f"Video info retrieval failed: {str(e)}") from e
    
    def validate_segments_timing(self, segments: List[Dict], video_duration: float = None) -> List[Dict]:
        """Validate and correct segment timing."""
        try:
            self.logger.info("Validating segment timing", {
                "segments_count": len(segments),
                "video_duration": video_duration
            })
            
            validated_segments = []
            
            for i, segment in enumerate(segments):
                validated_segment = segment.copy()
                
                # Convert time formats if needed
                start = segment.get('start', 0)
                end = segment.get('end', 0)
                
                # Handle string time formats
                if isinstance(start, str):
                    start = hhmmss_to_seconds(start)
                if isinstance(end, str):
                    end = hhmmss_to_seconds(end)
                
                # Validate timing
                start = max(0, float(start))
                end = max(start + 0.1, float(end))  # Minimum 0.1 second duration
                
                # Clamp to video duration if provided
                if video_duration:
                    start = min(start, video_duration - 0.1)
                    end = min(end, video_duration)
                
                validated_segment.update({
                    'start': start,
                    'end': end,
                    'duration': end - start,
                    'start_formatted': seconds_to_hhmmss(start),
                    'end_formatted': seconds_to_hhmmss(end)
                })
                
                validated_segments.append(validated_segment)
            
            self.logger.info("Segment timing validation completed", {
                "validated_segments": len(validated_segments)
            })
            
            return validated_segments
            
        except Exception as e:
            self.logger.error("Segment timing validation failed", {
                "segments_count": len(segments),
                "error": str(e)
            })
            raise VideoProcessingError(f"Segment validation failed: {str(e)}") from e
    
    def _validate_segments(self, segments: List[Dict]) -> None:
        """Validate segment format and content."""
        if not segments:
            raise VideoProcessingError("No segments provided")
        
        for i, segment in enumerate(segments):
            if not isinstance(segment, dict):
                raise VideoProcessingError(f"Segment {i} must be a dictionary")
            
            if 'start' not in segment or 'end' not in segment:
                raise VideoProcessingError(f"Segment {i} missing required 'start' or 'end' fields")
            
            try:
                start = float(segment['start']) if not isinstance(segment['start'], str) else hhmmss_to_seconds(segment['start'])
                end = float(segment['end']) if not isinstance(segment['end'], str) else hhmmss_to_seconds(segment['end'])
                
                if start < 0 or end < 0:
                    raise VideoProcessingError(f"Segment {i} has negative timestamps")
                
                if start >= end:
                    raise VideoProcessingError(f"Segment {i} has invalid time range: {start} >= {end}")
                    
            except (ValueError, TypeError) as e:
                raise VideoProcessingError(f"Segment {i} has invalid timestamp format: {str(e)}")
    
    def create_video_package(self, clips: List[str], task_id: str, package_name: str = None) -> str:
        """Create a package of video clips."""
        try:
            self.logger.info("Creating video package", {
                "clips_count": len(clips),
                "task_id": task_id,
                "package_name": package_name
            })
            
            if not clips:
                raise VideoProcessingError("No clips provided for packaging")
            
            # Validate all clips exist
            missing_clips = [clip for clip in clips if not os.path.exists(clip)]
            if missing_clips:
                raise VideoProcessingError(f"Missing clips: {missing_clips}")
            
            # Create package using file service
            package_path = self.file_service.create_output_package(
                task_id=task_id,
                files=clips,
                package_name=package_name or f"video_clips_{task_id}.zip"
            )
            
            self.logger.info("Video package created successfully", {
                "package_path": package_path,
                "clips_count": len(clips)
            })
            
            return package_path
            
        except Exception as e:
            self.logger.error("Failed to create video package", {
                "clips_count": len(clips),
                "task_id": task_id,
                "error": str(e)
            })
            if isinstance(e, VideoProcessingError):
                raise
            raise VideoProcessingError(f"Video package creation failed: {str(e)}") from e
    
    def health_check(self) -> Dict:
        """Perform health check on video processing capabilities."""
        try:
            health_status = {
                "status": "healthy",
                "video_service": "available",
                "file_service": "available",
                "dependencies": []
            }
            
            # Check video service
            try:
                video_health = self.video_service.health_check() if hasattr(self.video_service, 'health_check') else {"status": "unknown"}
                health_status["video_service_health"] = video_health
            except Exception as e:
                health_status["video_service"] = f"error: {str(e)}"
                health_status["status"] = "degraded"
            
            # Check file service
            try:
                file_health = self.file_service.health_check() if hasattr(self.file_service, 'health_check') else {"status": "unknown"}
                health_status["file_service_health"] = file_health
            except Exception as e:
                health_status["file_service"] = f"error: {str(e)}"
                health_status["status"] = "degraded"
            
            # Check ffmpeg availability
            try:
                import subprocess
                result = subprocess.run(['ffmpeg', '-version'], capture_output=True, timeout=5)
                health_status["dependencies"].append({
                    "name": "ffmpeg",
                    "status": "available" if result.returncode == 0 else "error",
                    "version": result.stdout.decode().split('\n')[0] if result.returncode == 0 else None
                })
            except Exception as e:
                health_status["dependencies"].append({
                    "name": "ffmpeg", 
                    "status": "error",
                    "error": str(e)
                })
                health_status["status"] = "unhealthy"
            
            self.logger.debug("Video processor health check completed", health_status)
            return health_status
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }
