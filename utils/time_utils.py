"""
Time and format utilities for PreenCut application.
Handles time conversions, formatting, and validation.
"""

import re
from typing import Union, Optional
from datetime import datetime, timedelta
import math

from core.logging import get_logger
from core.exceptions import handle_exceptions


logger = get_logger(__name__)


@handle_exceptions('time_utils')
def seconds_to_hhmmss(seconds: Union[float, int]) -> str:
    """
    Convert seconds to HH:MM:SS format.
    
    Args:
        seconds: Time in seconds (can be float)
        
    Returns:
        Formatted time string in HH:MM:SS format
    """
    if not isinstance(seconds, (int, float)):
        return "00:00:00"
    
    seconds = max(0, float(seconds))  # Ensure non-negative
    
    hours = int(seconds // 3600)
    remaining_seconds = seconds % 3600
    minutes = int(remaining_seconds // 60)
    secs = int(round(remaining_seconds % 60))
    
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


@handle_exceptions('time_utils')
def seconds_to_mmss(seconds: Union[float, int]) -> str:
    """
    Convert seconds to MM:SS format.
    
    Args:
        seconds: Time in seconds (can be float)
        
    Returns:
        Formatted time string in MM:SS format
    """
    if not isinstance(seconds, (int, float)):
        return "00:00"
    
    seconds = max(0, float(seconds))  # Ensure non-negative
    
    minutes = int(seconds // 60)
    secs = int(round(seconds % 60))
    
    return f"{minutes:02d}:{secs:02d}"


@handle_exceptions('time_utils')
def hhmmss_to_seconds(time_str: str) -> float:
    """
    Convert HH:MM:SS or MM:SS format to seconds.
    
    Args:
        time_str: Time string in HH:MM:SS or MM:SS format
        
    Returns:
        Time in seconds as float
        
    Raises:
        ValueError: If time format is invalid
    """
    if not time_str or not isinstance(time_str, str):
        raise ValueError("Time string cannot be empty")
    
    time_str = time_str.strip()
    parts = time_str.split(':')
    
    if len(parts) == 2:  # MM:SS format
        try:
            minutes, seconds = map(float, parts)
            return minutes * 60 + seconds
        except ValueError:
            raise ValueError(f"Invalid MM:SS format: {time_str}")
    
    elif len(parts) == 3:  # HH:MM:SS format
        try:
            hours, minutes, seconds = map(float, parts)
            return hours * 3600 + minutes * 60 + seconds
        except ValueError:
            raise ValueError(f"Invalid HH:MM:SS format: {time_str}")
    
    else:
        raise ValueError(f"Invalid time format: {time_str}. Expected MM:SS or HH:MM:SS")


@handle_exceptions('time_utils')
def validate_time_format(time_str: str) -> bool:
    """
    Validate time string format.
    
    Args:
        time_str: Time string to validate
        
    Returns:
        True if format is valid
    """
    try:
        hhmmss_to_seconds(time_str)
        return True
    except ValueError:
        return False


@handle_exceptions('time_utils')
def format_duration(seconds: Union[float, int], style: str = 'long') -> str:
    """
    Format duration in human-readable format.
    
    Args:
        seconds: Duration in seconds
        style: Format style ('long', 'short', 'compact')
        
    Returns:
        Formatted duration string
    """
    if not isinstance(seconds, (int, float)) or seconds < 0:
        return "0 seconds"
    
    seconds = int(seconds)
    
    if seconds < 60:
        if style == 'compact':
            return f"{seconds}s"
        elif style == 'short':
            return f"{seconds} sec"
        else:
            return f"{seconds} second{'s' if seconds != 1 else ''}"
    
    minutes = seconds // 60
    remaining_seconds = seconds % 60
    
    if minutes < 60:
        if style == 'compact':
            if remaining_seconds == 0:
                return f"{minutes}m"
            return f"{minutes}m {remaining_seconds}s"
        elif style == 'short':
            if remaining_seconds == 0:
                return f"{minutes} min"
            return f"{minutes} min {remaining_seconds} sec"
        else:
            parts = [f"{minutes} minute{'s' if minutes != 1 else ''}"]
            if remaining_seconds > 0:
                parts.append(f"{remaining_seconds} second{'s' if remaining_seconds != 1 else ''}")
            return " ".join(parts)
    
    hours = minutes // 60
    remaining_minutes = minutes % 60
    
    if style == 'compact':
        parts = [f"{hours}h"]
        if remaining_minutes > 0:
            parts.append(f"{remaining_minutes}m")
        if remaining_seconds > 0:
            parts.append(f"{remaining_seconds}s")
        return " ".join(parts)
    elif style == 'short':
        parts = [f"{hours} hr"]
        if remaining_minutes > 0:
            parts.append(f"{remaining_minutes} min")
        if remaining_seconds > 0:
            parts.append(f"{remaining_seconds} sec")
        return " ".join(parts)
    else:
        parts = [f"{hours} hour{'s' if hours != 1 else ''}"]
        if remaining_minutes > 0:
            parts.append(f"{remaining_minutes} minute{'s' if remaining_minutes != 1 else ''}")
        if remaining_seconds > 0:
            parts.append(f"{remaining_seconds} second{'s' if remaining_seconds != 1 else ''}")
        return " ".join(parts)


@handle_exceptions('time_utils')
def parse_duration_string(duration_str: str) -> Optional[float]:
    """
    Parse human-readable duration string to seconds.
    
    Args:
        duration_str: Duration string like "1h 30m 45s" or "90 minutes"
        
    Returns:
        Duration in seconds, or None if parsing fails
    """
    if not duration_str or not isinstance(duration_str, str):
        return None
    
    duration_str = duration_str.lower().strip()
    total_seconds = 0.0
    
    # Pattern for matching time components
    patterns = [
        (r'(\d+(?:\.\d+)?)\s*h(?:ours?)?', 3600),     # hours
        (r'(\d+(?:\.\d+)?)\s*m(?:in(?:utes?)?)?', 60), # minutes
        (r'(\d+(?:\.\d+)?)\s*s(?:ec(?:onds?)?)?', 1),   # seconds
    ]
    
    for pattern, multiplier in patterns:
        matches = re.findall(pattern, duration_str)
        for match in matches:
            try:
                total_seconds += float(match) * multiplier
            except ValueError:
                continue
    
    return total_seconds if total_seconds > 0 else None


@handle_exceptions('time_utils')
def time_range_overlap(start1: float, end1: float, start2: float, end2: float) -> float:
    """
    Calculate overlap between two time ranges.
    
    Args:
        start1, end1: First time range
        start2, end2: Second time range
        
    Returns:
        Overlap duration in seconds
    """
    overlap_start = max(start1, start2)
    overlap_end = min(end1, end2)
    
    return max(0, overlap_end - overlap_start)


@handle_exceptions('time_utils')
def time_ranges_merge(ranges: list) -> list:
    """
    Merge overlapping time ranges.
    
    Args:
        ranges: List of (start, end) tuples
        
    Returns:
        List of merged non-overlapping ranges
    """
    if not ranges:
        return []
    
    # Sort ranges by start time
    sorted_ranges = sorted(ranges, key=lambda x: x[0])
    merged = [sorted_ranges[0]]
    
    for current in sorted_ranges[1:]:
        last = merged[-1]
        
        # If current range overlaps with last merged range
        if current[0] <= last[1]:
            # Merge ranges
            merged[-1] = (last[0], max(last[1], current[1]))
        else:
            # Add new non-overlapping range
            merged.append(current)
    
    return merged


@handle_exceptions('time_utils')
def timestamp_to_filename_safe(timestamp: Optional[datetime] = None) -> str:
    """
    Convert timestamp to filename-safe string.
    
    Args:
        timestamp: Datetime object, or None for current time
        
    Returns:
        Filename-safe timestamp string
    """
    if timestamp is None:
        timestamp = datetime.now()
    
    return timestamp.strftime("%Y%m%d_%H%M%S")


@handle_exceptions('time_utils')
def estimate_processing_time(file_size_mb: float, duration_seconds: float) -> float:
    """
    Estimate processing time based on file characteristics.
    
    Args:
        file_size_mb: File size in megabytes
        duration_seconds: Audio/video duration in seconds
        
    Returns:
        Estimated processing time in seconds
    """
    # Base estimation: roughly 0.1x real-time for transcription
    # Plus additional time for file size overhead
    
    base_time = duration_seconds * 0.1
    size_factor = file_size_mb * 0.5  # 0.5 seconds per MB
    
    # Minimum 10 seconds, maximum 10 minutes
    estimated = max(10, min(600, base_time + size_factor))
    
    return estimated


@handle_exceptions('time_utils')
def format_timestamp_for_display(timestamp: datetime) -> str:
    """
    Format timestamp for user display.
    
    Args:
        timestamp: Datetime object
        
    Returns:
        Formatted timestamp string
    """
    now = datetime.now()
    diff = now - timestamp
    
    if diff.days > 7:
        return timestamp.strftime("%Y-%m-%d %H:%M")
    elif diff.days > 0:
        return f"{diff.days} day{'s' if diff.days > 1 else ''} ago"
    elif diff.seconds > 3600:
        hours = diff.seconds // 3600
        return f"{hours} hour{'s' if hours > 1 else ''} ago"
    elif diff.seconds > 60:
        minutes = diff.seconds // 60
        return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
    else:
        return "Just now"
