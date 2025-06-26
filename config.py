import os
import torch

# Set the Gradio temporary directory
os.environ['GRADIO_TEMP_DIR'] = './data/tmp/gradio'


def get_available_gpus():
    """Get all available GPU devices"""
    if torch.cuda.is_available():
        return list(range(torch.cuda.device_count()))
    return []


def get_device_config():
    """Setting device configuration"""
    gpus = get_available_gpus()

    # Check if the GPU is specified by the environment variable
    cuda_visible = os.getenv('CUDA_VISIBLE_DEVICES', '')
    if cuda_visible:
        try:
            # Parsing GPU index from environment variables
            selected_gpus = [int(x.strip()) for x in cuda_visible.split(',') if
                             x.strip()]
            return 'cuda', selected_gpus
        except ValueError:
            pass

    # If not specified but a GPU is detected
    if gpus:
        return 'cuda', gpus

    # Default use of CPU
    return 'cpu', []


# File upload configuration
ALLOWED_EXTENSIONS = ['mp4', 'avi', 'mov', 'mkv', 'ts', 'mxf', 'mp3', 'wav',
                      'flac']
MAX_FILE_SIZE = 10 * 1024 * 1024 * 1024  # 10GB
MAX_FILE_NUMBERS = 10  # Maximum number of files

# Temporary folder
TEMP_FOLDER = "./temp"

# Output Folder
OUTPUT_FOLDER = "./output"

# Speech recognition model configuration
SPEECH_RECOGNIZER_TYPE = 'whisperx' # whisperx, faster-whisper

DEVICE_TYPE, AVAILABLE_GPUS = get_device_config()
# Whisper Configuration
WHISPER_MODEL_SIZE = 'large-v3'  # Model size (tiny, base, small, medium, large, large-v2, large-v3)
WHISPER_DEVICE = DEVICE_TYPE
WHISPER_GPU_IDS = AVAILABLE_GPUS
WHISPER_COMPUTE_TYPE = 'float16' if WHISPER_DEVICE == 'cuda' else 'float32'  # float16, float32, int8
WHISPER_BATCH_SIZE = 16  # Batch size

# Language settings - Force Vietnamese detection
WHISPER_LANGUAGE = 'vi'  # Vietnamese language code
WHISPER_AUTO_DETECT_LANGUAGE = False  # Disable automatic language detection

FASTER_WHISPER_BEAM_SIZE = 5

# Speech-to-text alignment model
ENABLE_ALIGNMENT = True  # Whether to enable alignment
ALIGNMENT_MODEL = 'whisperx'  # Alignment model used

# Ollama LLM Configuration
LLM_MODEL_OPTIONS = [
    {
        "model": "qwen3:8b-q8_0",
        "base_url": "http://localhost:11434",
        "label": "Qwen3 8B",
        "max_tokens": 4096,
        "temperature": 0.3,
    },
    {
        "model": "hf.co/unsloth/gemma-3-27b-it-qat-GGUF:Q8_K_XL",
        "base_url": "http://localhost:11434",
        "label": "Gemma3 27B",
        "max_tokens": 4096,
        "temperature": 0.3,
    }
]

# Alternative configuration for mixed OpenAI API + Ollama setup
# Uncomment and modify if you want to keep some OpenAI API models alongside Ollama
"""
LLM_MODEL_OPTIONS = [
    # Ollama models (local)
    {
        "model": "llama3.1:8b",
        "base_url": "http://localhost:11434",
        "label": "Llama 3.1 8B (Ollama)",
        "max_tokens": 4096,
        "temperature": 0.3,
        "type": "ollama"
    },
    {
        "model": "qwen2.5:7b",
        "base_url": "http://localhost:11434",
        "label": "Qwen 2.5 7B (Ollama)",
        "max_tokens": 4096,
        "temperature": 0.3,
        "type": "ollama"
    },
    # OpenAI API compatible models
    {
        "model": "deepseek-v3-0324",
        "base_url": "https://api.lkeap.cloud.tencent.com/v1",
        "api_key_env_name": "sk-b1aa3a0cffd44265bbc89334a8b79a66",
        "label": "DeepSeek-V3-0324 (API)",
        "max_tokens": 4096,
        "temperature": 0.3,
        "type": "openai"
    }
]
"""

# Ollama configuration
OLLAMA_DEFAULT_HOST = "localhost"
OLLAMA_DEFAULT_PORT = 11434
OLLAMA_TIMEOUT = 120  # seconds
OLLAMA_KEEP_ALIVE = "5m"  # Keep model loaded for 5 minutes after last request

# Helper function to get Ollama base URL
def get_ollama_url(host=OLLAMA_DEFAULT_HOST, port=OLLAMA_DEFAULT_PORT):
    """Generate Ollama API base URL"""
    return f"http://{host}:{port}"

# Helper function to check if a model is available in Ollama
def check_ollama_model_availability():
    """Check which models are actually available in your Ollama installation"""
    import requests
    try:
        url = get_ollama_url()
        response = requests.get(f"{url}/api/tags", timeout=5)
        if response.status_code == 200:
            models = response.json().get("models", [])
            available_models = [model["name"] for model in models]
            print(f"Available Ollama models: {available_models}")
            return available_models
        else:
            print(f"Failed to connect to Ollama: HTTP {response.status_code}")
            return []
    except Exception as e:
        print(f"Error checking Ollama models: {e}")
        return []

# Create the necessary directories
for folder in [TEMP_FOLDER, OUTPUT_FOLDER]:
    os.makedirs(folder, exist_ok=True)

# Optional: Check available models on startup
if __name__ == "__main__":
    print("Checking available Ollama models...")
    check_ollama_model_availability()