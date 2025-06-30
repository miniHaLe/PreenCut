#!/usr/bin/env python3
"""Test script for refactored modules and service integration."""

import os
import sys
import traceback
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Test environment setup
test_results = []


def run_test(test_name: str, test_func):
    """Run a test and capture results."""
    try:
        print(f"\n{'='*50}")
        print(f"Running test: {test_name}")
        print('='*50)
        
        result = test_func()
        test_results.append({"name": test_name, "status": "PASS", "result": result})
        print(f"✅ {test_name} - PASSED")
        return True
        
    except Exception as e:
        error_msg = f"{str(e)}\n{traceback.format_exc()}"
        test_results.append({"name": test_name, "status": "FAIL", "error": error_msg})
        print(f"❌ {test_name} - FAILED: {str(e)}")
        return False


def test_dependency_injection():
    """Test dependency injection container and service registration."""
    from core.dependency_injection import get_container, configure_default_services
    from services.interfaces import VideoServiceInterface, FileServiceInterface
    
    # Get container
    container = get_container()
    
    # Configure services
    configure_default_services(container)
    
    # Test service resolution
    video_service = container.get_service(VideoServiceInterface)
    file_service = container.get_service(FileServiceInterface)
    
    assert video_service is not None, "Video service not resolved"
    assert file_service is not None, "File service not resolved"
    
    # Test health checks
    container_health = container.health_check()
    assert container_health["status"] in ["healthy", "degraded"], f"Container unhealthy: {container_health}"
    
    return {
        "container_health": container_health,
        "services_registered": len(container._services),
        "video_service_type": type(video_service).__name__,
        "file_service_type": type(file_service).__name__
    }


def test_video_service():
    """Test video service functionality."""
    from core.dependency_injection import get_container
    from services.interfaces import VideoServiceInterface
    
    container = get_container()
    video_service = container.get_service(VideoServiceInterface)
    
    # Test validation
    test_result = video_service.validate_video_file("/nonexistent/file.mp4")
    assert test_result == False, "Should return False for non-existent file"
    
    # Test health check if available
    if hasattr(video_service, 'health_check'):
        health = video_service.health_check()
        assert isinstance(health, dict), "Health check should return dict"
    
    return {
        "service_type": type(video_service).__name__,
        "validation_works": True,
        "has_health_check": hasattr(video_service, 'health_check')
    }


def test_file_service():
    """Test file service functionality."""
    from core.dependency_injection import get_container
    from services.interfaces import FileServiceInterface
    import tempfile
    import uuid
    
    container = get_container()
    file_service = container.get_service(FileServiceInterface)
    
    # Test disk usage
    usage = file_service.get_disk_usage()
    assert "total_bytes" in usage, "Disk usage should contain total_bytes"
    assert usage["total_bytes"] > 0, "Total bytes should be positive"
    
    # Test task directory creation
    task_id = str(uuid.uuid4())
    task_dir = file_service.create_task_directory(task_id)
    assert os.path.exists(task_dir), "Task directory should be created"
    
    # Test cleanup
    cleanup_result = file_service.cleanup_task_directory(task_id, force=True)
    assert cleanup_result == True, "Cleanup should succeed"
    assert not os.path.exists(task_dir), "Task directory should be removed"
    
    return {
        "service_type": type(file_service).__name__,
        "disk_usage_gb": usage.get("total_gb", 0),
        "task_operations_work": True
    }


def test_refactored_video_processor():
    """Test refactored video processor."""
    from modules.video_processor_refactored import VideoProcessorRefactored
    
    processor = VideoProcessorRefactored()
    
    # Test initialization
    assert processor.video_service is not None, "Video service should be injected"
    assert processor.file_service is not None, "File service should be injected"
    
    # Test health check
    health = processor.health_check()
    assert isinstance(health, dict), "Health check should return dict"
    assert "status" in health, "Health check should have status"
    
    # Test segment validation
    test_segments = [
        {"start": 0, "end": 10, "text": "Test segment 1"},
        {"start": 10, "end": 20, "text": "Test segment 2"}
    ]
    
    validated = processor.validate_segments_timing(test_segments, 30)
    assert len(validated) == 2, "Should validate 2 segments"
    assert all("duration" in seg for seg in validated), "Should add duration to segments"
    
    return {
        "processor_type": type(processor).__name__,
        "health_status": health["status"],
        "segment_validation_works": True,
        "dependencies_injected": True
    }


def test_settings_integration():
    """Test settings integration with services."""
    from config.settings import get_settings
    
    settings = get_settings()
    
    # Verify key settings are loaded
    assert hasattr(settings, 'temp_folder'), "Settings should have temp_folder"
    assert hasattr(settings, 'output_folder'), "Settings should have output_folder"
    assert hasattr(settings, 'allowed_extensions'), "Settings should have allowed_extensions"
    assert hasattr(settings, 'speech_recognizer_type'), "Settings should have speech_recognizer_type"
    
    # Test that paths exist or can be created
    from utils.file_utils import ensure_directory_exists
    ensure_directory_exists(settings.temp_folder)
    ensure_directory_exists(settings.output_folder)
    
    assert os.path.exists(settings.temp_folder), "Temp folder should exist"
    assert os.path.exists(settings.output_folder), "Output folder should exist"
    
    return {
        "temp_folder": settings.temp_folder,
        "output_folder": settings.output_folder,
        "allowed_extensions": list(settings.allowed_extensions),
        "speech_recognizer": settings.speech_recognizer_type,
        "folders_exist": True
    }


def test_logging_integration():
    """Test logging integration."""
    from core.logging import get_logger
    
    logger = get_logger("test_script")
    
    # Test different log levels
    logger.debug("Debug message")
    logger.info("Info message", {"test_data": "value"})
    logger.warning("Warning message")
    
    # Test structured logging
    logger.info("Structured log test", {
        "component": "test_script",
        "action": "testing",
        "status": "in_progress"
    })
    
    return {
        "logger_created": True,
        "structured_logging": True,
        "log_levels_work": True
    }


def test_exception_handling():
    """Test custom exception handling."""
    from core.exceptions import (
        VideoProcessingError, 
        FileOperationError, 
        ConfigurationError,
        ValidationError,
        ErrorCode
    )
    
    # Test exception creation and inheritance
    try:
        raise VideoProcessingError("Test video error", error_code=ErrorCode.FILE_PROCESSING_ERROR)
    except VideoProcessingError as e:
        assert str(e) == "Test video error", "Exception message should match"
        assert e.error_code == ErrorCode.FILE_PROCESSING_ERROR, "Error code should be set"
    
    try:
        raise FileOperationError("Test file error")
    except FileOperationError:
        pass  # Expected
    
    return {
        "custom_exceptions_work": True,
        "error_codes_supported": True,
        "inheritance_correct": True
    }


def main():
    """Run all tests."""
    print("🚀 Starting refactoring integration tests...")
    print(f"Project root: {project_root}")
    
    # Test order matters due to dependencies
    tests = [
        ("Settings Integration", test_settings_integration),
        ("Logging Integration", test_logging_integration),
        ("Exception Handling", test_exception_handling),
        ("Dependency Injection", test_dependency_injection),
        ("Video Service", test_video_service),
        ("File Service", test_file_service),
        ("Refactored Video Processor", test_refactored_video_processor),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        if run_test(test_name, test_func):
            passed += 1
        else:
            failed += 1
    
    # Print summary
    print(f"\n{'='*60}")
    print("TEST SUMMARY")
    print('='*60)
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    print(f"📊 Total:  {len(tests)}")
    
    if failed == 0:
        print("\n🎉 All tests passed! Refactoring integration is working correctly.")
    else:
        print(f"\n⚠️  {failed} test(s) failed. Check the output above for details.")
    
    print(f"\n{'='*60}")
    print("DETAILED RESULTS")
    print('='*60)
    
    for result in test_results:
        status_icon = "✅" if result["status"] == "PASS" else "❌"
        print(f"{status_icon} {result['name']}: {result['status']}")
        
        if result["status"] == "PASS" and "result" in result:
            print(f"   📋 Result: {result['result']}")
        elif result["status"] == "FAIL":
            print(f"   ❌ Error: {result['error']}")
        print()
    
    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
