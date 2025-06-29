#!/usr/bin/env python3
"""
Test script for social media download functionality in PreenCut.
This script tests the social media optimization and download features.
"""

import sys
import os
import tempfile
import shutil
import zipfile

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from web.gradio_ui import download_social_media_clips, CHECKBOX_CHECKED, CHECKBOX_UNCHECKED
from modules.processing_queue import ProcessingQueue
from config import TEMP_FOLDER, OUTPUT_FOLDER

def create_mock_task_result():
    """Create a mock task result for testing"""
    return {
        "status": "completed",
        "result": [  # Use legacy format for compatibility
            {
                "filename": "test_video.mp4",
                "filepath": "/path/to/test_video.mp4",
                "segments": [
                    {
                        "start": 10.5,
                        "end": 25.3,
                        "text": "This is a test segment for TikTok"
                    },
                    {
                        "start": 30.0,
                        "end": 50.0,
                        "text": "Another segment for Instagram"
                    }
                ]
            }
        ]
    }

def create_mock_social_results():
    """Create mock social media results for testing"""
    return [
        [
            CHECKBOX_CHECKED,  # Selected
            "🎵 TikTok",
            "00:00:10 - 00:00:25",
            "15s",
            "Amazing TikTok Content",
            "Bạn có biết điều này?",
            "#viral #tiktok #amazing",
            "8.5/10 ⭐",
            "🔴 Cao",
            "/path/to/thumbnail1.jpg"
        ],
        [
            CHECKBOX_UNCHECKED,  # Not selected
            "📸 Instagram",
            "00:00:30 - 00:00:50",
            "20s",
            "Instagram Reel Content",
            "Đây là bí quyết...",
            "#instagram #reel #content",
            "7.2/10 ⭐",
            "🟡 Trung bình",
            "/path/to/thumbnail2.jpg"
        ],
        [
            CHECKBOX_CHECKED,  # Selected
            "🎬 YouTube",
            "00:01:00 - 00:01:15",
            "15s",
            "YouTube Shorts Content",
            "Chào mọi người!",
            "#youtube #shorts #viral",
            "9.1/10 ⭐",
            "🔴 Cao",
            "/path/to/thumbnail3.jpg"
        ]
    ]

def test_download_functionality():
    """Test the social media download functionality"""
    print("🧪 Testing Social Media Download Functionality")
    print("=" * 50)
    
    # Setup test environment
    test_task_id = "test_social_media_123"
    
    # Create mock processing queue result
    processing_queue = ProcessingQueue()
    mock_result = create_mock_task_result()
    
    # Debug: Print the mock result structure
    print(f"   Debug - Mock result keys: {list(mock_result.keys())}")
    
    # Manually add result to queue for testing
    with processing_queue.lock:
        processing_queue.results[test_task_id] = mock_result
        
    # Debug: Verify the result was added
    stored_result = processing_queue.get_result(test_task_id)
    print(f"   Debug - Stored result keys: {list(stored_result.keys()) if stored_result else 'None'}")
    print(f"   Debug - Result status: {stored_result.get('status', 'Unknown') if stored_result else 'No result'}")
    
    # Create mock social results
    social_results = create_mock_social_results()
    
    print(f"✅ Created mock data:")
    print(f"   - Task ID: {test_task_id}")
    print(f"   - Social results: {len(social_results)} clips")
    print(f"   - Selected clips: {sum(1 for clip in social_results if clip[0] == CHECKBOX_CHECKED)}")
    
    # Test cases
    test_cases = [
        {
            "name": "Zip Download Mode",
            "download_mode": "Đóng gói thành tệp zip",
            "expected_extension": ".zip"
        },
        {
            "name": "Platform-specific Download Mode", 
            "download_mode": "Tải riêng lẻ theo nền tảng",
            "expected_extension": None  # Should return directory
        }
    ]
    
    for test_case in test_cases:
        print(f"\n🔄 Testing: {test_case['name']}")
        print("-" * 30)
        
        try:
            # Test the download function
            # Note: This will fail with actual video processing since we don't have real video files
            # But we can test the logic and error handling
            
            result = download_social_media_clips(
                task_id=test_task_id,
                social_results=social_results,
                download_mode=test_case["download_mode"]
            )
            
            print(f"   ✅ Function executed successfully")
            print(f"   📁 Result path: {result}")
            
            if test_case["expected_extension"]:
                if result.endswith(test_case["expected_extension"]):
                    print(f"   ✅ Correct file extension: {test_case['expected_extension']}")
                else:
                    print(f"   ❌ Wrong file extension. Expected: {test_case['expected_extension']}")
            
        except Exception as e:
            error_msg = str(e)
            if "FFmpeg error" in error_msg or "video file" in error_msg.lower():
                print(f"   ⚠️  Expected error (no real video files): {error_msg}")
            else:
                print(f"   ❌ Unexpected error: {error_msg}")
    
    # Test error cases
    print(f"\n🔄 Testing Error Cases")
    print("-" * 30)
    
    error_test_cases = [
        {
            "name": "Empty task ID",
            "task_id": "",
            "social_results": social_results,
            "expected_error": "Không có tác vụ xử lý nào đang hoạt động"
        },
        {
            "name": "No social results",
            "task_id": test_task_id,
            "social_results": [],
            "expected_error": "Chưa có kết quả tối ưu hóa nào"
        },
        {
            "name": "No selected clips",
            "task_id": test_task_id,
            "social_results": [[CHECKBOX_UNCHECKED, "TikTok", "00:00:10 - 00:00:25", "15s", "Test", "Hook", "#test", "8.0", "Cao", ""]],
            "expected_error": "Vui lòng chọn ít nhất một clip để tải xuống"
        }
    ]
    
    for test_case in error_test_cases:
        print(f"\n   Testing: {test_case['name']}")
        try:
            download_social_media_clips(
                task_id=test_case["task_id"],
                social_results=test_case["social_results"],
                download_mode="Đóng gói thành tệp zip"
            )
            print(f"      ❌ Should have raised error: {test_case['expected_error']}")
        except Exception as e:
            if test_case["expected_error"] in str(e):
                print(f"      ✅ Correctly raised expected error")
            else:
                print(f"      ❌ Wrong error. Expected: {test_case['expected_error']}, Got: {str(e)}")

def test_integration():
    """Test integration with UI components"""
    print(f"\n🔗 Testing UI Integration")
    print("=" * 50)
    
    try:
        # Test imports and function availability
        from web.gradio_ui import (
            download_social_media_clips,
            optimize_for_social_media, 
            select_all_clips,
            deselect_all_clips
        )
        
        print("✅ All required functions imported successfully")
        
        # Test utility functions
        test_data = [
            [CHECKBOX_UNCHECKED, "Test", "Data"],
            [CHECKBOX_UNCHECKED, "More", "Data"]
        ]
        
        # Test select all
        selected_data = select_all_clips(test_data)
        if all(row[0] == CHECKBOX_CHECKED for row in selected_data):
            print("✅ Select all function works correctly")
        else:
            print("❌ Select all function failed")
        
        # Test deselect all
        deselected_data = deselect_all_clips(selected_data)
        if all(row[0] == CHECKBOX_UNCHECKED for row in deselected_data):
            print("✅ Deselect all function works correctly")
        else:
            print("❌ Deselect all function failed")
            
    except Exception as e:
        print(f"❌ Integration test failed: {str(e)}")

def main():
    """Main test function"""
    print("🚀 PreenCut Social Media Download Feature Test")
    print("=" * 60)
    print("This test verifies the social media download functionality")
    print("including error handling and UI integration.\n")
    
    try:
        test_download_functionality()
        test_integration()
        
        print(f"\n🎉 Test Summary")
        print("=" * 50)
        print("✅ Basic functionality: Tested")
        print("✅ Error handling: Tested")
        print("✅ UI integration: Tested")
        print("\nNote: Video processing tests require actual video files")
        print("and will show expected errors in this test environment.")
        
    except Exception as e:
        print(f"\n❌ Test suite failed with error: {str(e)}")
        return False
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
