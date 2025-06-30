"""
File utilities for PreenCut application.
Handles file operations, validation, and path management.
"""

import os
import shutil
import hashlib
from pathlib import Path
from typing import List, Optional
import re

from config import get_config
from core.logging import get_logger
from core.exceptions import ErrorHandler, handle_exceptions


logger = get_logger(__name__)
config = get_config()


@handle_exceptions('file_utils')
def generate_safe_filename(filename: str, max_length: int = 100) -> str:
    """
    Generate a safe filename by removing special characters and limiting length.
    
    Args:
        filename: Original filename
        max_length: Maximum length for the filename
        
    Returns:
        Safe filename string
    """
    if not filename:
        return "unnamed_file"
    
    # Remove or replace unsafe characters
    safe_filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    safe_filename = re.sub(r'[^\w\s.-]', '', safe_filename)
    safe_filename = safe_filename.strip()
    
    # Limit length while preserving extension
    if len(safe_filename) > max_length:
        name, ext = os.path.splitext(safe_filename)
        max_name_length = max_length - len(ext)
        safe_filename = name[:max_name_length] + ext
    
    return safe_filename or "unnamed_file"


@handle_exceptions('file_utils')
def clear_directory_fast(directory_path: str) -> None:
    """
    Quickly clear directory contents by removing and recreating it.
    
    Args:
        directory_path: Path to directory to clear
    """
    path = Path(directory_path)
    
    if path.exists():
        shutil.rmtree(path)
        logger.info(f"Removed directory: {path}")
    
    path.mkdir(parents=True, exist_ok=True)
    logger.info(f"Created clean directory: {path}")


@handle_exceptions('file_utils')
def ensure_directory_exists(directory_path: str) -> Path:
    """
    Ensure directory exists, create if it doesn't.
    
    Args:
        directory_path: Path to directory
        
    Returns:
        Path object for the directory
    """
    path = Path(directory_path)
    path.mkdir(parents=True, exist_ok=True)
    return path


@handle_exceptions('file_utils')
def get_file_hash(file_path: str, algorithm: str = 'md5') -> str:
    """
    Calculate hash of a file.
    
    Args:
        file_path: Path to file
        algorithm: Hash algorithm (md5, sha1, sha256)
        
    Returns:
        Hex digest of file hash
    """
    hash_obj = hashlib.new(algorithm)
    
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_obj.update(chunk)
    
    return hash_obj.hexdigest()


@handle_exceptions('file_utils')
def get_file_size_mb(file_path: str) -> float:
    """
    Get file size in megabytes.
    
    Args:
        file_path: Path to file
        
    Returns:
        File size in MB
    """
    size_bytes = os.path.getsize(file_path)
    return size_bytes / (1024 * 1024)


@handle_exceptions('file_utils')
def validate_file_extension(file_path: str, allowed_extensions: Optional[List[str]] = None) -> bool:
    """
    Validate file extension against allowed extensions.
    
    Args:
        file_path: Path to file
        allowed_extensions: List of allowed extensions (without dots)
        
    Returns:
        True if extension is allowed
    """
    if allowed_extensions is None:
        allowed_extensions = config.file.allowed_extensions
    
    file_ext = Path(file_path).suffix.lower().lstrip('.')
    return file_ext in [ext.lower() for ext in allowed_extensions]


@handle_exceptions('file_utils')
def create_unique_filename(directory: str, base_name: str, extension: str = '') -> str:
    """
    Create a unique filename in the given directory.
    
    Args:
        directory: Target directory
        base_name: Base filename without extension
        extension: File extension (with or without dot)
        
    Returns:
        Unique filename
    """
    if extension and not extension.startswith('.'):
        extension = '.' + extension
    
    directory_path = Path(directory)
    counter = 0
    
    while True:
        if counter == 0:
            filename = f"{base_name}{extension}"
        else:
            filename = f"{base_name}_{counter}{extension}"
        
        if not (directory_path / filename).exists():
            return filename
        
        counter += 1


@handle_exceptions('file_utils')
def copy_file_safely(source: str, destination: str, overwrite: bool = False) -> str:
    """
    Safely copy a file with error handling.
    
    Args:
        source: Source file path
        destination: Destination file path
        overwrite: Whether to overwrite existing files
        
    Returns:
        Actual destination path used
    """
    source_path = Path(source)
    dest_path = Path(destination)
    
    if not source_path.exists():
        raise ErrorHandler.create_file_not_found_error(str(source_path))
    
    # Ensure destination directory exists
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Handle existing destination
    if dest_path.exists() and not overwrite:
        # Create unique filename
        base_name = dest_path.stem
        extension = dest_path.suffix
        unique_name = create_unique_filename(str(dest_path.parent), base_name, extension)
        dest_path = dest_path.parent / unique_name
    
    shutil.copy2(source_path, dest_path)
    logger.info(f"Copied file: {source_path} -> {dest_path}")
    
    return str(dest_path)


@handle_exceptions('file_utils')
def move_file_safely(source: str, destination: str, overwrite: bool = False) -> str:
    """
    Safely move a file with error handling.
    
    Args:
        source: Source file path
        destination: Destination file path
        overwrite: Whether to overwrite existing files
        
    Returns:
        Actual destination path used
    """
    dest_path = copy_file_safely(source, destination, overwrite)
    
    # Remove source file
    os.remove(source)
    logger.info(f"Moved file: {source} -> {dest_path}")
    
    return dest_path


@handle_exceptions('file_utils')
def cleanup_old_files(directory: str, max_age_hours: int = 24) -> int:
    """
    Clean up old files in a directory.
    
    Args:
        directory: Directory to clean
        max_age_hours: Maximum age in hours before deletion
        
    Returns:
        Number of files deleted
    """
    import time
    
    directory_path = Path(directory)
    if not directory_path.exists():
        return 0
    
    current_time = time.time()
    max_age_seconds = max_age_hours * 3600
    deleted_count = 0
    
    for file_path in directory_path.rglob('*'):
        if file_path.is_file():
            file_age = current_time - file_path.stat().st_mtime
            if file_age > max_age_seconds:
                try:
                    file_path.unlink()
                    deleted_count += 1
                    logger.debug(f"Deleted old file: {file_path}")
                except Exception as e:
                    logger.warning(f"Failed to delete file {file_path}: {e}")
    
    logger.info(f"Cleaned up {deleted_count} old files from {directory}")
    return deleted_count


@handle_exceptions('file_utils')
def get_directory_size(directory: str) -> int:
    """
    Get total size of directory in bytes.
    
    Args:
        directory: Directory path
        
    Returns:
        Total size in bytes
    """
    total_size = 0
    directory_path = Path(directory)
    
    if directory_path.exists():
        for file_path in directory_path.rglob('*'):
            if file_path.is_file():
                total_size += file_path.stat().st_size
    
    return total_size


@handle_exceptions('file_utils')
def create_temp_directory(prefix: str = "preencut_") -> str:
    """
    Create a temporary directory with unique name.
    
    Args:
        prefix: Prefix for directory name
        
    Returns:
        Path to created directory
    """
    import tempfile
    import uuid
    
    temp_name = f"{prefix}{uuid.uuid4().hex[:8]}"
    temp_path = Path(config.file.temp_folder) / temp_name
    temp_path.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"Created temporary directory: {temp_path}")
    return str(temp_path)
