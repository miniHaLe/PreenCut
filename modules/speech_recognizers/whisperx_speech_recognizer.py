from typing import Optional
from modules.speech_recognizers.speech_recognizer import SpeechRecognizer
import whisperx


class WhisperXSpeechRecognizer(SpeechRecognizer):
    """WhisperX speech recognizer implementation with robust error handling."""
    
    def __init__(
            self,
            model_size: str,
            device: str,
            compute_type: str,
            device_index: list,
            batch_size: int,
            language: Optional[str] = None
    ):
        """Initialize WhisperX speech recognizer.
        
        Args:
            model_size: Model size (e.g., 'large-v3')
            device: Device type ('cuda' or 'cpu')
            compute_type: Compute precision ('float16' or 'float32')
            device_index: List of GPU indices to use
            batch_size: Batch size for processing
            language: Target language code
        """
        super().__init__(
            model_size,
            device,
            device_index=device_index,
            compute_type=compute_type,
            batch_size=batch_size,
            language=language
        )
        
        print(f"Loading the Whisper model: {self.model_size}")
        print(f"device = {self.device}")
        print(f"Model config: {self.model_size, self.device, self.compute_type, self.opts}")
        
        # Initialize the model with proper error handling
        self._load_model()
    
    def _load_model(self):
        """Load the WhisperX model with appropriate configuration."""
        asr_options = {
            "initial_prompt": "Yes, this sentence is for added punctuation.",
        }
        
        try:
            if self.device == 'cuda':
                self.model = whisperx.load_model(
                    self.model_size,
                    self.device,
                    device_index=self.device_index,
                    compute_type=self.compute_type,
                    asr_options=asr_options,
                    language=self.language
                )
            else:
                self.model = whisperx.load_model(
                    self.model_size,
                    self.device,
                    compute_type=self.compute_type,
                    asr_options=asr_options,
                    language=self.language
                )
            print(f"✅ WhisperX model loaded successfully")
                
        except Exception as e:
            print(f"❌ Failed to load WhisperX model: {e}")
            raise RuntimeError(f"WhisperX model initialization failed: {e}") from e

    def transcribe(self, audio_path: str):
        """Transcribe audio file to text.
        
        Args:
            audio_path: Path to the audio file
            
        Returns:
            Dictionary containing transcription results
        """
        # Validate audio file (inherited method)
        self.before_transcribe(audio_path)
        
        try:
            # Load audio data
            print(f"Loading audio data: {audio_path}")
            audio = whisperx.load_audio(audio_path)
            print(f"✅ Audio loaded successfully")
            
            # Perform transcription
            print(f"Starting transcription with batch size = {self.batch_size}")
            result = self.model.transcribe(
                audio,
                batch_size=self.batch_size,
            )
            
            print(f"✅ Transcription completed successfully")
            print(f"Result summary: {len(result.get('segments', []))} segments detected")
            return result
            
        except Exception as e:
            print(f"❌ Transcription failed: {e}")
            raise RuntimeError(f"WhisperX transcription failed: {e}") from e
