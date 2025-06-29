from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import gradio as gr
import uvicorn
import signal
import sys
import os
import shutil
import atexit

import config
from web.gradio_ui import create_gradio_interface
from web.api import router as api_router


import logging

# Block access logs
block_endpoints = "./"


class LogFilter(logging.Filter):
    def filter(self, record):
        if record.args and len(record.args) >= 3:
            if str(record.args[2]).startswith(block_endpoints):
                return False
        return True


uvicorn_logger = logging.getLogger("uvicorn.access")
uvicorn_logger.addFilter(LogFilter())


app = FastAPI()

# Cross-domain middleware
origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# Adding API Routes
app.include_router(api_router)

# Check GPU availability
try:
    import torch

    if torch.cuda.is_available():
        print("✅ If a GPU is detected to be available, GPU acceleration will be used")
    else:
        print("⚠️ No GPU detected, will run using CPU")
except ImportError:
    print("⚠️ Unable to import torch, GPU status unknown")

# Print the current configuration
print("Current Configuration:")
print(f"  Speech recognition processing module: {config.SPEECH_RECOGNIZER_TYPE}")
print(f"  Model size: {config.WHISPER_MODEL_SIZE}")
print(f"  Computing equipment: {config.WHISPER_DEVICE}")
print(f"  Calculation Type: {config.WHISPER_COMPUTE_TYPE}")
print(f"  Using GPU: {config.WHISPER_GPU_IDS}")
print(f"  Batch size: {config.WHISPER_BATCH_SIZE}")

# Creating the Gradio Interface
gradio_app = create_gradio_interface()
app = gr.mount_gradio_app(app, gradio_app, path="/web")

def cleanup_directories():
    """Clean up temporary and output directories"""
    try:
        if os.path.exists(config.TEMP_FOLDER):
            shutil.rmtree(config.TEMP_FOLDER)
            print(f"✅ Cleaned up {config.TEMP_FOLDER}")
        if os.path.exists(config.OUTPUT_FOLDER):
            shutil.rmtree(config.OUTPUT_FOLDER)
            print(f"✅ Cleaned up {config.OUTPUT_FOLDER}")
    except Exception as e:
        print(f"⚠️ Error during cleanup: {e}")

def signal_handler(signum, frame):
    """Handle termination signals"""
    print("\n🛑 Received termination signal, cleaning up...")
    cleanup_directories()
    sys.exit(0)

if __name__ == "__main__":
    # Register cleanup function to run on normal exit
    atexit.register(cleanup_directories)
    
    # Register signal handlers for Ctrl+C and other termination signals
    signal.signal(signal.SIGINT, signal_handler)  # Ctrl+C
    signal.signal(signal.SIGTERM, signal_handler)  # Termination signal
    
    try:
        # Start the application
        port = int(os.environ.get("PORT", 8860))
        uvicorn.run(app, host="0.0.0.0", port=port)
    except KeyboardInterrupt:
        print("\n🛑 Application interrupted by user")
        cleanup_directories()
    except Exception as e:
        print(f"❌ Application error: {e}")
        cleanup_directories()
        raise
