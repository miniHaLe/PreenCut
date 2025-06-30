#!/usr/bin/env python3
"""Simple test to check service imports."""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_imports():
    """Test basic imports."""
    try:
        print("Testing config imports...")
        from config.settings import get_settings
        settings = get_settings()
        print(f"✅ Settings loaded: {settings.name}")
        
        print("\nTesting logging imports...")
        from core.logging import get_logger
        logger = get_logger("test")
        print("✅ Logger created")
        
        print("\nTesting exception imports...")
        from core.exceptions import VideoProcessingError, LLMProcessingError
        print("✅ Exception classes imported")
        
        print("\nTesting interface imports...")
        from services.interfaces import VideoServiceInterface, FileServiceInterface
        print("✅ Service interfaces imported")
        
        print("\nTesting service implementations...")
        from services.video_service import VideoService
        from services.file_service import FileService
        print("✅ Core services imported")
        
        print("\nTesting service dependencies...")
        video_service = VideoService()
        file_service = FileService()
        print("✅ Services instantiated")
        
        print("\nTesting dependency injection...")
        from core.dependency_injection import get_container, configure_default_services
        container = get_container()
        print("✅ Container created")
        
        print("\nConfiguring services...")
        configure_default_services(container)
        print("✅ Services configured")
        
        return True
        
    except Exception as e:
        print(f"❌ Import test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_imports()
    sys.exit(0 if success else 1)
