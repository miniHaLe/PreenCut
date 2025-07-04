import faster_whisper
import gc

from modules.speech_recognizers.speech_recognizer import SpeechRecognizer


def cleanup_whisper_gpu_memory():
    """Simple GPU VRAM cleanup function specifically for Whisper model usage."""
    try:
        # Force garbage collection first
        gc.collect()
        
        # Clear GPU cache if PyTorch is available
        try:
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except ImportError:
            pass  # PyTorch not available, skip GPU cleanup
            
    except Exception:
        pass  # Silent cleanup failure


class FasterWhisperSpeechRecognizer(SpeechRecognizer):
    beam_size = 5

    def __init__(
            self,
            model_size,
            device,
            device_index,
            compute_type,
            batch_size=32,
            beam_size=5,
            language="vi"
    ):
        super().__init__(model_size, device, device_index=device_index, compute_type=compute_type,
                         batch_size=batch_size, language=language)
        self.language = language
        if beam_size > 0:
            self.beam_size = beam_size
        print(f"Loading the Whisper model: {self.model_size}")
        print(f"device = {self.device}")
        print(f"{self.model_size, self.device, self.compute_type, self.opts}")
        if self.device == 'cpu':
            self.model = faster_whisper.WhisperModel(self.model_size, device=self.device,
                                                     compute_type=self.compute_type)
        else:
            self.model = faster_whisper.WhisperModel(self.model_size,
                                                     device=self.device,
                                                     device_index=self.device_index,
                                                     compute_type=self.compute_type)

    def transcribe(self, audio_path: str):
        """Transcribe audio files to text"""
        # Make sure the audio file exists
        self.before_transcribe(audio_path)
        print(f"get audio data: {audio_path}")
        print(f"batch size = {self.batch_size}")
        
        try:
            audio = faster_whisper.decode_audio(audio_path)
            print("load audio success")
            segments, info = self.model.transcribe(
                audio,
                beam_size=self.beam_size,
                language=self.language
            )
            segment_list = []
            for segment in segments:
                # print("[%.2fs -> %.2fs] %s" % (segment.start, segment.end, segment.text))
                # Convert Segment object to dictionary format for compatibility with WhisperX
                segment_dict = {
                    "start": segment.start,
                    "end": segment.end,
                    "text": segment.text
                }
                segment_list.append(segment_dict)
            # format result
            result = {"language": info.language, "segments": segment_list}
            return result
        finally:
            # Clean up GPU memory after Whisper model inference
            cleanup_whisper_gpu_memory()
