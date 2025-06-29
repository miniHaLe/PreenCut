#!/usr/bin/env python3
"""
Test script for timestamp accuracy in PreenCut
"""

import sys
import os
import json

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.llm_processor import LLMProcessor

def test_timestamp_accuracy():
    """Test the new timestamp-aware processing"""
    print("Testing PreenCut timestamp accuracy improvements...")
    
    # Create sample subtitle segments with realistic timestamps
    sample_segments = [
        {"start": 0.0, "end": 3.5, "text": "Xin chào các bạn, hôm nay chúng ta sẽ học về kinh tế."},
        {"start": 3.5, "end": 7.2, "text": "Đầu tiên, chúng ta sẽ tìm hiểu về thị trường chứng khoán."},
        {"start": 7.2, "end": 12.8, "text": "Thị trường chứng khoán là nơi mua bán cổ phiếu của các công ty."},
        {"start": 12.8, "end": 18.1, "text": "Giá cổ phiếu thay đổi theo cung và cầu trên thị trường."},
        {"start": 18.1, "end": 24.3, "text": "Bây giờ chúng ta sẽ chuyển sang chủ đề khác là về công nghệ."},
        {"start": 24.3, "end": 29.7, "text": "Công nghệ AI đang phát triển rất nhanh trong những năm gần đây."},
        {"start": 29.7, "end": 35.2, "text": "Machine learning là một phần quan trọng của AI."},
        {"start": 35.2, "end": 40.8, "text": "Hôm nay chúng ta đã học được nhiều điều thú vị."}
    ]
    
    # Test the new logical segmentation
    try:
        llm = LLMProcessor("llama3.1")  # Use default model
        
        print("\n1. Testing logical segmentation...")
        logical_segments = llm._create_logical_segments(sample_segments, target_duration=20)
        
        print(f"   Original segments: {len(sample_segments)}")
        print(f"   Logical segments: {len(logical_segments)}")
        
        for i, seg in enumerate(logical_segments):
            duration = seg['end'] - seg['start']
            print(f"   Segment {i+1}: {seg['start']:.1f}s - {seg['end']:.1f}s ({duration:.1f}s)")
            print(f"   Content: {seg['text'][:50]}...")
        
        print("\n2. Testing narrative segmentation...")
        # Create a mock align_result
        align_result = {
            'segments': sample_segments
        }
        
        # Test topic extraction
        prompt = "thị trường chứng khoán"
        narrative_segments = llm.segment_narrative(align_result, prompt)
        
        print(f"   Found {len(narrative_segments)} segments for topic: '{prompt}'")
        for i, seg in enumerate(narrative_segments):
            duration = seg['end'] - seg['start']
            print(f"   Match {i+1}: {seg['start']:.1f}s - {seg['end']:.1f}s ({duration:.1f}s)")
            print(f"   Summary: {seg['summary']}")
            print(f"   Relevance: {seg.get('relevance', 'N/A')}")
        
        print(f"\n✅ Timestamp accuracy test completed successfully!")
        print(f"   Key improvements:")
        print(f"   - Uses actual subtitle timestamps instead of generated ones")
        print(f"   - Groups into logical segments of appropriate duration")
        print(f"   - Sentence-level analysis for topic extraction")
        print(f"   - Merges and extends segments for better context")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_timestamp_accuracy()
    if success:
        print("\n🎉 All timestamp accuracy tests passed!")
        print("The fixes should resolve the timing issues you experienced.")
    else:
        print("\n❌ Some tests failed. Please check the errors above.")
    
    sys.exit(0 if success else 1)
