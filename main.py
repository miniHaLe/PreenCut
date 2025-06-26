from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import gradio as gr
import uvicorn

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

if __name__ == "__main__":
    # Start the application
    uvicorn.run(app, host="localhost", port=8860)
