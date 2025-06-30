"""
Utility package for PreenCut application.
Provides common utilities for file handling, time formatting, and media processing.
"""

# Import legacy utilities for backwards compatibility
from .file_utils import (
    generate_safe_filename,
    clear_directory_fast,
    ensure_directory_exists,
    get_file_hash,
    get_file_size_mb,
    validate_file_extension,
    create_unique_filename,
    copy_file_safely,
    move_file_safely,
    cleanup_old_files,
    get_directory_size,
    create_temp_directory
)

from .time_utils import (
    seconds_to_hhmmss,
    seconds_to_mmss,
    hhmmss_to_seconds,
    validate_time_format,
    format_duration,
    parse_duration_string,
    time_range_overlap,
    time_ranges_merge,
    timestamp_to_filename_safe,
    estimate_processing_time,
    format_timestamp_for_display
)

from .media_utils import (
    get_media_info,
    get_audio_codec,
    is_video_file,
    is_audio_file,
    validate_media_file,
    estimate_audio_quality,
    convert_to_wav,
    extract_audio_segment,
    get_media_duration,
    check_ffmpeg_availability
)


__all__ = [
    # File utilities
    'generate_safe_filename',
    'clear_directory_fast',
    'ensure_directory_exists',
    'get_file_hash',
    'get_file_size_mb',
    'validate_file_extension',
    'create_unique_filename',
    'copy_file_safely',
    'move_file_safely',
    'cleanup_old_files',
    'get_directory_size',
    'create_temp_directory',
    
    # Time utilities
    'seconds_to_hhmmss',
    'seconds_to_mmss',
    'hhmmss_to_seconds',
    'validate_time_format',
    'format_duration',
    'parse_duration_string',
    'time_range_overlap',
    'time_ranges_merge',
    'timestamp_to_filename_safe',
    'estimate_processing_time',
    'format_timestamp_for_display',
    
    # Media utilities
    'get_media_info',
    'get_audio_codec',
    'is_video_file',
    'is_audio_file',
    'validate_media_file',
    'estimate_audio_quality',
    'convert_to_wav',
    'extract_audio_segment',
    'get_media_duration',
    'check_ffmpeg_availability',
]
