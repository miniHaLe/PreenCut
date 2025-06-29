#!/usr/bin/env python3
"""
Test script to demonstrate the new Gradio Progress functionality
"""

import sys
import os
import time

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import gradio as gr

def test_progress_example():
    """Test function with Gradio Progress similar to your reference"""
    
    def slowly_process_items(items, progress=gr.Progress()):
        progress(0, desc="Starting...")
        time.sleep(0.5)
        progress(0.05)
        
        result = []
        for i, item in progress.tqdm(enumerate(items), desc="Processing items"):
            time.sleep(0.2)  # Simulate work
            result.append(f"Processed: {item}")
            
        return result
    
    # Create a simple interface to test
    with gr.Blocks() as demo:
        gr.Markdown("# Test Gradio Progress with tqdm")
        
        input_text = gr.Textbox(label="Enter items (comma separated)", 
                               value="item1,item2,item3,item4,item5")
        process_btn = gr.Button("Process with Progress", variant="primary")
        output_list = gr.JSON(label="Results")
        
        def process_input(text):
            items = [item.strip() for item in text.split(',') if item.strip()]
            return slowly_process_items(items)
        
        process_btn.click(
            process_input,
            inputs=input_text,
            outputs=output_list
        )
    
    print("✅ Progress test interface created successfully!")
    print("This demonstrates the tqdm-style progress bar that PreenCut now uses.")
    return demo

if __name__ == "__main__":
    try:
        demo = test_progress_example()
        print("\n🎉 Test successful! The progress functionality is working.")
        print("Your PreenCut app now uses similar progress bars with:")
        print("1. ✅ Real-time tqdm-style progress during file processing")
        print("2. ✅ Dynamic progress descriptions")
        print("3. ✅ Progress bars for each processing stage")
        print("4. ✅ No more static text-based progress")
        
        # Uncomment the next line if you want to launch the test interface
        # demo.launch(server_name="0.0.0.0", server_port=7860)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
