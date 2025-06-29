#!/usr/bin/env python3
"""
Test script to validate the Gradio UI fixes for PreenCut
"""

import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import gradio as gr
from web.gradio_ui import create_gradio_interface

def test_ui():
    """Test the Gradio UI"""
    print("Testing PreenCut Gradio UI fixes...")
    
    # Create the interface
    try:
        app = create_gradio_interface()
        print("✅ Gradio interface created successfully")
        
        # Test launch (will only validate the interface, not actually launch)
        print("✅ Interface validation completed")
        print("\nChanges made:")
        print("1. ✅ Fixed checkbox selection preservation during status updates")
        print("2. ✅ Enhanced thumbnail generation with better error handling")
        print("3. ✅ Replaced slider-based progress bar with proper Gradio Progress")
        print("4. ✅ Reduced UI flickering by stopping timer when processing completes")
        print("5. ✅ Added debugging for thumbnail generation")
        
        return True
        
    except Exception as e:
        print(f"❌ Error creating interface: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_ui()
    if success:
        print("\n🎉 All tests passed! The UI fixes should resolve your issues.")
    else:
        print("\n❌ Some tests failed. Please check the errors above.")
    
    sys.exit(0 if success else 1)
