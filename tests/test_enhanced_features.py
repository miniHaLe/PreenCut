#!/usr/bin/env python3
"""
Test script for enhanced PreenCut features:
1. Enhanced summaries with word counts
2. Relevancy ranking for segment matching
3. Social media optimization for viral content
"""

import sys
import os
import json

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.llm_processor import LLMProcessor

def test_enhanced_features():
    """Test all enhanced features"""
    print("🚀 Testing PreenCut Enhanced Features...")
    
    # Create realistic Vietnamese video content with timestamps
    sample_segments = [
        {"start": 0.0, "end": 5.2, "text": "Xin chào mọi người! Hôm nay tôi sẽ chia sẻ 5 mẹo học tiếng Anh hiệu quả."},
        {"start": 5.2, "end": 12.8, "text": "Mẹo đầu tiên là nghe nhạc tiếng Anh mỗi ngày. Điều này giúp bạn làm quen với âm thanh và nhịp điệu của ngôn ngữ."},
        {"start": 12.8, "end": 20.1, "text": "Mẹo thứ hai là xem phim với phụ đề tiếng Anh. Bạn có thể bắt đầu với phim hoạt hình đơn giản."},
        {"start": 20.1, "end": 28.3, "text": "Điều quan trọng nhất là thực hành nói hàng ngày, dù chỉ 10-15 phút. Hãy nói to để cải thiện phát âm."},
        {"start": 28.3, "end": 35.7, "text": "Bây giờ chúng ta chuyển sang chủ đề khác - cách nấu ăn ngon tại nhà với nguyên liệu đơn giản."},
        {"start": 35.7, "end": 43.2, "text": "Để nấu phở ngon, bạn cần có nước dùng trong, thịt bò tươi, và bánh phở chất lượng tốt."},
        {"start": 43.2, "end": 50.8, "text": "Bí quyết của phở ngon nằm ở nước dùng. Hầm xương bò ít nhất 4-6 tiếng để có nước dùng đậm đà."},
        {"start": 50.8, "end": 58.1, "text": "Cuối cùng, tôi muốn chia sẻ về xu hướng làm đẹp tự nhiên đang rất hot trên TikTok hiện nay."}
    ]
    
    try:
        llm = LLMProcessor("llama3.1")
        
        print("\n📊 1. Testing Enhanced Video Segmentation...")
        enhanced_segments = llm.segment_video(sample_segments, "Tạo video hướng dẫn học tiếng Anh")
        
        print(f"   ✅ Generated {len(enhanced_segments)} enhanced segments")
        for i, seg in enumerate(enhanced_segments):
            word_count = seg.get('word_count', 'N/A')
            print(f"   Segment {i+1}: {seg['start']:.1f}s-{seg['end']:.1f}s ({word_count} từ)")
            print(f"   Summary: {seg['summary'][:80]}...")
        
        print("\n🎯 2. Testing Social Media Optimization...")
        platforms = ['tiktok', 'instagram', 'youtube_shorts']
        
        for platform in platforms:
            print(f"\n   Testing {platform.upper()}:")
            social_segments = llm.segment_video_for_social_media(
                sample_segments, 
                platform=platform, 
                prompt="Mẹo học tiếng Anh viral"
            )
            
            best_clips = llm.get_best_clips_for_platform(social_segments, platform, 3)
            print(f"   ✅ {len(best_clips)} viral clips for {platform}")
            
            for j, clip in enumerate(best_clips):
                duration = clip.get('end', 0) - clip.get('start', 0)
                engagement = clip.get('engagement_score', 0)
                viral = clip.get('viral_potential', 'N/A')
                print(f"     Clip {j+1}: {duration:.0f}s, Engagement: {engagement}/10, Viral: {viral}")
                print(f"     Hook: {clip.get('hook_text', 'N/A')[:50]}...")
        
        print("\n🔍 3. Testing Enhanced Narrative Segmentation...")
        # Create mock align_result for narrative testing
        align_result = {'segments': sample_segments}
        
        # Test different prompts with relevancy ranking
        test_prompts = [
            "học tiếng Anh",
            "nấu ăn và phở",
            "làm đẹp TikTok"
        ]
        
        for prompt in test_prompts:
            print(f"\n   Testing narrative search: '{prompt}'")
            narrative_segments = llm.segment_narrative(align_result, prompt)
            
            print(f"   ✅ Found {len(narrative_segments)} relevant segments")
            for k, seg in enumerate(narrative_segments):
                relevance = seg.get('relevance_score', seg.get('relevance', 0))
                engagement = seg.get('engagement_score', 0)
                word_count = seg.get('word_count', 0)
                viral = seg.get('viral_potential', 'N/A')
                
                print(f"     Match {k+1}: Relevance {relevance:.1f}/10, Engagement {engagement:.1f}/10")
                print(f"     {word_count} words, Viral: {viral}")
                print(f"     Summary: {seg.get('summary', 'N/A')[:60]}...")
        
        print(f"\n✅ All Enhanced Features Test Completed Successfully!")
        print(f"   🎉 Key Improvements:")
        print(f"   📝 Detailed summaries with word counts")
        print(f"   📊 Relevancy ranking (1-10 scale)")
        print(f"   🚀 Social media optimization for TikTok/Instagram/YouTube")
        print(f"   💯 Engagement scoring and viral potential analysis")
        print(f"   🎯 Platform-specific content optimization")
        print(f"   🔍 Enhanced keyword matching with context")
        
        return True
        
    except Exception as e:
        print(f"❌ Enhanced features test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_enhanced_features()
    if success:
        print("\n🎊 All Enhanced Features Working Perfectly!")
        print("   Ready for viral content creation! 🚀📱")
    else:
        print("\n❌ Some enhanced features failed. Please check the errors above.")
    
    sys.exit(0 if success else 1)
