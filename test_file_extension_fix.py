#!/usr/bin/env python3
"""
Test script to validate file extension checking logic
"""

import os
import sys

# Add the project root to Python path
sys.path.insert(0, '/ssd2/PreenCut')

from config import ALLOWED_EXTENSIONS

def test_file_extension_validation():
    """Test the fixed file extension validation logic"""
    
    print("🧪 Testing File Extension Validation Fix")
    print("=" * 50)
    
    # Test cases
    test_files = [
        "video.mp4",
        "audio.wav", 
        "movie.avi",
        "clip.mov",
        "invalid.txt",
        "document.pdf"
    ]
    
    print(f"📁 ALLOWED_EXTENSIONS: {ALLOWED_EXTENSIONS}")
    print()
    
    for filename in test_files:
        # Use the fixed logic (keep the dot)
        ext = os.path.splitext(filename)[1].lower()
        is_valid = ext in ALLOWED_EXTENSIONS
        
        status = "✅ VALID" if is_valid else "❌ INVALID"
        print(f"{filename:<15} -> Extension: {ext:<6} -> {status}")
    
    print()
    print("🎯 Test completed!")

if __name__ == "__main__":
    test_file_extension_validation()
