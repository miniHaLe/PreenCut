"""File management service implementation."""

import os
import shutil
import zipfile
import uuid
from typing import List, Dict, Optional, Any
from pathlib import Path

from core.logging import get_logger
from core.exceptions import FileOperationError, ValidationError, FileNotFoundError as CustomFileNotFoundError
from services.interfaces import FileServiceInterface
from utils.file_utils import generate_safe_filename, ensure_directory_exists, clear_directory_fast
from config.settings import get_settings


class FileService(FileServiceInterface):
    """Production-ready file management service."""
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self.settings = get_settings()
    
    def validate_upload(self, file_path: str, max_size: int = None) -> Dict[str, Any]:
        """Validate uploaded file meets requirements."""
        try:
            self.logger.info("Validating file upload", {
                "file_path": file_path,
                "max_size": max_size
            })
            
            if not os.path.exists(file_path):
                raise CustomFileNotFoundError(f"File not found: {file_path}")
            
            # Get file info
            file_size = os.path.getsize(file_path)
            file_ext = os.path.splitext(file_path)[1].lower()
            filename = os.path.basename(file_path)
            
            validation_result = {
                "is_valid": True,
                "file_path": file_path,
                "filename": filename,
                "file_size": file_size,
                "file_extension": file_ext,
                "errors": [],
                "warnings": []
            }
            
            # Check file size
            max_file_size = max_size or self.settings.max_file_size
            if file_size > max_file_size:
                validation_result["is_valid"] = False
                validation_result["errors"].append(
                    f"File size ({file_size} bytes) exceeds maximum ({max_file_size} bytes)"
                )
            
            # Check file extension
            if file_ext not in self.settings.allowed_extensions:
                validation_result["is_valid"] = False
                validation_result["errors"].append(
                    f"File extension '{file_ext}' not allowed. "
                    f"Allowed: {', '.join(self.settings.allowed_extensions)}"
                )
            
            # Check if file is empty
            if file_size == 0:
                validation_result["is_valid"] = False
                validation_result["errors"].append("File is empty")
            
            # Check filename for problematic characters
            safe_filename = generate_safe_filename(filename)
            if safe_filename != filename:
                validation_result["warnings"].append(
                    f"Filename contains special characters. Safe name: {safe_filename}"
                )
                validation_result["safe_filename"] = safe_filename
            
            self.logger.info("File validation completed", {
                "is_valid": validation_result["is_valid"],
                "errors_count": len(validation_result["errors"]),
                "warnings_count": len(validation_result["warnings"])
            })
            
            return validation_result
            
        except Exception as e:
            self.logger.error("File validation failed", {
                "file_path": file_path,
                "error": str(e)
            })
            if isinstance(e, CustomFileNotFoundError):
                raise
            raise ValidationError(f"File validation failed: {str(e)}") from e
    
    def save_uploaded_file(self, source_path: str, task_id: str, filename: str = None) -> str:
        """Save uploaded file to task directory with validation."""
        try:
            # Validate the upload first
            validation = self.validate_upload(source_path)
            if not validation["is_valid"]:
                raise ValidationError(f"File validation failed: {', '.join(validation['errors'])}")
            
            # Generate safe filename if not provided
            if not filename:
                filename = validation.get("safe_filename", validation["filename"])
            else:
                filename = generate_safe_filename(filename)
            
            # Create task directory
            task_dir = os.path.join(self.settings.temp_folder, task_id)
            ensure_directory_exists(task_dir)
            
            # Generate destination path
            dest_path = os.path.join(task_dir, filename)
            
            # Handle filename conflicts
            counter = 1
            base_name, ext = os.path.splitext(filename)
            while os.path.exists(dest_path):
                new_filename = f"{base_name}_{counter}{ext}"
                dest_path = os.path.join(task_dir, new_filename)
                counter += 1
            
            # Copy file
            shutil.copy2(source_path, dest_path)
            
            # Verify copy
            if not os.path.exists(dest_path):
                raise FileOperationError("File copy verification failed")
            
            dest_size = os.path.getsize(dest_path)
            source_size = os.path.getsize(source_path)
            if dest_size != source_size:
                raise FileOperationError(f"File size mismatch after copy: {dest_size} != {source_size}")
            
            self.logger.info("File saved successfully", {
                "source_path": source_path,
                "dest_path": dest_path,
                "task_id": task_id,
                "file_size": dest_size
            })
            
            return dest_path
            
        except Exception as e:
            self.logger.error("Failed to save uploaded file", {
                "source_path": source_path,
                "task_id": task_id,
                "filename": filename,
                "error": str(e)
            })
            if isinstance(e, (ValidationError, FileOperationError)):
                raise
            raise FileOperationError(f"File save failed: {str(e)}") from e
    
    def create_task_directory(self, task_id: str = None) -> str:
        """Create a new task directory and return its path."""
        try:
            if not task_id:
                task_id = str(uuid.uuid4())
            
            task_dir = os.path.join(self.settings.temp_folder, task_id)
            ensure_directory_exists(task_dir)
            
            self.logger.info("Task directory created", {
                "task_id": task_id,
                "task_dir": task_dir
            })
            
            return task_dir
            
        except Exception as e:
            self.logger.error("Failed to create task directory", {
                "task_id": task_id,
                "error": str(e)
            })
            raise FileOperationError(f"Task directory creation failed: {str(e)}") from e
    
    def cleanup_task_directory(self, task_id: str, force: bool = False) -> bool:
        """Clean up task directory and all its contents."""
        try:
            task_dir = os.path.join(self.settings.temp_folder, task_id)
            
            if not os.path.exists(task_dir):
                self.logger.warning("Task directory does not exist", {
                    "task_id": task_id,
                    "task_dir": task_dir
                })
                return True
            
            # Check if directory is empty or force cleanup
            if not force:
                if os.listdir(task_dir):
                    self.logger.info("Task directory not empty, skipping cleanup", {
                        "task_id": task_id,
                        "task_dir": task_dir
                    })
                    return False
            
            # Use fast directory clearing
            clear_directory_fast(task_dir)
            
            # Remove the directory itself
            os.rmdir(task_dir)
            
            self.logger.info("Task directory cleaned up successfully", {
                "task_id": task_id,
                "task_dir": task_dir,
                "force": force
            })
            
            return True
            
        except Exception as e:
            self.logger.error("Failed to cleanup task directory", {
                "task_id": task_id,
                "force": force,
                "error": str(e)
            })
            return False
    
    def create_output_package(self, task_id: str, files: List[str], package_name: str = None) -> str:
        """Create a zip package of output files."""
        try:
            self.logger.info("Creating output package", {
                "task_id": task_id,
                "files_count": len(files),
                "package_name": package_name
            })
            
            if not files:
                raise ValidationError("No files provided for packaging")
            
            # Validate all files exist
            missing_files = [f for f in files if not os.path.exists(f)]
            if missing_files:
                raise FileOperationError(f"Missing files for packaging: {missing_files}")
            
            # Generate package path
            if not package_name:
                package_name = f"output_{task_id}.zip"
            else:
                package_name = generate_safe_filename(package_name)
                if not package_name.endswith('.zip'):
                    package_name += '.zip'
            
            output_dir = self.settings.output_folder
            ensure_directory_exists(output_dir)
            package_path = os.path.join(output_dir, package_name)
            
            # Handle filename conflicts
            counter = 1
            base_name = package_name.replace('.zip', '')
            while os.path.exists(package_path):
                new_name = f"{base_name}_{counter}.zip"
                package_path = os.path.join(output_dir, new_name)
                counter += 1
            
            # Create zip file
            with zipfile.ZipFile(package_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file_path in files:
                    # Use just the filename in the zip (no directory structure)
                    arcname = os.path.basename(file_path)
                    zipf.write(file_path, arcname)
            
            # Verify package
            if not os.path.exists(package_path):
                raise FileOperationError("Package creation verification failed")
            
            package_size = os.path.getsize(package_path)
            
            self.logger.info("Output package created successfully", {
                "package_path": package_path,
                "package_size": package_size,
                "files_count": len(files)
            })
            
            return package_path
            
        except Exception as e:
            self.logger.error("Failed to create output package", {
                "task_id": task_id,
                "files_count": len(files),
                "error": str(e)
            })
            if isinstance(e, (ValidationError, FileOperationError)):
                raise
            raise FileOperationError(f"Package creation failed: {str(e)}") from e
    
    def get_directory_info(self, directory_path: str) -> Dict[str, Any]:
        """Get comprehensive information about a directory."""
        try:
            self.logger.debug("Getting directory info", {"directory_path": directory_path})
            
            if not os.path.exists(directory_path):
                raise CustomFileNotFoundError(f"Directory not found: {directory_path}")
            
            if not os.path.isdir(directory_path):
                raise ValidationError(f"Path is not a directory: {directory_path}")
            
            files = []
            total_size = 0
            file_count = 0
            dir_count = 0
            
            for root, dirs, filenames in os.walk(directory_path):
                dir_count += len(dirs)
                for filename in filenames:
                    file_path = os.path.join(root, filename)
                    try:
                        file_size = os.path.getsize(file_path)
                        rel_path = os.path.relpath(file_path, directory_path)
                        
                        files.append({
                            "name": filename,
                            "path": file_path,
                            "relative_path": rel_path,
                            "size": file_size,
                            "extension": os.path.splitext(filename)[1].lower()
                        })
                        
                        total_size += file_size
                        file_count += 1
                        
                    except (OSError, IOError) as e:
                        self.logger.warning("Cannot access file", {
                            "file_path": file_path,
                            "error": str(e)
                        })
                        continue
            
            info = {
                "directory_path": directory_path,
                "total_size": total_size,
                "file_count": file_count,
                "directory_count": dir_count,
                "files": files,
                "largest_file": max(files, key=lambda x: x["size"]) if files else None,
                "extensions": list(set(f["extension"] for f in files if f["extension"]))
            }
            
            self.logger.debug("Directory info retrieved", {
                "directory_path": directory_path,
                "file_count": file_count,
                "total_size": total_size
            })
            
            return info
            
        except Exception as e:
            self.logger.error("Failed to get directory info", {
                "directory_path": directory_path,
                "error": str(e)
            })
            if isinstance(e, (CustomFileNotFoundError, ValidationError)):
                raise
            raise FileOperationError(f"Directory info retrieval failed: {str(e)}") from e
    
    def move_files(self, source_paths: List[str], dest_directory: str) -> List[str]:
        """Move multiple files to destination directory."""
        try:
            self.logger.info("Moving files", {
                "source_count": len(source_paths),
                "dest_directory": dest_directory
            })
            
            if not source_paths:
                raise ValidationError("No source files provided")
            
            # Ensure destination directory exists
            ensure_directory_exists(dest_directory)
            
            moved_files = []
            failed_files = []
            
            for source_path in source_paths:
                try:
                    if not os.path.exists(source_path):
                        failed_files.append({"path": source_path, "error": "File not found"})
                        continue
                    
                    filename = os.path.basename(source_path)
                    dest_path = os.path.join(dest_directory, filename)
                    
                    # Handle filename conflicts
                    counter = 1
                    base_name, ext = os.path.splitext(filename)
                    while os.path.exists(dest_path):
                        new_filename = f"{base_name}_{counter}{ext}"
                        dest_path = os.path.join(dest_directory, new_filename)
                        counter += 1
                    
                    # Move file
                    shutil.move(source_path, dest_path)
                    moved_files.append(dest_path)
                    
                except Exception as e:
                    failed_files.append({
                        "path": source_path,
                        "error": str(e)
                    })
                    self.logger.warning("Failed to move file", {
                        "source_path": source_path,
                        "error": str(e)
                    })
            
            self.logger.info("File move operation completed", {
                "moved_count": len(moved_files),
                "failed_count": len(failed_files),
                "dest_directory": dest_directory
            })
            
            if failed_files and not moved_files:
                raise FileOperationError(f"Failed to move any files. Errors: {failed_files}")
            
            return moved_files
            
        except Exception as e:
            self.logger.error("File move operation failed", {
                "source_count": len(source_paths),
                "dest_directory": dest_directory,
                "error": str(e)
            })
            if isinstance(e, (ValidationError, FileOperationError)):
                raise
            raise FileOperationError(f"File move failed: {str(e)}") from e
    
    def get_disk_usage(self, path: str = None) -> Dict[str, Any]:
        """Get disk usage information for specified path or system."""
        try:
            check_path = path or self.settings.temp_folder
            
            if not os.path.exists(check_path):
                raise CustomFileNotFoundError(f"Path not found: {check_path}")
            
            statvfs = shutil.disk_usage(check_path)
            total, used, free = statvfs
            
            usage_info = {
                "path": check_path,
                "total_bytes": total,
                "used_bytes": used,
                "free_bytes": free,
                "usage_percent": round((used / total) * 100, 2) if total > 0 else 0,
                "total_gb": round(total / (1024**3), 2),
                "used_gb": round(used / (1024**3), 2),
                "free_gb": round(free / (1024**3), 2)
            }
            
            self.logger.debug("Disk usage retrieved", usage_info)
            return usage_info
            
        except Exception as e:
            self.logger.error("Failed to get disk usage", {
                "path": path,
                "error": str(e)
            })
            return {
                "path": path or "unknown",
                "error": str(e),
                "total_bytes": 0,
                "free_bytes": 0,
                "usage_percent": 0
            }
