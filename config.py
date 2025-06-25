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
MAX_FILE_NUMBERS = 10  # 最大文件数量

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

FASTER_WHISPER_BEAM_SIZE = 5



# Speech-to-text alignment model
ENABLE_ALIGNMENT = True  # Whether to enable alignment
ALIGNMENT_MODEL = 'whisperx'  # Alignment model used

# OpenAI API Configuration
LLM_MODEL_OPTIONS = [
    {
        "model": "deepseek-v3-0324",
        "base_url": "https://api.lkeap.cloud.tencent.com/v1",
        "api_key_env_name": "DEEPSEEK_V3_API_KEY",
        "label": "DeepSeek-V3-0324",
        "max_tokens": 4096,
        "temperature": 0.3,
    },
    {
        "model": "doubao-1-5-pro-32k-250115",
        "base_url": "https://ark.cn-beijing.volces.com/api/v3",
        "api_key_env_name": "DOUBAO_1_5_PRO_API_KEY",
        "label": "Bean buns",
        "max_tokens": 4096,
        "temperature": 0.3,
    }
]

# Create the necessary directories
for folder in [TEMP_FOLDER, OUTPUT_FOLDER]:
    os.makedirs(folder, exist_ok=True)
