from typing import Optional

from config import (
    ALIGNMENT_MODEL,
    WHISPER_DEVICE,
)


class TextAligner:
    """Text aligner class, used to align text with audio and generate SRT subtitles"""

    def __init__(self, language_code: Optional[str] = None):
        self.language_code = language_code or 'vi'  # The default language code is Vietnamese
        self.model = self._load_model()

    def _load_model(self):
        if ALIGNMENT_MODEL == 'whisperx':
            try:
                import whisperx
                print(f"Load WhisperX alignment model, language{self.language_code}")
                model = whisperx.load_align_model(
                    language_code=self.language_code, device=WHISPER_DEVICE)
                return model
            except ImportError:
                raise ImportError(
                    "WhisperX not installed. Please install with 'pip install whisperx'")
        else:
            raise ValueError(
                f"Unsupported forced alignment model: {ALIGNMENT_MODEL}")

    def align(self, segments: str, audio_path: str) -> str:
        """Align text with audio and generate SRT subtitles"""
        if ALIGNMENT_MODEL == 'whisperx':
            # Alignment with WhisperX
            import whisperx
            audio = whisperx.load_audio(audio_path)
            align_model, align_model_metadata = self.model
            result = whisperx.align(segments, align_model, align_model_metadata,
                                    audio, WHISPER_DEVICE,
                                    return_char_alignments=False)
            for segment in result["segments"]:
                segment.pop("words", None)
            return result
        else:
            raise ValueError(
                f"Unsupported forced alignment model: {ALIGNMENT_MODEL}")
