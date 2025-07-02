import os


class SpeechRecognizer:
    model_size = 'large_v3'
    device = 'cuda:1'
    compute_type = 'float16'
    batch_size = 16
    language = "vi"
    device_index = []
    opts = {}

    def __init__(self, model_size, device, device_index, compute_type, batch_size, language, opts={}):
        self.model_size = model_size
        self.device = device
        self.device_index = device_index
        self.compute_type = compute_type
        self.batch_size = batch_size
        self.language = language

    @staticmethod
    def before_transcribe(audio_path):
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"audio file not found: {audio_path}")

    def transcribe(self, audio_path):
        pass
