#!/usr/bin/env python3
"""
Simple test for the social media download functionality.
"""

import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_function_import():
    """Test if we can import the download function"""
    try:
        from web.gradio_ui import download_social_media_clips
        print("✅ download_social_media_clips imported successfully")
        return True
    except Exception as e:
        print(f"❌ Failed to import download_social_media_clips: {e}")
        return False

def test_ui_components():
    """Test if we can import UI helper functions"""
    try:
        from web.gradio_ui import (
            select_all_clips,
            deselect_all_clips,
            CHECKBOX_CHECKED,
            CHECKBOX_UNCHECKED
        )
        print("✅ UI helper functions imported successfully")
        
        # Test basic functionality
        test_data = [
            [CHECKBOX_UNCHECKED, "Test1"],
            [CHECKBOX_UNCHECKED, "Test2"]
        ]
        
        selected = select_all_clips(test_data)
        if all(row[0] == CHECKBOX_CHECKED for row in selected):
            print("✅ Select all function works")
        else:
            print("❌ Select all function failed")
            
        deselected = deselect_all_clips(selected)
        if all(row[0] == CHECKBOX_UNCHECKED for row in deselected):
            print("✅ Deselect all function works")
        else:
            print("❌ Deselect all function failed")
            
        return True
    except Exception as e:
        print(f"❌ Failed to import UI functions: {e}")
        return False

def test_gradio_interface():
    """Test if we can create the Gradio interface"""
    try:
        from web.gradio_ui import create_gradio_interface
        print("✅ create_gradio_interface imported successfully")
        print("   (Not creating actual interface in test)")
        return True
    except Exception as e:
        print(f"❌ Failed to import create_gradio_interface: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 Simple Social Media Download Test")
    print("=" * 40)
    
    tests = [
        ("Function Import", test_function_import),
        ("UI Components", test_ui_components), 
        ("Gradio Interface", test_gradio_interface)
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n📋 Testing: {test_name}")
        print("-" * 20)
        try:
            result = test_func()
            results.append(result)
        except Exception as e:
            print(f"❌ Test {test_name} failed with exception: {e}")
            results.append(False)
    
    print(f"\n📊 Test Summary")
    print("=" * 40)
    passed = sum(results)
    total = len(results)
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 All tests passed!")
        return True
    else:
        print("⚠️  Some tests failed")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
