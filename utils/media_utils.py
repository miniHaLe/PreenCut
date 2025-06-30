"""
Media processing utilities for PreenCut application.
Handles audio/video format detection, conversion, and validation.
"""

import subprocess
import json
import os
from pathlib import Path
from typing import Dict, Any, Optional, List

from core.logging import get_logger
from core.exceptions import handle_exceptions, ErrorHandler


logger = get_logger(__name__)


@handle_exceptions('media_utils')
def get_media_info(file_path: str) -> Dict[str, Any]:
    """
    Get comprehensive media file information using ffprobe.
    
    Args:
        file_path: Path to media file
        
    Returns:
        Dictionary containing media information
    """
    if not os.path.exists(file_path):
        raise ErrorHandler.create_file_not_found_error(file_path)
    
    cmd = [
        "ffprobe",
        "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        file_path
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        info = json.loads(result.stdout)
        
        # Extract useful information
        media_info = {
            'filepath': file_path,
            'filename': os.path.basename(file_path),
            'format': info.get('format', {}),
            'streams': info.get('streams', []),
            'has_video': False,
            'has_audio': False,
            'duration': 0.0,
            'size_bytes': 0,
            'video_info': None,
            'audio_info': None
        }
        
        # Parse format info
        format_info = media_info['format']
        media_info['duration'] = float(format_info.get('duration', 0))
        media_info['size_bytes'] = int(format_info.get('size', 0))
        
        # Parse streams
        for stream in media_info['streams']:
            codec_type = stream.get('codec_type', '')
            
            if codec_type == 'video':
                media_info['has_video'] = True
                media_info['video_info'] = {
                    'codec': stream.get('codec_name'),
                    'width': stream.get('width'),
                    'height': stream.get('height'),
                    'fps': eval(stream.get('r_frame_rate', '0/1')),
                    'bit_rate': stream.get('bit_rate'),
                    'pixel_format': stream.get('pix_fmt')
                }
            
            elif codec_type == 'audio':
                media_info['has_audio'] = True
                media_info['audio_info'] = {
                    'codec': stream.get('codec_name'),
                    'sample_rate': stream.get('sample_rate'),
                    'channels': stream.get('channels'),
                    'bit_rate': stream.get('bit_rate'),
                    'channel_layout': stream.get('channel_layout')
                }
        
        return media_info
        
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to get media info for {file_path}: {e}")
        raise ErrorHandler.create_file_processing_error(file_path, e)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse ffprobe output for {file_path}: {e}")
        raise ErrorHandler.create_file_processing_error(file_path, e)


@handle_exceptions('media_utils')
def get_audio_codec(file_path: str) -> str:
    """
    Get audio codec information using ffprobe.
    
    Args:
        file_path: Path to media file
        
    Returns:
        Audio codec name
    """
    media_info = get_media_info(file_path)
    
    if not media_info['has_audio']:
        raise ValueError(f"No audio stream found in {file_path}")
    
    return media_info['audio_info']['codec']


@handle_exceptions('media_utils')
def is_video_file(file_path: str) -> bool:
    """
    Check if file is a video file.
    
    Args:
        file_path: Path to file
        
    Returns:
        True if file contains video stream
    """
    try:
        media_info = get_media_info(file_path)
        return media_info['has_video']
    except Exception:
        # If we can't get media info, fall back to extension check
        video_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.ts', '.mxf', '.webm', '.flv'}
        return Path(file_path).suffix.lower() in video_extensions


@handle_exceptions('media_utils')
def is_audio_file(file_path: str) -> bool:
    """
    Check if file is an audio file.
    
    Args:
        file_path: Path to file
        
    Returns:
        True if file contains audio stream
    """
    try:
        media_info = get_media_info(file_path)
        return media_info['has_audio']
    except Exception:
        # If we can't get media info, fall back to extension check
        audio_extensions = {'.mp3', '.wav', '.flac', '.aac', '.ogg', '.m4a'}
        return Path(file_path).suffix.lower() in audio_extensions


@handle_exceptions('media_utils')
def validate_media_file(file_path: str) -> Dict[str, Any]:
    """
    Validate media file and return validation results.
    
    Args:
        file_path: Path to media file
        
    Returns:
        Dictionary with validation results
    """
    validation_result = {
        'valid': False,
        'has_audio': False,
        'has_video': False,
        'duration': 0.0,
        'issues': [],
        'warnings': []
    }
    
    try:
        media_info = get_media_info(file_path)
        
        validation_result['has_audio'] = media_info['has_audio']
        validation_result['has_video'] = media_info['has_video']
        validation_result['duration'] = media_info['duration']
        
        # Check for issues
        if not media_info['has_audio'] and not media_info['has_video']:
            validation_result['issues'].append("File contains no audio or video streams")
        
        if media_info['duration'] <= 0:
            validation_result['issues'].append("File has no duration or invalid duration")
        
        if media_info['duration'] > 7200:  # 2 hours
            validation_result['warnings'].append("File is very long (>2 hours), processing may take time")
        
        # Audio-specific checks
        if media_info['has_audio']:
            audio_info = media_info['audio_info']
            sample_rate = int(audio_info.get('sample_rate', 0))
            
            if sample_rate < 8000:
                validation_result['warnings'].append("Low audio sample rate may affect transcription quality")
            
            if sample_rate > 48000:
                validation_result['warnings'].append("High audio sample rate may slow processing")
        
        # Video-specific checks
        if media_info['has_video']:
            video_info = media_info['video_info']
            
            if video_info.get('width', 0) > 1920 or video_info.get('height', 0) > 1080:
                validation_result['warnings'].append("High resolution video may slow processing")
        
        validation_result['valid'] = len(validation_result['issues']) == 0
        
    except Exception as e:
        validation_result['issues'].append(f"Failed to analyze file: {str(e)}")
    
    return validation_result


@handle_exceptions('media_utils')
def estimate_audio_quality(file_path: str) -> Dict[str, Any]:
    """
    Estimate audio quality for transcription.
    
    Args:
        file_path: Path to audio/video file
        
    Returns:
        Dictionary with quality assessment
    """
    quality_info = {
        'score': 0.0,  # 0-1 scale
        'factors': [],
        'recommendations': []
    }
    
    try:
        media_info = get_media_info(file_path)
        
        if not media_info['has_audio']:
            quality_info['factors'].append("No audio stream")
            return quality_info
        
        audio_info = media_info['audio_info']
        sample_rate = int(audio_info.get('sample_rate', 0))
        channels = int(audio_info.get('channels', 0))
        bit_rate = audio_info.get('bit_rate')
        
        score = 0.5  # Base score
        
        # Sample rate factor
        if sample_rate >= 44100:
            score += 0.2
            quality_info['factors'].append("Good sample rate")
        elif sample_rate >= 22050:
            score += 0.1
            quality_info['factors'].append("Adequate sample rate")
        else:
            score -= 0.1
            quality_info['factors'].append("Low sample rate")
            quality_info['recommendations'].append("Consider using higher sample rate audio")
        
        # Channel factor
        if channels >= 2:
            score += 0.1
            quality_info['factors'].append("Stereo/multi-channel audio")
        else:
            quality_info['factors'].append("Mono audio")
        
        # Bit rate factor (if available)
        if bit_rate:
            bit_rate_kbps = int(bit_rate) // 1000
            if bit_rate_kbps >= 128:
                score += 0.1
                quality_info['factors'].append("Good bit rate")
            elif bit_rate_kbps >= 64:
                quality_info['factors'].append("Adequate bit rate")
            else:
                score -= 0.1
                quality_info['factors'].append("Low bit rate")
                quality_info['recommendations'].append("Consider using higher bit rate")
        
        # Codec factor
        codec = audio_info.get('codec', '').lower()
        if codec in ['flac', 'wav', 'pcm']:
            score += 0.1
            quality_info['factors'].append("Lossless audio codec")
        elif codec in ['mp3', 'aac']:
            quality_info['factors'].append("Compressed audio codec")
        
        quality_info['score'] = max(0.0, min(1.0, score))
        
    except Exception as e:
        logger.warning(f"Failed to estimate audio quality for {file_path}: {e}")
        quality_info['factors'].append("Unable to analyze audio quality")
    
    return quality_info


@handle_exceptions('media_utils')
def convert_to_wav(input_path: str, output_path: str, sample_rate: int = 16000) -> str:
    """
    Convert media file to WAV format for processing.
    
    Args:
        input_path: Path to input media file
        output_path: Path for output WAV file
        sample_rate: Target sample rate
        
    Returns:
        Path to converted WAV file
    """
    if not os.path.exists(input_path):
        raise ErrorHandler.create_file_not_found_error(input_path)
    
    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    cmd = [
        'ffmpeg',
        '-i', input_path,
        '-vn',  # No video
        '-acodec', 'pcm_s16le',  # 16-bit PCM
        '-ar', str(sample_rate),  # Sample rate
        '-ac', '1',  # Mono
        '-y',  # Overwrite output
        output_path
    ]
    
    try:
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True, 
            check=True
        )
        
        logger.info(f"Converted {input_path} to WAV: {output_path}")
        return output_path
        
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to convert {input_path} to WAV: {e}")
        logger.error(f"FFmpeg stderr: {e.stderr}")
        raise ErrorHandler.create_file_processing_error(input_path, e)


@handle_exceptions('media_utils')
def extract_audio_segment(input_path: str, output_path: str, start_time: float, 
                         duration: float, format: str = 'wav') -> str:
    """
    Extract audio segment from media file.
    
    Args:
        input_path: Path to input media file
        output_path: Path for output file
        start_time: Start time in seconds
        duration: Duration in seconds
        format: Output format ('wav', 'mp3', etc.)
        
    Returns:
        Path to extracted segment
    """
    if not os.path.exists(input_path):
        raise ErrorHandler.create_file_not_found_error(input_path)
    
    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    cmd = [
        'ffmpeg',
        '-i', input_path,
        '-ss', str(start_time),
        '-t', str(duration),
        '-vn',  # No video
        '-y',  # Overwrite output
        output_path
    ]
    
    try:
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True, 
            check=True
        )
        
        logger.info(f"Extracted audio segment: {output_path}")
        return output_path
        
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to extract audio segment: {e}")
        raise ErrorHandler.create_file_processing_error(input_path, e)


@handle_exceptions('media_utils')
def get_media_duration(file_path: str) -> float:
    """
    Get media file duration in seconds.
    
    Args:
        file_path: Path to media file
        
    Returns:
        Duration in seconds
    """
    media_info = get_media_info(file_path)
    return media_info['duration']


@handle_exceptions('media_utils')
def check_ffmpeg_availability() -> bool:
    """
    Check if FFmpeg is available on the system.
    
    Returns:
        True if FFmpeg is available
    """
    try:
        result = subprocess.run(
            ['ffmpeg', '-version'], 
            capture_output=True, 
            check=True
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False
