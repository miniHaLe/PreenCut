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
            except ImportError as ie:
                if "Wav2Vec2ForCTC" in str(ie):
                    print(f"⚠️  WhisperX alignment model incompatible with current transformers version. Alignment will be skipped.")
                    return None
                else:
                    raise ImportError(
                        "WhisperX not installed. Please install with 'pip install whisperx'")
            except Exception as e:
                print(f"⚠️  Could not load WhisperX alignment model: {e}. Alignment will be skipped.")
                return None
        else:
            raise ValueError(
                f"Unsupported forced alignment model: {ALIGNMENT_MODEL}")

    def align(self, segments: list, audio_path: str) -> dict:
        """Align text with audio and generate SRT subtitles with robust error handling"""
        if ALIGNMENT_MODEL == 'whisperx':
            # Check if model is available
            if self.model is None:
                print("⚠️  WhisperX alignment model not available, returning original segments")
                return {"segments": segments, "language": self.language_code}
                
            try:
                # Alignment with WhisperX
                import whisperx
                import torch
                
                print(f"Loading audio for alignment: {audio_path}")
                audio = whisperx.load_audio(audio_path)
                align_model, align_model_metadata = self.model
                
                print(f"Starting WhisperX alignment for {len(segments)} segments")
                
                # Preprocess segments to ensure proper format and handle tensor/string issues
                processed_segments = self._preprocess_segments_for_alignment(segments)
                
                # Attempt alignment with error handling
                result = whisperx.align(processed_segments, align_model, align_model_metadata,
                                        audio, WHISPER_DEVICE,
                                        return_char_alignments=False)
                
                # Clean up word-level alignments to save memory
                for segment in result["segments"]:
                    segment.pop("words", None)
                
                print(f"WhisperX alignment completed successfully")
                return result
                
            except Exception as e:
                error_msg = str(e)
                print(f"WhisperX alignment failed: {error_msg}")
                
                # Common error types and solutions
                if "tensors used as indices must be long, int, byte or bool tensors" in error_msg:
                    print("Tensor type error in WhisperX - fixing tensor types and retrying...")
                    try:
                        # Try to fix tensor type issues and retry
                        fixed_result = self._retry_alignment_with_type_fixes(segments, audio_path)
                        if fixed_result:
                            return fixed_result
                    except Exception as retry_error:
                        print(f"Retry with type fixes also failed: {retry_error}")
                elif "string indices must be integers" in error_msg:
                    print("String index error - fixing data types and retrying...")
                    try:
                        fixed_result = self._retry_alignment_with_string_fixes(segments, audio_path)
                        if fixed_result:
                            return fixed_result
                    except Exception as retry_error:
                        print(f"Retry with string fixes also failed: {retry_error}")
                elif "backtrack failed" in error_msg:
                    print("Alignment backtrack failed - using original timestamps")
                elif "IndexError" in error_msg:
                    print("Index error in alignment - falling back to original segments")
                else:
                    print(f"Unknown alignment error: {error_msg}")
                
                # Return original segments with original structure intact
                return {
                    "segments": segments,
                    "language": getattr(segments[0] if segments else {}, 'language', self.language_code),
                    "alignment_failed": True,
                    "alignment_error": error_msg
                }
                
        else:
            raise ValueError(f"Unsupported forced alignment model: {ALIGNMENT_MODEL}")

    def _preprocess_segments_for_alignment(self, segments: list) -> list:
        """Preprocess segments to ensure proper format for WhisperX alignment"""
        processed_segments = []
        
        for segment in segments:
            # Ensure all required fields are present and properly typed
            processed_segment = {
                "start": float(segment.get("start", 0)),
                "end": float(segment.get("end", 0)),
                "text": str(segment.get("text", "")).strip()
            }
            
            # Only include non-empty text segments
            if processed_segment["text"]:
                processed_segments.append(processed_segment)
        
        return processed_segments
    
    def _retry_alignment_with_type_fixes(self, segments: list, audio_path: str) -> dict:
        """Retry alignment with tensor type fixes"""
        import whisperx
        import torch
        
        try:
            print("Attempting alignment with tensor type fixes...")
            audio = whisperx.load_audio(audio_path)
            align_model, align_model_metadata = self.model
            
            # Ensure segments are properly formatted with correct types
            fixed_segments = []
            for segment in segments:
                fixed_segment = {
                    "start": torch.tensor(float(segment.get("start", 0)), dtype=torch.float32),
                    "end": torch.tensor(float(segment.get("end", 0)), dtype=torch.float32),
                    "text": str(segment.get("text", "")).strip()
                }
                if fixed_segment["text"]:
                    fixed_segments.append(fixed_segment)
            
            # Convert back to proper format for alignment
            alignment_input = {
                "segments": [
                    {
                        "start": float(seg["start"]),
                        "end": float(seg["end"]),
                        "text": seg["text"]
                    } for seg in fixed_segments
                ]
            }
            
            result = whisperx.align(alignment_input, align_model, align_model_metadata,
                                  audio, WHISPER_DEVICE, return_char_alignments=False)
            
            print("Tensor type fix successful!")
            return result
            
        except Exception as e:
            print(f"Tensor type fix failed: {e}")
            return None
    
    def _retry_alignment_with_string_fixes(self, segments: list, audio_path: str) -> dict:
        """Retry alignment with string type fixes"""
        import whisperx
        
        try:
            print("Attempting alignment with string type fixes...")
            audio = whisperx.load_audio(audio_path)
            align_model, align_model_metadata = self.model
            
            # Ensure all data is properly converted to expected types
            clean_segments = []
            for i, segment in enumerate(segments):
                clean_segment = {}
                
                # Handle start time
                start_val = segment.get("start", 0)
                if isinstance(start_val, str):
                    start_val = float(start_val)
                clean_segment["start"] = float(start_val)
                
                # Handle end time
                end_val = segment.get("end", 0)
                if isinstance(end_val, str):
                    end_val = float(end_val)
                clean_segment["end"] = float(end_val)
                
                # Handle text
                text_val = segment.get("text", "")
                if not isinstance(text_val, str):
                    text_val = str(text_val)
                clean_segment["text"] = text_val.strip()
                
                # Only include segments with valid text
                if clean_segment["text"] and clean_segment["end"] > clean_segment["start"]:
                    clean_segments.append(clean_segment)
            
            if not clean_segments:
                print("No valid segments after cleaning")
                return None
            
            alignment_input = {"segments": clean_segments}
            
            result = whisperx.align(alignment_input, align_model, align_model_metadata,
                                  audio, WHISPER_DEVICE, return_char_alignments=False)
            
            print("String type fix successful!")
            return result
            
        except Exception as e:
            print(f"String type fix failed: {e}")
            return None
