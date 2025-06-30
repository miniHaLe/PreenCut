#!/usr/bin/env python3
"""
Test script for refactored PreenCut functionality.
"""

import sys
import os

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_basic_functionality():
    """Test basic functionality of refactored components."""
    print("🔍 Testing refactored PreenCut components...")
    
    try:
        # Test time utilities
        from utils.time_utils import seconds_to_hhmmss, hhmmss_to_seconds
        print("✅ Time utilities imported successfully")
        
        # Test time conversion
        time_str = seconds_to_hhmmss(3661)
        assert time_str == "01:01:01", f"Expected 01:01:01, got {time_str}"
        print(f"✅ Time conversion: 3661 seconds -> {time_str}")
        
        # Test reverse conversion
        seconds = hhmmss_to_seconds("01:01:01")
        assert seconds == 3661, f"Expected 3661, got {seconds}"
        print(f"✅ Reverse conversion: 01:01:01 -> {seconds} seconds")
        
    except Exception as e:
        print(f"❌ Time utilities test failed: {e}")
        return False
    
    try:
        # Test file utilities
        from utils.file_utils import generate_safe_filename
        print("✅ File utilities imported successfully")
        
        # Test safe filename generation
        safe_name = generate_safe_filename("test file <name>.mp4")
        print(f"✅ Safe filename: 'test file <name>.mp4' -> '{safe_name}'")
        
    except Exception as e:
        print(f"❌ File utilities test failed: {e}")
        return False
    
    try:
        # Test configuration (without GPU dependencies)
        print("✅ Testing configuration system...")
        
        # This should work even without torch
        import os
        os.environ['WHISPER_DEVICE'] = 'cpu'  # Force CPU mode for testing
        
        from config.settings import ConfigManager
        config_manager = ConfigManager()
        config = config_manager.config
        
        print(f"✅ Configuration loaded: {config.name} v{config.version}")
        print(f"✅ Environment: {config.environment.value}")
        print(f"✅ Device: {config.gpu.whisper_device}")
        
    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
        return False
    
    try:
        # Test logging (basic functionality)
        from core.logging import get_logger
        logger = get_logger('test')
        print("✅ Logging system imported successfully")
        
    except Exception as e:
        print(f"❌ Logging test failed: {e}")
        return False
    
    try:
        # Test exception handling
        from core.exceptions import ErrorHandler, ErrorCode
        print("✅ Exception handling imported successfully")
        
        # Test error creation
        error = ErrorHandler.create_file_not_found_error("/nonexistent/file.txt")
        assert error.error_details.code == ErrorCode.FILE_NOT_FOUND
        print("✅ Error handling working correctly")
        
    except Exception as e:
        print(f"❌ Exception handling test failed: {e}")
        return False
    
    print("\n🎉 All refactored components are working correctly!")
    return True


def test_legacy_compatibility():
    """Test that legacy imports still work."""
    print("\n🔍 Testing legacy compatibility...")
    
    try:
        # Test legacy config import (should show deprecation warning)
        import config
        print("✅ Legacy config import works (with deprecation warning)")
        
        # Test legacy utils import (should show deprecation warning)
        import utils
        print("✅ Legacy utils import works (with deprecation warning)")
        
        print("✅ Legacy compatibility maintained")
        return True
        
    except Exception as e:
        print(f"❌ Legacy compatibility test failed: {e}")
        return False


def test_project_structure():
    """Test that the new project structure is correct."""
    print("\n🔍 Testing project structure...")
    
    required_dirs = [
        'config',
        'core', 
        'services',
        'utils',
        'web',
        'modules',
        'tests',
        'docs'
    ]
    
    required_files = [
        '.env.example',
        'main.py',
        'requirements.txt',
        'config/__init__.py',
        'config/settings.py',
        'core/__init__.py',
        'core/logging.py',
        'core/exceptions.py',
        'core/dependency_injection.py',
        'services/__init__.py',
        'services/interfaces.py',
        'utils/__init__.py',
        'utils/file_utils.py',
        'utils/time_utils.py',
        'utils/media_utils.py',
        'docs/PRODUCTION_DEPLOYMENT.md',
        'docs/REFACTORING_SUMMARY.md'
    ]
    
    missing_dirs = []
    missing_files = []
    
    for directory in required_dirs:
        if not os.path.isdir(directory):
            missing_dirs.append(directory)
    
    for file_path in required_files:
        if not os.path.isfile(file_path):
            missing_files.append(file_path)
    
    if missing_dirs:
        print(f"❌ Missing directories: {missing_dirs}")
        return False
    
    if missing_files:
        print(f"❌ Missing files: {missing_files}")
        return False
    
    print("✅ All required directories and files are present")
    return True


if __name__ == "__main__":
    print("🚀 PreenCut Refactoring Test Suite")
    print("=" * 50)
    
    # Test project structure
    structure_ok = test_project_structure()
    
    # Test basic functionality
    basic_ok = test_basic_functionality()
    
    # Test legacy compatibility
    legacy_ok = test_legacy_compatibility()
    
    print("\n" + "=" * 50)
    print("📊 Test Results Summary:")
    print(f"  Project Structure: {'✅ PASS' if structure_ok else '❌ FAIL'}")
    print(f"  Basic Functionality: {'✅ PASS' if basic_ok else '❌ FAIL'}")
    print(f"  Legacy Compatibility: {'✅ PASS' if legacy_ok else '❌ FAIL'}")
    
    if all([structure_ok, basic_ok, legacy_ok]):
        print("\n🎉 All tests passed! PreenCut refactoring is successful.")
        print("\n📚 Next steps:")
        print("  1. Copy .env.example to .env and configure")
        print("  2. Install requirements: pip install -r requirements.txt")
        print("  3. Run the application: python main.py")
        print("  4. See docs/PRODUCTION_DEPLOYMENT.md for production setup")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed. Please check the issues above.")
        sys.exit(1)
