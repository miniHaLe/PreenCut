import json
import requests
from config import LLM_MODEL_OPTIONS
from typing import List, Dict, Optional, Any, Union
import re


class LLMProcessor:
    def __init__(self, llm_model: str):
        for model in LLM_MODEL_OPTIONS:
            if model['label'] == llm_model:
                # Ollama typically runs on localhost:11434
                self.base_url = model.get('base_url', 'http://localhost:11434')
                self.model = model['model']
                self.temperature = model.get('temperature', 0.3)
                self.max_tokens = model.get('max_tokens', 4096)
                break

        if not hasattr(self, 'base_url'):
            raise ValueError(
                f"Unsupported LLM model: {llm_model}. Available models: "
                f"{', '.join([m['label'] for m in LLM_MODEL_OPTIONS])}"
            )

    def _call_ollama(self, messages: List[Dict], format_schema: Optional[Dict[str, Any]] = None) -> str:
        """Make API call to Ollama with optional structured output format"""
        # Combine system and user messages for Ollama
        prompt = ""
        for message in messages:
            if message["role"] == "system":
                prompt += f"{message['content']}\n\n"
            elif message["role"] == "user":
                prompt += f"{message['content']}\n\n"
        
        # Prepare the payload for Ollama API
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": self.temperature,
                "num_predict": self.max_tokens,
                "top_p": 0.9,
                "repeat_penalty": 1.1
            }
        }
        
        # Add format schema if provided
        if format_schema:
            # For structured output with schema
            payload["format"] = format_schema
            print(f"[DEBUG] Using structured output schema: {json.dumps(format_schema)[:200]}...")
        else:
            # For basic JSON format, use the API parameter
            payload["options"]["format"] = "json"
            print(f"[DEBUG] Using basic JSON format")
            
        print(f"[DEBUG] Sending request to {self.base_url}/api/generate")
        print(f"[DEBUG] Model: {self.model}, Using format schema: {format_schema is not None}")
            
        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=120  # 2 minute timeout for longer responses
            )
            
            print(f"[DEBUG] Response status: {response.status_code}")
            
            if response.status_code != 200:
                print(f"[DEBUG] Response content: {response.text}")
                response.raise_for_status()
            
            result = response.json()
            response_text = result.get("response", "")
            
            if not response_text:
                raise ValueError("Empty response from Ollama")
                
            return response_text
            
        except requests.exceptions.RequestException as e:
            raise ValueError(f"Error calling Ollama API: {str(e)}")
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON response from Ollama: {str(e)}")

    def segment_video(self, subtitles, prompt: Optional[str] = None) -> List[Dict]:
        """Use Ollama to segment videos based on subtitle content"""
        
        # Handle both string and list inputs for subtitles
        if isinstance(subtitles, list):
            subtitle_text = '\n'.join(str(item) for item in subtitles)
        else:
            subtitle_text = str(subtitles)
        
        # Define the schema for video segments
        segments_schema = {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "start": {
                        "type": "number",
                        "description": "Thời gian bắt đầu của phân đoạn tính bằng giây"
                    },
                    "end": {
                        "type": "number",
                        "description": "Thời gian kết thúc của phân đoạn tính bằng giây"
                    },
                    "summary": {
                        "type": "string",
                        "description": "Tóm tắt ngắn gọn về nội dung của phân đoạn video (PHẢI VIẾT BẰNG TIẾNG VIỆT, MIÊU TẢ NHƯ THỂ ĐANG XEM VIDEO)"
                    },
                    "tags": {
                        "type": "array",
                        "items": {
                            "type": "string"
                        },
                        "description": "Các từ khóa hoặc cụm từ đặc trưng cho phân đoạn video (PHẢI VIẾT BẰNG TIẾNG VIỆT)"
                    }
                },
                "required": ["start", "end", "summary", "tags"]
            }
        }
        
        # Build system prompt with explicit JSON format instructions
        system_prompt = (
            "Bạn là trợ lý biên tập video chuyên nghiệp. Bạn phải phân tích nội dung video và trả về các phân đoạn video. "
            "HƯỚNG DẪN QUAN TRỌNG:\n"
            "1. Phân tích nội dung và tạo tối đa 10 phân đoạn video có ý nghĩa\n"
            "2. Mỗi phân đoạn phải có thời gian bắt đầu, thời gian kết thúc, tóm tắt và các thẻ\n"
            "3. PHẢI VIẾT TẤT CẢ TÓM TẮT VÀ THẺ BẰNG TIẾNG VIỆT, KHÔNG ĐƯỢC DÙNG TIẾNG ANH\n"
            "4. Thời gian phải tính bằng giây dưới dạng số\n"
            "5. Trả về kết quả theo định dạng JSON được chỉ định\n"
            "6. QUAN TRỌNG: Khi viết tóm tắt, hãy miêu tả nội dung như thể bạn đang xem video, KHÔNG đề cập đến 'văn bản', 'phụ đề', 'bản ghi' hay 'người nói'. Thay vào đó, hãy miêu tả những gì đang diễn ra trong video."
        )

        # User prompt (used if there is a custom prompt)
        user_prompt = (
            "Đây là nội dung bạn cần phân tích trong video:\n"
            f"{prompt}\n\n"
            "---\n"
            "Phân tích nội dung video và tạo tối đa 10 phân đoạn video.\n"
            "Mỗi phân đoạn cần: thời gian bắt đầu (giây), thời gian kết thúc (giây), tóm tắt (một câu), thẻ (1-3 từ).\n"
            "TẤT CẢ TÓM TẮT VÀ THẺ PHẢI ĐƯỢC VIẾT BẰNG TIẾNG VIỆT, KHÔNG ĐƯỢC DÙNG TIẾNG ANH.\n"
            "QUAN TRỌNG: Khi viết tóm tắt, hãy miêu tả nội dung như thể bạn đang xem video, KHÔNG đề cập đến 'văn bản', 'phụ đề', 'bản ghi' hay 'người nói'. Thay vào đó, hãy miêu tả những gì đang diễn ra trong video.\n"
        )

        # Combined complete prompt
        full_prompt = f"{user_prompt}\n\nNội dung video:\n{subtitle_text}"

        print(f"[DEBUG] Calling Ollama with model: {self.model}")
        print(f"[DEBUG] Subtitle length: {len(subtitle_text)} characters")

        # Try with structured output format
        try:
            result = self._call_ollama([
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": full_prompt}
            ], format_schema=segments_schema)
            
            print(f"[DEBUG] Raw Ollama response (first 500 chars): {result[:500]}")
            
            # Try to parse directly as JSON
            try:
                segments = json.loads(result)
                if isinstance(segments, list):
                    print(f"[DEBUG] Successfully parsed {len(segments)} segments directly")
                    return self._validate_segments(segments)
            except json.JSONDecodeError:
                print(f"[DEBUG] Direct JSON parsing failed, trying validation")
                
            # Try validation with cleanup
            segments = self._parse_and_validate_response(result)
            if segments:
                print(f"[DEBUG] Successfully parsed {len(segments)} segments")
                return segments
                
        except Exception as e:
            print(f"[DEBUG] Structured format failed: {str(e)}")
            
        # Fallback: Try without schema but with stricter prompt
        try:
            print("[DEBUG] Trying fallback without schema...")
            
            # More aggressive prompt for fallback
            strict_prompt = (
                "QUAN TRỌNG: Chỉ trả lời bằng một mảng JSON. Không suy nghĩ thành tiếng. "
                "Không sử dụng thẻ <think>. Bắt đầu ngay lập tức với [ và kết thúc với ]. "
                "Tất cả các trường summary và tags phải bằng tiếng Việt. "
                "Khi viết tóm tắt, hãy miêu tả nội dung như thể bạn đang xem video, không đề cập đến văn bản hay phụ đề.\n"
                f"{user_prompt}\n\nNội dung video:\n{subtitle_text}"
            )
            
            result = self._call_ollama([
                {"role": "user", "content": strict_prompt}
            ], format_schema=None)
            
            print(f"[DEBUG] Fallback response (first 500 chars): {result[:500]}")
            
            segments = self._parse_and_validate_response(result)
            if segments:
                print(f"[DEBUG] Fallback successful with {len(segments)} segments")
                return segments
                
        except Exception as e:
            print(f"[DEBUG] Fallback also failed: {str(e)}")
            
        # Last resort: Return a simple default segmentation
        print("[DEBUG] Using default segmentation as last resort")
        return self._create_default_segments(subtitle_text)
        
    def _validate_segments(self, segments: List[Dict]) -> List[Dict]:
        """Validate and clean up segments"""
        if not isinstance(segments, list):
            return []
            
        valid_segments = []
        for i, segment in enumerate(segments):
            try:
                if not isinstance(segment, dict):
                    continue
                    
                # Check required keys
                if 'start' not in segment or 'end' not in segment:
                    continue
                    
                # Ensure required fields exist
                segment.setdefault('summary', f"Phân đoạn {i+1}")
                segment.setdefault('tags', ['phân_đoạn'])
                
                # Check if summary is in English and translate if needed
                segment['summary'] = self._ensure_vietnamese(segment['summary'])
                
                # Ensure tags are in Vietnamese
                if isinstance(segment['tags'], list):
                    segment['tags'] = [self._ensure_vietnamese(tag) for tag in segment['tags']]
                elif isinstance(segment['tags'], str):
                    segment['tags'] = [self._ensure_vietnamese(segment['tags'])]
                else:
                    segment['tags'] = ['phân_đoạn']
                
                # Type conversion
                segment['start'] = float(segment['start'])
                segment['end'] = float(segment['end'])
                
                # Validate time range
                if segment['start'] >= segment['end']:
                    continue
                    
                valid_segments.append(segment)
            except Exception:
                continue
                
        return valid_segments

    def _ensure_vietnamese(self, text: str) -> str:
        """Ensure text is in Vietnamese, attempt basic translation if it appears to be in English"""
        # Simple check for whether text might be English - check for common English words
        english_words = ['the', 'and', 'is', 'in', 'to', 'of', 'for', 'with', 'this', 'that', 'on', 'at']
        
        # Count English words in the text
        word_count = sum(1 for word in text.lower().split() if word in english_words)
        
        # If text appears to be in English (has multiple English common words), translate
        if word_count >= 2:
            print(f"[DEBUG] Text appears to be in English, attempting translation: {text[:30]}...")
            try:
                # First try translation via LLM
                translation = self._translate_via_llm(text)
                return translation
            except:
                # If LLM translation fails, use a simple mapping for common words
                return self._simple_translate(text)
        
        return text
    
    def _translate_via_llm(self, text: str) -> str:
        """Use the LLM to translate text from English to Vietnamese"""
        system_prompt = (
            "Bạn là một chuyên gia dịch thuật giỏi. "
            "Chuyển dịch văn bản từ tiếng Anh sang tiếng Việt. "
            "Chỉ trả về bản dịch tiếng Việt, không kèm giải thích hoặc nội dung khác."
        )
        
        user_prompt = f"Dịch câu sau sang tiếng Việt: \"{text}\""
        
        try:
            result = self._call_ollama([
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ], format_schema=None)
            
            # Clean up the response
            result = result.strip()
            if result.startswith('"') and result.endswith('"'):
                result = result[1:-1]
                
            print(f"[DEBUG] Translated from '{text}' to '{result}'")
            return result
        except:
            # Fall back to simple translation if LLM call fails
            return self._simple_translate(text)
    
    def _simple_translate(self, text: str) -> str:
        """Attempt a simple replacement of common English words with Vietnamese equivalents"""
        # Simple dictionary of common English words to Vietnamese
        translations = {
            'the': 'các',
            'and': 'và',
            'is': 'là',
            'in': 'trong',
            'of': 'của',
            'to': 'đến',
            'for': 'cho',
            'with': 'với',
            'this': 'này',
            'that': 'đó',
            'on': 'trên',
            'at': 'tại',
            'discussion': 'thảo luận',
            'introduction': 'giới thiệu',
            'conclusion': 'kết luận',
            'summary': 'tóm tắt',
            'segment': 'phân đoạn'
        }
        
        # Basic word replacement
        words = text.split()
        translated_words = []
        
        for word in words:
            lower_word = word.lower()
            if lower_word in translations:
                # Preserve capitalization
                if word[0].isupper() and len(word) > 1:
                    translated_words.append(translations[lower_word].capitalize())
                else:
                    translated_words.append(translations[lower_word])
            else:
                translated_words.append(word)
        
        return " ".join(translated_words)

    def _parse_and_validate_response(self, result: str) -> Optional[List[Dict]]:
        """Parse and validate the response from Ollama"""
        try:
            # Clean up the response
            result = result.strip()
            
            # Remove <think> tags and their content
            think_pattern = r'<think>.*?</think>'
            result = re.sub(think_pattern, '', result, flags=re.DOTALL)
            result = result.strip()
            
            # Remove possible markdown code blocks
            if result.startswith("```json"):
                result = result[7:]
                if result.endswith("```"):
                    result = result[:-3]
            elif result.startswith("```"):
                result = result[3:]
                if result.endswith("```"):
                    result = result[:-3]
            
            result = result.strip()
            
            # Try to parse as JSON directly first
            try:
                parsed_data = json.loads(result)
                
                # If it's an array, use it directly
                if isinstance(parsed_data, list):
                    print(f"[DEBUG] Successfully parsed JSON array directly")
                    segments = parsed_data
                # If it's a dictionary, look for array fields
                elif isinstance(parsed_data, dict):
                    print(f"[DEBUG] Response is a dictionary, looking for array fields")
                    # Look for common array fields that might contain segments
                    array_fields = ['segments', 'results', 'items', 'data']
                    for field in array_fields:
                        if field in parsed_data and isinstance(parsed_data[field], list):
                            print(f"[DEBUG] Found array in field '{field}'")
                            segments = parsed_data[field]
                            break
                    else:
                        # If no array field found, try to extract the first array value
                        array_values = [v for v in parsed_data.values() if isinstance(v, list)]
                        if array_values:
                            print(f"[DEBUG] Using first array value found in dictionary")
                            segments = array_values[0]
                        else:
                            # Last resort: convert dictionary to a single-item array
                            print(f"[DEBUG] Converting dictionary to single-item array")
                            segments = [parsed_data]
                else:
                    print(f"[DEBUG] Response is not a list or dict: {type(parsed_data)}")
                    return None
            except json.JSONDecodeError:
                # If direct parsing fails, try to extract JSON array from text
                print(f"[DEBUG] Direct parsing failed, trying to extract JSON array")
                # Try to find JSON array in the response
                start_idx = result.find('[')
                end_idx = result.rfind(']')
                
                if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                    json_str = result[start_idx:end_idx + 1]
                    print(f"[DEBUG] Extracted JSON: {json_str[:200]}...")
                    segments = json.loads(json_str)
                else:
                    print(f"[DEBUG] Could not find JSON array in response")
                    return None
            
            # Validate the structure
            if not isinstance(segments, list):
                print(f"[DEBUG] Segments is not a list: {type(segments)}")
                return None
            
            if len(segments) == 0:
                print("[DEBUG] Empty segments list")
                return None
                
            # Validate each segment
            valid_segments = []
            for i, segment in enumerate(segments):
                if not isinstance(segment, dict):
                    print(f"[DEBUG] Segment {i} is not a dictionary: {type(segment)}")
                    continue
                
                # Check required keys and fix missing ones
                if 'start' not in segment or 'end' not in segment:
                    print(f"[DEBUG] Segment {i} missing start/end times")
                    continue
                    
                # Ensure required fields exist with defaults
                segment.setdefault('summary', f"Phân đoạn {i+1}")
                segment.setdefault('tags', ['phân_đoạn'])
                
                # Type conversion and validation
                try:
                    segment['start'] = float(segment['start'])
                    segment['end'] = float(segment['end'])
                    if not isinstance(segment['summary'], str):
                        segment['summary'] = str(segment['summary'])
                    if not isinstance(segment['tags'], list):
                        segment['tags'] = [str(segment['tags'])] if segment['tags'] else ['phân_đoạn']
                    
                    # Basic time validation
                    if segment['start'] >= segment['end']:
                        print(f"[DEBUG] Invalid time range for segment {i}: {segment['start']} >= {segment['end']}")
                        continue
                        
                    valid_segments.append(segment)
                    
                except (ValueError, TypeError) as e:
                    print(f"[DEBUG] Type conversion error for segment {i}: {e}")
                    continue
            
            print(f"[DEBUG] Validated {len(valid_segments)} out of {len(segments)} segments")
            return valid_segments if valid_segments else None
            
        except json.JSONDecodeError as e:
            print(f"[DEBUG] JSON decode error: {e}")
            print(f"[DEBUG] Problematic content: {result[:200]}...")
            return None
        except Exception as e:
            print(f"[DEBUG] Validation error: {e}")
            return None

    def _create_default_segments(self, subtitles) -> List[Dict]:
        """Create a simple default segmentation when LLM fails"""
        print("[DEBUG] Creating default segments")
        
        # Handle both string and list inputs
        if isinstance(subtitles, list):
            # If it's a list, join it into a string or process each item
            subtitle_text = '\n'.join(str(item) for item in subtitles)
        else:
            # If it's already a string, use it as is
            subtitle_text = str(subtitles)
        
        # Try to extract time information from subtitles
        time_pattern = r'(\d{1,2}:\d{2}:\d{2}(?:\.\d{3})?|\d+(?:\.\d+)?)'
        times = []
        
        for line in subtitle_text.split('\n'):
            matches = re.findall(time_pattern, line)
            for match in matches:
                try:
                    if ':' in match:
                        # Convert HH:MM:SS or MM:SS to seconds
                        parts = match.split(':')
                        if len(parts) == 3:
                            seconds = int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
                        elif len(parts) == 2:
                            seconds = int(parts[0]) * 60 + float(parts[1])
                        else:
                            continue
                    else:
                        seconds = float(match)
                    times.append(seconds)
                except ValueError:
                    continue
        
        if times:
            times = sorted(set(times))
            total_duration = times[-1] if times else 300  # Default 5 minutes
        else:
            total_duration = 300  # Default 5 minutes
            
        # Create 5 equal segments
        segments = []
        segment_duration = total_duration / 5
        
        for i in range(5):
            start_time = i * segment_duration
            end_time = (i + 1) * segment_duration
            segments.append({
                "start": round(start_time, 1),
                "end": round(end_time, 1),
                "summary": f"Phân đoạn video {i + 1}",
                "tags": ["phân_đoạn", f"phần_{i + 1}"]
            })
            
        print(f"[DEBUG] Created {len(segments)} default segments")
        return segments

    def check_connection(self) -> bool:
        """Check if Ollama is running and the model is available"""
        try:
            # Check if Ollama is running
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            response.raise_for_status()
            
            # Check if our model is available
            models = response.json().get("models", [])
            available_models = [model["name"] for model in models]
            
            if self.model not in available_models:
                raise ValueError(f"Model '{self.model}' not found. Available models: {available_models}")
            
            return True
            
        except requests.exceptions.RequestException as e:
            raise ValueError(f"Cannot connect to Ollama at {self.base_url}: {str(e)}")

    def segment_narrative(self, align_result, prompt: str) -> List[Dict]:
        """
        Enhanced narrative segmentation with relevancy ranking and detailed analysis
        Returns precise timestamps for segments matching the narrative with engagement scores
        """
        print(f"[DEBUG] Starting enhanced narrative segmentation with prompt: {prompt}")
        
        # Extract segments from align_result
        segments = align_result.get('segments', [])
        if not segments:
            print("[DEBUG] No segments found in align_result")
            return []
        
        print(f"[DEBUG] Processing {len(segments)} segments for narrative extraction")
        
        # Combine all text with sentence-level timestamps and word counts
        full_text_with_timestamps = []
        sentence_segments = []
        
        for segment in segments:
            text = segment.get('text', '').strip()
            start_time = float(segment.get('start', 0))
            end_time = float(segment.get('end', 0))
            
            if not text:
                continue
                
            # Split into sentences while preserving timestamps
            sentences = self._split_into_sentences(text)
            segment_duration = end_time - start_time
            segment_word_count = len(text.split())
            
            for i, sentence in enumerate(sentences):
                if not sentence.strip():
                    continue
                    
                # Estimate sentence timing within the segment
                sentence_start = start_time + (i / len(sentences)) * segment_duration
                sentence_end = start_time + ((i + 1) / len(sentences)) * segment_duration
                sentence_word_count = len(sentence.split())
                
                sentence_info = {
                    'text': sentence.strip(),
                    'start': sentence_start,
                    'end': sentence_end,
                    'segment_start': start_time,
                    'segment_end': end_time,
                    'word_count': sentence_word_count
                }
                
                sentence_segments.append(sentence_info)
                full_text_with_timestamps.append(f"[{sentence_start:.1f}-{sentence_end:.1f}] {sentence.strip()} ({sentence_word_count} từ)")
        
        print(f"[DEBUG] Created {len(sentence_segments)} sentence segments with word counts")
        
        # Create full text for analysis
        full_text = '\n'.join(full_text_with_timestamps)
        
        # Use enhanced LLM to identify relevant segments with ranking
        relevant_segments = self._find_relevant_segments_with_enhanced_llm(full_text, prompt, sentence_segments)
        
        if not relevant_segments:
            print("[DEBUG] No relevant segments found, trying broader search with ranking")
            # Try broader search with enhanced fallback
            relevant_segments = self._find_relevant_segments_enhanced_fallback(sentence_segments, prompt)
        else:
            print(f"[DEBUG] Found {len(relevant_segments)} relevant segments with enhanced LLM")
        
        # Sort by relevance score (highest first)
        if relevant_segments:
            relevant_segments.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)
        
        print(f"[DEBUG] Found {len(relevant_segments)} relevant segments with ranking")
        return relevant_segments
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences"""
        import re
        # Split on sentence endings, including Vietnamese punctuation
        sentence_endings = r'[.!?。！？]\s+'
        sentences = re.split(sentence_endings, text)
        return [s.strip() for s in sentences if s.strip()]
    
    def _find_relevant_segments_with_enhanced_llm(self, full_text: str, prompt: str, sentence_segments: List[Dict]) -> List[Dict]:
        """Enhanced LLM analysis with detailed summaries, word counts, and relevancy ranking"""
        
        # Enhanced schema for detailed analysis
        enhanced_schema = {
            "type": "object",
            "properties": {
                "relevant_segments": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "start_time": {"type": "number", "description": "Thời gian bắt đầu (giây)"},
                            "end_time": {"type": "number", "description": "Thời gian kết thúc (giây)"},
                            "relevance_score": {"type": "number", "minimum": 1, "maximum": 10},
                            "engagement_score": {"type": "number", "minimum": 1, "maximum": 10},
                            "summary": {"type": "string", "description": "Tóm tắt chi tiết bằng tiếng Việt (20-40 từ)"},
                            "detailed_summary": {"type": "string", "description": "Mô tả chi tiết nội dung (40-80 từ)"},
                            "hook_text": {"type": "string", "description": "Câu mở đầu hấp dẫn (10-15 từ)"},
                            "tags": {"type": "array", "items": {"type": "string"}},
                            "word_count": {"type": "number", "description": "Số từ trong phân đoạn"},
                            "viral_potential": {"type": "string", "enum": ["low", "medium", "high"]},
                            "content_type": {"type": "string", "description": "Loại nội dung: giáo dục, giải trí, thông tin, etc."}
                        },
                        "required": ["start_time", "end_time", "relevance_score", "engagement_score", "summary", "tags", "word_count"]
                    }
                }
            },
            "required": ["relevant_segments"]
        }
        
        # Enhanced system prompt focusing on engagement
        system_prompt = (
            "Bạn là chuyên gia phân tích video với kinh nghiệm tạo nội dung viral. "
            "Nhiệm vụ của bạn là tìm và phân tích TẤT CẢ các phân đoạn có liên quan đến chủ đề, "
            "đồng thời đánh giá tiềm năng thu hút khán giả của từng phân đoạn.\n"
            "TIÊU CHÍ PHÂN TÍCH:\n"
            "1. Relevance Score (1-10): Mức độ liên quan trực tiếp đến chủ đề\n"
            "2. Engagement Score (1-10): Tiềm năng thu hút và giữ chân khán giả\n"
            "3. Viral Potential: Khả năng lan truyền (low/medium/high)\n"
            "4. Content Type: Phân loại nội dung (giáo dục, giải trí, thông tin, etc.)\n"
            "5. Hook Text: Câu mở đầu thu hút trong 10-15 từ\n"
            "6. Word Count: Số từ thực tế trong phân đoạn\n"
            "7. Detailed Summary: Mô tả chi tiết 40-80 từ về nội dung và giá trị\n"
            "\nTẬP TRUNG VÀO: Moments có thể viral, thông tin hữu ích, câu chuyện hấp dẫn, dữ liệu thú vị"
        )
        
        # Enhanced user prompt with specific instructions
        user_prompt = (
            f"CHỦ ĐỀ TÌM KIẾM: {prompt}\n\n"
            "Hãy phân tích video và tìm TẤT CẢ các phân đoạn liên quan, bao gồm:\n"
            "- Đề cập trực tiếp đến chủ đề (relevance ≥ 8)\n"
            "- Thảo luận gián tiếp hoặc liên quan (relevance ≥ 6)\n"
            "- Bối cảnh hoặc dẫn dắt đến chủ đề (relevance ≥ 5)\n\n"
            "QUAN TRỌNG: Đối với mỗi phân đoạn, BẮT BUỘC phải cung cấp:\n"
            "1. Xác định thời gian chính xác (tối thiểu 15 giây)\n"
            "2. Đánh giá relevance_score chính xác từ 1-10 (KHÔNG được bỏ trống hoặc null)\n"
            "3. Đánh giá engagement_score từ 1-10 (khả năng thu hút)\n"
            "4. Viết summary ngắn và detailed_summary dài\n"
            "5. Tạo hook_text hấp dẫn\n"
            "6. Đếm chính xác word_count\n\n"
            "LƯU Ý: relevance_score phải được tính toán cẩn thận:\n"
            "- 9-10: Đề cập trực tiếp, chi tiết về chủ đề\n"
            "- 7-8: Thảo luận rõ ràng về chủ đề\n"
            "- 5-6: Liên quan gián tiếp hoặc đề cập ngắn\n"
            "- 1-4: Chỉ liên quan xa hoặc không nên chọn\n\n"
            "6. Thêm tags SEO-friendly\n"
            "7. Đếm word_count chính xác\n"
            "8. Đánh giá viral_potential\n"
            "9. Phân loại content_type\n\n"
            f"Nội dung video:\n{full_text}"
        )
        
        try:
            result = self._call_ollama([
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ], format_schema=enhanced_schema)
            
            print(f"[DEBUG] Enhanced LLM response type: {type(result)}")
            print(f"[DEBUG] Enhanced LLM response (first 500 chars): {str(result)[:500]}...")
            
            # Parse the enhanced result
            try:
                parsed_result = json.loads(result)
                print(f"[DEBUG] Parsed result keys: {parsed_result.keys() if isinstance(parsed_result, dict) else 'Not a dict'}")
                segments_data = parsed_result.get('relevant_segments', [])
                print(f"[DEBUG] Found {len(segments_data)} segments in LLM response")
                
                if not segments_data:
                    print("[DEBUG] No segments found in enhanced LLM response")
                    return []
                
                # Log the first segment for debugging
                if segments_data:
                    first_seg = segments_data[0]
                    print(f"[DEBUG] First segment keys: {list(first_seg.keys())}")
                    print(f"[DEBUG] First segment relevance_score: {first_seg.get('relevance_score', 'MISSING')}")
                    print(f"[DEBUG] First segment: {first_seg}")
                
                # Convert to enhanced segments format
                enhanced_segments = []
                for seg_data in segments_data:
                    # Get relevance score without defaulting to 5
                    relevance_score = seg_data.get('relevance_score')
                    engagement_score = seg_data.get('engagement_score', 5)
                    
                    # Check if relevance_score is actually provided by LLM
                    if relevance_score is None:
                        print(f"[WARNING] LLM did not provide relevance_score for segment: {seg_data}")
                        print(f"[DEBUG] Available keys in segment: {list(seg_data.keys())}")
                        # Skip segments without relevance score to avoid defaulting
                        continue
                    
                    # Validate relevance score
                    try:
                        relevance_score = float(relevance_score)
                        if not (1 <= relevance_score <= 10):
                            print(f"[WARNING] Invalid relevance_score {relevance_score}, should be 1-10")
                            continue
                    except (ValueError, TypeError):
                        print(f"[ERROR] Cannot convert relevance_score to float: {relevance_score}")
                        continue
                    
                    print(f"[DEBUG] Segment relevance_score: {relevance_score}")
                    
                    # Only include segments with good relevance (≥ 5)
                    if relevance_score >= 5:
                        enhanced_segment = {
                            'start': float(seg_data['start_time']),
                            'end': float(seg_data['end_time']),
                            'summary': seg_data.get('summary', 'Phân đoạn liên quan'),
                            'detailed_summary': seg_data.get('detailed_summary', seg_data.get('summary', '')),
                            'tags': seg_data.get('tags', []),
                            'word_count': int(seg_data.get('word_count', 0)),
                            'relevance_score': relevance_score,
                            'engagement_score': engagement_score,
                            'viral_potential': seg_data.get('viral_potential', 'medium'),
                            'content_type': seg_data.get('content_type', 'thông tin'),
                            'hook_text': seg_data.get('hook_text', 'Bạn có biết...'),
                            'composite_score': (relevance_score * 0.6 + engagement_score * 0.4)  # Weighted score
                        }
                        enhanced_segments.append(enhanced_segment)
                    else:
                        print(f"[DEBUG] Skipping segment with low relevance_score: {relevance_score}")
                
                print(f"[DEBUG] Created {len(enhanced_segments)} enhanced segments with valid relevance scores")
                
                # Merge overlapping segments and extend short ones
                merged_segments = self._merge_and_extend_enhanced_segments(enhanced_segments, sentence_segments)
                return merged_segments
                
            except json.JSONDecodeError as e:
                print(f"[DEBUG] Enhanced JSON parsing failed: {e}")
                return []
                
        except Exception as e:
            print(f"[DEBUG] Enhanced LLM call failed: {e}")
            return []

    def _find_relevant_segments_enhanced_fallback(self, sentence_segments: List[Dict], prompt: str) -> List[Dict]:
        """Enhanced fallback method with better keyword matching and scoring"""
        print("[DEBUG] Using enhanced fallback with relevancy ranking")
        
        # Advanced keyword processing
        prompt_words = set(prompt.lower().split())
        # Add common Vietnamese word variations
        expanded_keywords = set(prompt_words)
        
        # Simple stemming for Vietnamese words
        for word in prompt_words:
            if word.endswith('tion'):
                expanded_keywords.add(word[:-4])
            if word.endswith('ing'):
                expanded_keywords.add(word[:-3])
        
        relevant_segments = []
        current_segment = None
        
        for sentence_info in sentence_segments:
            text_lower = sentence_info['text'].lower()
            
            # Enhanced relevance calculation
            word_matches = sum(1 for keyword in expanded_keywords if keyword in text_lower)
            phrase_match = 1 if prompt.lower() in text_lower else 0
            
            # Calculate relevance score (1-10)
            base_relevance = word_matches + (phrase_match * 3)
            text_length = len(sentence_info['text'].split())
            
            # Normalize by text length (longer text = more context)
            relevance_score = min(10, base_relevance + (text_length / 20))
            
            if relevance_score >= 3:  # Lower threshold for fallback
                if current_segment is None:
                    # Start new segment
                    current_segment = {
                        'start': sentence_info['start'],
                        'end': sentence_info['end'],
                        'text': sentence_info['text'],
                        'word_count': sentence_info.get('word_count', len(sentence_info['text'].split())),
                        'relevance_score': relevance_score,
                        'total_matches': word_matches + phrase_match
                    }
                else:
                    # Extend current segment
                    current_segment['end'] = sentence_info['end']
                    current_segment['text'] += ' ' + sentence_info['text']
                    current_segment['word_count'] += sentence_info.get('word_count', len(sentence_info['text'].split()))
                    current_segment['relevance_score'] = max(current_segment['relevance_score'], relevance_score)
                    current_segment['total_matches'] += word_matches + phrase_match
            else:
                # End current segment if it exists and meets criteria
                if current_segment and (current_segment['end'] - current_segment['start']) >= 15:
                    # Calculate engagement score based on content analysis
                    engagement_score = self._estimate_engagement_score(current_segment['text'], current_segment['word_count'])
                    
                    enhanced_segment = {
                        'start': current_segment['start'],
                        'end': current_segment['end'],
                        'summary': f"Nội dung về {prompt}: {current_segment['text'][:60]}... ({current_segment['word_count']} từ)",
                        'detailed_summary': f"Phân đoạn thảo luận về {prompt} với {current_segment['total_matches']} điểm liên quan. Nội dung: {current_segment['text'][:100]}...",
                        'tags': [prompt.split()[0] if prompt.split() else "chủ_đề", "liên_quan", "tìm_kiếm"],
                        'word_count': current_segment['word_count'],
                        'relevance_score': min(10, current_segment['relevance_score']),
                        'engagement_score': engagement_score,
                        'viral_potential': 'medium' if engagement_score >= 6 else 'low',
                        'content_type': 'thông tin',
                        'hook_text': f"Khám phá {prompt}...",
                        'composite_score': (current_segment['relevance_score'] * 0.6 + engagement_score * 0.4)
                    }
                    relevant_segments.append(enhanced_segment)
                current_segment = None
        
        # Add last segment if exists
        if current_segment and (current_segment['end'] - current_segment['start']) >= 15:
            engagement_score = self._estimate_engagement_score(current_segment['text'], current_segment['word_count'])
            
            enhanced_segment = {
                'start': current_segment['start'],
                'end': current_segment['end'],
                'summary': f"Nội dung về {prompt}: {current_segment['text'][:60]}... ({current_segment['word_count']} từ)",
                'detailed_summary': f"Phân đoạn thảo luận về {prompt} với {current_segment['total_matches']} điểm liên quan. Nội dung: {current_segment['text'][:100]}...",
                'tags': [prompt.split()[0] if prompt.split() else "chủ_đề", "liên_quan", "tìm_kiếm"],
                'word_count': current_segment['word_count'],
                'relevance_score': min(10, current_segment['relevance_score']),
                'engagement_score': engagement_score,
                'viral_potential': 'medium' if engagement_score >= 6 else 'low',
                'content_type': 'thông tin',
                'hook_text': f"Khám phá {prompt}...",
                'composite_score': (current_segment['relevance_score'] * 0.6 + engagement_score * 0.4)
            }
            relevant_segments.append(enhanced_segment)
        
        return relevant_segments

    def _estimate_engagement_score(self, text: str, word_count: int) -> float:
        """Estimate engagement score based on text content analysis"""
        
        # Engagement indicators
        question_words = ['gì', 'sao', 'như thế nào', 'tại sao', 'ở đâu', 'khi nào', 'ai']
        excitement_words = ['tuyệt vời', 'thú vị', 'đáng kinh ngạc', 'bất ngờ', 'khám phá', 'mới lạ']
        action_words = ['xem', 'nghe', 'làm', 'tạo', 'thực hiện', 'khám phá', 'tìm hiểu']
        
        text_lower = text.lower()
        
        # Base score from word count (optimal around 50-100 words)
        if 50 <= word_count <= 100:
            word_score = 7
        elif 30 <= word_count <= 150:
            word_score = 6
        elif word_count >= 20:
            word_score = 5
        else:
            word_score = 3
        
        # Bonus for engagement indicators
        question_bonus = sum(0.5 for word in question_words if word in text_lower)
        excitement_bonus = sum(0.3 for word in excitement_words if word in text_lower)
        action_bonus = sum(0.2 for word in action_words if word in text_lower)
        
        # Penalty for very long or very short content
        length_penalty = 0
        if word_count > 200:
            length_penalty = 1
        elif word_count < 15:
            length_penalty = 2
        
        final_score = word_score + question_bonus + excitement_bonus + action_bonus - length_penalty
        return max(1, min(10, final_score))

    def _merge_and_extend_enhanced_segments(self, segments: List[Dict], sentence_segments: List[Dict]) -> List[Dict]:
        """Enhanced merging with composite score preservation"""
        if not segments:
            return []
        
        # Sort by composite score first, then by start time
        segments.sort(key=lambda x: (-x.get('composite_score', 0), x['start']))
        
        merged = []
        current = segments[0].copy()
        
        for segment in segments[1:]:
            # If segments overlap or are very close (within 3 seconds)
            if segment['start'] <= current['end'] + 3:
                # Merge them, keeping the higher scores
                current['end'] = max(current['end'], segment['end'])
                current['summary'] = f"{current['summary']}; {segment['summary']}"
                current['detailed_summary'] = f"{current['detailed_summary']} {segment['detailed_summary']}"
                current['tags'] = list(set(current['tags'] + segment['tags']))
                current['word_count'] += segment['word_count']
                current['relevance_score'] = max(current['relevance_score'], segment['relevance_score'])
                current['engagement_score'] = max(current['engagement_score'], segment['engagement_score'])
                current['composite_score'] = max(current['composite_score'], segment['composite_score'])
                
                # Update viral potential to highest
                viral_hierarchy = {'low': 1, 'medium': 2, 'high': 3}
                current_viral = viral_hierarchy.get(current.get('viral_potential', 'medium'), 2)
                segment_viral = viral_hierarchy.get(segment.get('viral_potential', 'medium'), 2)
                if segment_viral > current_viral:
                    current['viral_potential'] = segment['viral_potential']
            else:
                # Add current segment and start a new one
                merged.append(current)
                current = segment.copy()
        
        # Add the last segment
        merged.append(current)
        
        # Extend segments that are too short (less than 20 seconds)
        for segment in merged:
            duration = segment['end'] - segment['start']
            if duration < 20:
                # Try to extend by finding more context
                extend_start = max(0, segment['start'] - 5)
                extend_end = segment['end'] + 10
                
                # Make sure we don't go beyond available content
                if sentence_segments:
                    max_time = max(s['end'] for s in sentence_segments)
                    extend_end = min(extend_end, max_time)
                
                segment['start'] = extend_start
                segment['end'] = extend_end
                
                # Update word count estimate
                duration_increase = (extend_end - extend_start) / duration
                segment['word_count'] = int(segment['word_count'] * duration_increase)
        
        # Sort final results by composite score
        merged.sort(key=lambda x: x.get('composite_score', 0), reverse=True)
        
        return merged
            
        # Last resort: create a default segment
        return self._create_default_narrative_segment(subtitle_text, prompt)
        
    def _validate_narrative_segments(self, segments: List[Dict]) -> List[Dict]:
        """Validate and clean narrative segments"""
        if not isinstance(segments, list):
            return []
            
        valid_segments = []
        for i, segment in enumerate(segments):
            try:
                # Check if it's a dictionary
                if not isinstance(segment, dict):
                    print(f"[DEBUG] Segment {i} is not a dictionary")
                    continue
                    
                # Check required keys
                if 'start' not in segment or 'end' not in segment:
                    print(f"[DEBUG] Segment {i} missing start/end times")
                    continue
                    
                # Type conversion and validation
                segment['start'] = float(segment['start'])
                segment['end'] = float(segment['end'])
                
                # Ensure minimum segment length (15 seconds)
                if segment['end'] - segment['start'] < 15:
                    segment['end'] = segment['start'] + 15
                    
                # Validate other fields
                if not isinstance(segment.get('summary', ''), str):
                    segment['summary'] = "Phân đoạn được tìm thấy"
                if not isinstance(segment.get('context', ''), str):
                    segment['context'] = "Bối cảnh của phân đoạn"
                if not isinstance(segment.get('relevance', 0), (int, float)):
                    segment['relevance'] = 5
                if not isinstance(segment.get('tags', []), list):
                    segment['tags'] = ["phân_đoạn"]
                    
                # Only include segments with relevance >= 6
                if segment.get('relevance', 0) >= 6:
                    valid_segments.append(segment)
            except Exception as e:
                print(f"[DEBUG] Error processing narrative segment {i}: {e}")
                
        return valid_segments

    def _create_default_narrative_segment(self, subtitle_text: str, prompt: str) -> List[Dict]:
        """Create a default segment for the narrative prompt when structured output fails"""
        print(f"[DEBUG] Creating default narrative segment for prompt: {prompt}")
        
        # Try to find content matching the prompt in the subtitle text
        prompt_words = set(prompt.lower().split())
        best_match_score = 0
        best_match_index = 0
        best_match_line = ""
        
        # Parse timestamps if they exist in the subtitle text
        time_pattern = r'\[(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)\]'
        timestamps = []
        lines = subtitle_text.split('\n')
        
        # First pass: extract all timestamps and text
        timestamped_lines = []
        for i, line in enumerate(lines):
            # Try to extract timestamp from the line
            match = re.search(time_pattern, line)
            if match:
                try:
                    start_time = float(match.group(1))
                    end_time = float(match.group(2))
                    # Extract text after timestamp
                    text = line[match.end():].strip()
                    timestamped_lines.append({
                        'index': i,
                        'start': start_time,
                        'end': end_time,
                        'text': text
                    })
                except ValueError:
                    continue
        
        # Second pass: find best matching content
        for i, line_data in enumerate(timestamped_lines):
            line = line_data['text'].lower()
            # Calculate word overlap
            line_words = set(line.split())
            intersection = prompt_words.intersection(line_words)
            score = len(intersection) / len(prompt_words) if prompt_words else 0
            
            # Check for exact phrase match (higher priority)
            if prompt.lower() in line.lower():
                score += 0.5  # Boost score for phrase match
                
            if score > best_match_score:
                best_match_score = score
                best_match_index = i
                best_match_line = line_data['text']
        
        # If we found a good match (score > 0.3), use its timestamp
        if best_match_score > 0.3 and timestamped_lines:
            match_data = timestamped_lines[best_match_index]
            start_time = match_data['start']
            end_time = match_data['end']
            
            # Extend context by including surrounding lines
            context_start = max(0, best_match_index - 2)
            context_end = min(len(timestamped_lines) - 1, best_match_index + 2)
            
            # Adjust start/end times to include context
            if context_start < best_match_index:
                start_time = timestamped_lines[context_start]['start']
            if context_end > best_match_index:
                end_time = timestamped_lines[context_end]['end']
                
            # Ensure minimum segment length (30 seconds)
            if end_time - start_time < 30:
                end_time = start_time + 30
                
            # Create a segment with the matched content
            segment = {
                "start": start_time,
                "end": end_time,
                "summary": f"Phân đoạn video về chủ đề: {prompt}",
                "tags": ["kết_quả_tìm_kiếm", "phân_đoạn_phù_hợp"],
            }
        else:
            # No good match found, create a generic segment
            # Try to find any timestamps in the subtitles
            times = []
            for line_data in timestamped_lines:
                times.append(line_data['start'])
                times.append(line_data['end'])
            
            if times:
                # Use the middle of the content as a fallback
                times.sort()
                mid_point = times[len(times) // 2]
                start_time = max(0, mid_point - 15)
                end_time = min(times[-1], mid_point + 15)
            else:
                # No timestamps found, create a segment in the middle of the estimated duration
                start_time = 60
                end_time = 180
            
            # Create a generic segment
            segment = {
                "start": start_time,
                "end": end_time,
                "summary": f"Phân đoạn video có thể liên quan đến chủ đề: {prompt}",
                "tags": ["độ_tin_cậy_thấp", "kết_quả_mặc_định"],
            }
        
        print(f"[DEBUG] Created default narrative segment: {segment}")
        return [segment]
        
    def _convert_narrative_to_standard_segments(self, narrative_segments: List[Dict]) -> List[Dict]:
        """Convert narrative segments format to standard segment format"""
        standard_segments = []
        
        for segment in narrative_segments:
            # Create standard segment with additional context info
            standard_segment = {
                "start": segment["start"],
                "end": segment["end"],
                "summary": segment["summary"],
                "tags": segment["tags"].copy() if isinstance(segment["tags"], list) else [str(segment["tags"])]
            }
            
            # Transfer relevance_score properly
            if "relevance_score" in segment:
                standard_segment["relevance_score"] = segment["relevance_score"]
            elif "relevance" in segment:
                standard_segment["relevance_score"] = segment["relevance"]
            else:
                # If no relevance score, we should not default to 5 - let it be missing so we can debug
                print(f"[WARNING] No relevance score found in segment: {segment}")
            
            # Transfer other scoring fields if available
            if "engagement_score" in segment:
                standard_segment["engagement_score"] = segment["engagement_score"]
            if "composite_score" in segment:
                standard_segment["composite_score"] = segment["composite_score"]
            
            # Add context information to the summary if available
            if "context" in segment and segment["context"] and segment["context"] != segment["summary"]:
                # Include context in the summary for better understanding
                standard_segment["summary"] = f"{segment['summary']} - {segment['context']}"
                
            # Add relevance score to tags if available for visual identification
            if "relevance_score" in standard_segment:
                relevance = int(standard_segment["relevance_score"])
                if relevance >= 8:
                    standard_segment["tags"].append("độ_liên_quan_cao")
                elif relevance >= 6:
                    standard_segment["tags"].append("độ_liên_quan_trung_bình")
                else:
                    standard_segment["tags"].append("độ_liên_quan_thấp")
                    
            # Add query-related tag for easier identification
            standard_segment["tags"].append("kết_quả_truy_vấn")
                    
            standard_segments.append(standard_segment)
            
        return standard_segments

    def segment_video_with_timestamps(self, subtitle_segments, prompt: Optional[str] = None) -> List[Dict]:
        """Segment video using actual subtitle timestamps to ensure accuracy"""
        
        if not subtitle_segments:
            return []
            
        print(f"[DEBUG] Processing {len(subtitle_segments)} subtitle segments")
        
        # Group consecutive segments into logical chunks (30-60 seconds each)
        logical_segments = self._create_logical_segments(subtitle_segments)
        print(f"[DEBUG] Created {len(logical_segments)} logical segments")
        
        # Create placeholder segments with real timestamps for now
        # This ensures timestamps are always accurate
        result_segments = []
        for i, segment in enumerate(logical_segments):
            # Use actual start/end times from subtitle segments
            start_time = segment['start']
            end_time = segment['end']
            
            # Create a descriptive summary based on the content
            text_content = segment['text']
            word_count = len(text_content.split())
            
            # Generate basic summary for now (can be enhanced later)
            if prompt and prompt.strip():
                summary = f"Phân đoạn {i+1}: Nội dung liên quan đến '{prompt}' ({word_count} từ)"
                tags = [prompt.split()[0] if prompt.split() else "nội_dung", "phân_đoạn"]
            else:
                summary = f"Phân đoạn {i+1}: Nội dung video ({word_count} từ)"
                tags = ["video", "nội_dung"]
            
            result_segments.append({
                "start": start_time,
                "end": end_time,
                "summary": summary,
                "tags": tags
            })
        
        print(f"[DEBUG] Generated {len(result_segments)} result segments with accurate timestamps")
        return result_segments
    
    def _create_logical_segments(self, subtitle_segments, target_duration=45) -> List[Dict]:
        """Group subtitle segments into logical chunks with target duration"""
        if not subtitle_segments:
            return []
            
        logical_segments = []
        current_segment = {
            'start': None,
            'end': None,
            'text': ''
        }
        
        for segment in subtitle_segments:
            start_time = float(segment.get('start', 0))
            end_time = float(segment.get('end', 0))
            text = segment.get('text', '').strip()
            
            if not text:
                continue
            
            # Initialize the first segment
            if current_segment['start'] is None:
                current_segment['start'] = start_time
                current_segment['end'] = end_time
                current_segment['text'] = text
                continue
            
            # Check if we should start a new segment
            current_duration = current_segment['end'] - current_segment['start']
            
            # Start new segment if:
            # 1. Current segment is long enough (target_duration seconds)
            # 2. There's a significant pause (>3 seconds) between segments
            # 3. Text contains sentence endings and we have enough content
            gap = start_time - current_segment['end']
            has_sentence_end = any(punct in current_segment['text'][-10:] for punct in ['.', '!', '?', '。', '！', '？'])
            
            if (current_duration >= target_duration or 
                (gap > 3.0 and current_duration >= 15) or
                (has_sentence_end and current_duration >= 20 and gap > 1.0)):
                
                # Finish current segment
                logical_segments.append(current_segment.copy())
                
                # Start new segment
                current_segment = {
                    'start': start_time,
                    'end': end_time,
                    'text': text
                }
            else:
                # Continue current segment
                current_segment['end'] = end_time
                current_segment['text'] += ' ' + text
        
        # Add the last segment
        if current_segment['start'] is not None:
            logical_segments.append(current_segment)
        
        return logical_segments
    
    def _parse_and_validate_enhanced_response(self, result: str) -> Optional[List[Dict]]:
        """Enhanced parsing for responses that include word counts and detailed summaries"""
        try:
            # Clean up the response
            result = result.strip()
            
            # Remove <think> tags and their content
            think_pattern = r'<think>.*?</think>'
            result = re.sub(think_pattern, '', result, flags=re.DOTALL)
            result = result.strip()
            
            # Remove possible markdown code blocks
            if result.startswith("```json"):
                result = result[7:]
                if result.endswith("```"):
                    result = result[:-3]
            elif result.startswith("```"):
                result = result[3:]
                if result.endswith("```"):
                    result = result[:-3]
            
            result = result.strip()
            
            # Try to parse as JSON directly first
            try:
                parsed_data = json.loads(result)
                
                # If it's an array, use it directly
                if isinstance(parsed_data, list):
                    print(f"[DEBUG] Successfully parsed enhanced JSON array directly")
                    segments = parsed_data
                # If it's a dictionary, look for array fields
                elif isinstance(parsed_data, dict):
                    print(f"[DEBUG] Response is a dictionary, looking for array fields")
                    array_fields = ['segments', 'results', 'items', 'data']
                    for field in array_fields:
                        if field in parsed_data and isinstance(parsed_data[field], list):
                            print(f"[DEBUG] Found array in field '{field}'")
                            segments = parsed_data[field]
                            break
                    else:
                        segments = [parsed_data]
                else:
                    print(f"[DEBUG] Response is not a list or dict: {type(parsed_data)}")
                    return None
            except json.JSONDecodeError:
                # If direct parsing fails, try to extract JSON array from text
                print(f"[DEBUG] Direct parsing failed, trying to extract JSON array")
                start_idx = result.find('[')
                end_idx = result.rfind(']')
                
                if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                    json_str = result[start_idx:end_idx + 1]
                    print(f"[DEBUG] Extracted JSON: {json_str[:200]}...")
                    segments = json.loads(json_str)
                else:
                    print(f"[DEBUG] Could not find JSON array in response")
                    return None
            
            # Enhanced validation
            if not isinstance(segments, list):
                print(f"[DEBUG] Segments is not a list: {type(segments)}")
                return None
            
            if len(segments) == 0:
                print("[DEBUG] Empty segments list")
                return None
                
            # Validate each segment with enhanced fields
            valid_segments = []
            for i, segment in enumerate(segments):
                if not isinstance(segment, dict):
                    print(f"[DEBUG] Segment {i} is not a dictionary: {type(segment)}")
                    continue
                
                # Check required keys
                if 'start' not in segment or 'end' not in segment:
                    print(f"[DEBUG] Segment {i} missing start/end times")
                    continue
                    
                # Ensure required fields exist with enhanced defaults
                segment.setdefault('summary', f"Phân đoạn video {i+1} với nội dung thú vị")
                segment.setdefault('tags', ['video', 'nội_dung'])
                segment.setdefault('word_count', 0)
                
                # Type conversion and validation
                try:
                    segment['start'] = float(segment['start'])
                    segment['end'] = float(segment['end'])
                    
                    if not isinstance(segment['summary'], str):
                        segment['summary'] = str(segment['summary'])
                    
                    if not isinstance(segment['tags'], list):
                        segment['tags'] = [str(segment['tags'])] if segment['tags'] else ['nội_dung']
                    
                    # Validate word_count
                    if 'word_count' in segment:
                        try:
                            segment['word_count'] = int(segment['word_count'])
                        except (ValueError, TypeError):
                            # Calculate word count from summary if not provided or invalid
                            segment['word_count'] = len(segment['summary'].split())
                    else:
                        segment['word_count'] = len(segment['summary'].split())
                    
                    # Basic time validation
                    if segment['start'] >= segment['end']:
                        print(f"[DEBUG] Invalid time range for segment {i}: {segment['start']} >= {segment['end']}")
                        continue
                        
                    valid_segments.append(segment)
                    
                except (ValueError, TypeError) as e:
                    print(f"[DEBUG] Type conversion error for segment {i}: {e}")
                    continue
            
            print(f"[DEBUG] Enhanced validation: {len(valid_segments)} out of {len(segments)} segments")
            return valid_segments if valid_segments else None
            
        except json.JSONDecodeError as e:
            print(f"[DEBUG] JSON decode error: {e}")
            print(f"[DEBUG] Problematic content: {result[:200]}...")
            return None
        except Exception as e:
            print(f"[DEBUG] Enhanced validation error: {e}")
            return None

    def _create_enhanced_default_segments(self, subtitle_text: str) -> List[Dict]:
        """Create enhanced default segments with word counts and detailed summaries"""
        print("[DEBUG] Creating enhanced default segments")
        
        # Try to extract time information from subtitles
        time_pattern = r'(\d{1,2}:\d{2}:\d{2}(?:\.\d{3})?|\d+(?:\.\d+)?)'
        times = []
        
        for line in subtitle_text.split('\n'):
            matches = re.findall(time_pattern, line)
            for match in matches:
                try:
                    if ':' in match:
                        # Convert HH:MM:SS or MM:SS to seconds
                        parts = match.split(':')
                        if len(parts) == 3:
                            seconds = int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
                        elif len(parts) == 2:
                            seconds = int(parts[0]) * 60 + float(parts[1])
                        else:
                            continue
                    else:
                        seconds = float(match)
                    times.append(seconds)
                except ValueError:
                    continue
        
        if times:
            times = sorted(set(times))
            total_duration = times[-1] if times else 300
        else:
            total_duration = 300
            
        # Create enhanced segments with detailed summaries
        segments = []
        segment_duration = total_duration / 5
        total_words = len(subtitle_text.split())
        words_per_segment = total_words // 5
        
        for i in range(5):
            start_time = i * segment_duration
            end_time = (i + 1) * segment_duration
            
            # Create more engaging summaries for social media
            summary_templates = [
                f"Phần {i+1}: Nội dung thú vị và hấp dẫn với những thông tin quan trọng ({words_per_segment} từ)",
                f"Đoạn {i+1}: Những điểm nổi bật và thông tin giá trị cho khán giả ({words_per_segment} từ)",
                f"Phân đoạn {i+1}: Nội dung chất lượng cao với thông điệp rõ ràng ({words_per_segment} từ)",
                f"Khoảnh khắc {i+1}: Thông tin hữu ích và thu hút sự chú ý ({words_per_segment} từ)",
                f"Clip {i+1}: Nội dung viral-worthy với giá trị giải trí cao ({words_per_segment} từ)"
            ]
            
            segments.append({
                "start": round(start_time, 1),
                "end": round(end_time, 1),
                "summary": summary_templates[i],
                "tags": ["video_viral", "nội_dung_hot", f"phần_{i + 1}", "thu_hút"],
                "word_count": words_per_segment
            })
            
        print(f"[DEBUG] Created {len(segments)} enhanced default segments")
        return segments

    def generate_chapters(self, transcript_text: str) -> List[Dict]:
        """Generate chapters from transcript text using LLM"""
        
        # Define the schema for chapters
        chapters_schema = {
            "type": "object",
            "properties": {
                "chapters": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "start_time": {"type": "number", "description": "Thời gian bắt đầu (giây)"},
                            "end_time": {"type": "number", "description": "Thời gian kết thúc (giây)"},
                            "title": {"type": "string", "description": "Tiêu đề chương (10-50 từ)"},
                            "summary": {"type": "string", "description": "Tóm tắt chi tiết nội dung chương (100-200 từ), bao gồm các thông tin quan trọng và insights chính"},
                            "key_points": {"type": "array", "items": {"type": "string"}, "description": "Các điểm chính của chương"},
                            "duration": {"type": "number", "description": "Thời lượng chương (giây)"}
                        },
                        "required": ["start_time", "end_time", "title", "summary", "key_points", "duration"]
                    }
                }
            },
            "required": ["chapters"]
        }
        
        system_prompt = (
            "Bạn là chuyên gia phân tích nội dung với khả năng chia video thành các chương logic. "
            "Nhiệm vụ của bạn là phân tích transcript và tạo ra các chương có ý nghĩa, "
            "mỗi chương đại diện cho một chủ đề hoặc phần nội dung riêng biệt.\n"
            "TIÊU CHÍ CHIA CHƯƠNG:\n"
            "1. Mỗi chương nên dài ít nhất 30 giây và không quá 10 phút\n"
            "2. Chia theo chủ đề, không gian thời gian, hoặc người nói\n"
            "3. Đảm bảo các chương không chồng lấn về thời gian\n"
            "4. Tiêu đề chương ngắn gọn, súc tích (10-50 từ)\n"
            "5. Tóm tắt chương chi tiết và thông tin (100-200 từ)\n"
            "6. Tạo 3-5 điểm chính cho mỗi chương\n"
            "7. Tính toán chính xác duration = end_time - start_time"
        )
        
        user_prompt = (
            "Hãy phân tích transcript sau đây và chia thành các chương logic:\n\n"
            f"{transcript_text}\n\n"
            "Tạo các chương với:\n"
            "- Thời gian bắt đầu và kết thúc chính xác\n"
            "- Tiêu đề mô tả nội dung chính của chương\n"
            "- Tóm tắt chi tiết và đầy đủ nội dung của từng chương\n"
            "- Các điểm chính trong chương\n"
            "- Thời lượng chính xác của chương"
        )
        
        try:
            result = self._call_ollama([
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ], format_schema=chapters_schema)
            
            print(f"[DEBUG] Chapter generation response: {result[:300]}...")
            
            # Parse the response
            if isinstance(result, str):
                try:
                    parsed_result = json.loads(result)
                except json.JSONDecodeError:
                    # Fallback: try to extract JSON from the response
                    json_match = re.search(r'\{.*\}', result, re.DOTALL)
                    if json_match:
                        parsed_result = json.loads(json_match.group())
                    else:
                        raise ValueError("Could not parse JSON from response")
            else:
                parsed_result = result
            
            chapters = parsed_result.get("chapters", [])
            
            # Validate and fix chapters
            validated_chapters = []
            for chapter in chapters:
                if all(key in chapter for key in ["start_time", "end_time", "title", "summary", "key_points"]):
                    # Calculate duration if not present
                    if "duration" not in chapter:
                        chapter["duration"] = chapter["end_time"] - chapter["start_time"]
                    
                    # Ensure key_points is a list
                    if not isinstance(chapter["key_points"], list):
                        chapter["key_points"] = [str(chapter["key_points"])]
                    
                    validated_chapters.append(chapter)
            
            if not validated_chapters:
                # Fallback: create a single chapter for the entire content
                validated_chapters = [{
                    "start_time": 0,
                    "end_time": 300,  # Default 5 minutes
                    "title": "Nội dung chính",
                    "summary": "Tóm tắt toàn bộ nội dung",
                    "key_points": ["Điểm chính 1", "Điểm chính 2"],
                    "duration": 300
                }]
            
            return validated_chapters
            
        except Exception as e:
            print(f"Error generating chapters: {str(e)}")
            # Return a fallback chapter
            return [{
                "start_time": 0,
                "end_time": 300,
                "title": "Nội dung chính",
                "summary": "Không thể tạo chương tự động. Vui lòng kiểm tra transcript.",
                "key_points": ["Nội dung cần được phân tích thủ công"],
                "duration": 300
            }]

    def generate_individual_chapter_summary(self, chapter_text: str, chapter_title: str) -> Dict:
        """Generate detailed summary for a single chapter"""
        
        summary_schema = {
            "type": "object",
            "properties": {
                "detailed_summary": {"type": "string", "description": "Tóm tắt chi tiết và đầy đủ (150-300 từ)"},
                "key_insights": {"type": "array", "items": {"type": "string"}, "description": "Những insights và điểm quan trọng nhất (3-5 điểm)"},
                "main_topics": {"type": "array", "items": {"type": "string"}, "description": "Các chủ đề chính được đề cập"},
                "action_items": {"type": "array", "items": {"type": "string"}, "description": "Các hành động hoặc takeaways có thể áp dụng (nếu có)"}
            },
            "required": ["detailed_summary", "key_insights", "main_topics"]
        }
        
        system_prompt = (
            "Bạn là chuyên gia phân tích nội dung chuyên sâu. Nhiệm vụ của bạn là tạo ra một "
            "bản tóm tắt chi tiết và toàn diện cho từng chương, bao gồm tất cả thông tin quan trọng, "
            "insights, và takeaways mà người xem có thể học được từ phần này."
        )
        
        user_prompt = (
            f"Hãy phân tích và tóm tắt chi tiết chương sau:\n\n"
            f"TIÊU ĐỀ CHƯƠNG: {chapter_title}\n\n"
            f"NỘI DUNG:\n{chapter_text}\n\n"
            "Tạo một bản tóm tắt bao gồm:\n"
            "1. Tóm tắt chi tiết và đầy đủ nội dung (150-300 từ)\n"
            "2. Những insights và điểm quan trọng nhất\n"
            "3. Các chủ đề chính được đề cập\n"
            "4. Các hành động hoặc takeaways có thể áp dụng (nếu có)"
        )
        
        try:
            result = self._call_ollama([
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ], format_schema=summary_schema)
            
            if isinstance(result, str):
                try:
                    parsed_result = json.loads(result)
                except json.JSONDecodeError:
                    json_match = re.search(r'\{.*\}', result, re.DOTALL)
                    if json_match:
                        parsed_result = json.loads(json_match.group())
                    else:
                        return {
                            "detailed_summary": "Không thể tạo tóm tắt chi tiết",
                            "key_insights": ["Lỗi xử lý"],
                            "main_topics": ["Không xác định"]
                        }
            else:
                parsed_result = result
            
            return parsed_result
            
        except Exception as e:
            print(f"[ERROR] Error generating individual chapter summary: {str(e)}")
            return {
                "detailed_summary": "Không thể tạo tóm tắt chi tiết",
                "key_insights": ["Lỗi xử lý"],
                "main_topics": ["Không xác định"]
            }

    def generate_transcription_summary(self, transcript_text: str) -> Dict:
        """Generate a comprehensive summary of the entire transcription in Vietnamese"""
        
        # Schema for structured transcription summary
        summary_schema = {
            "type": "object",
            "properties": {
                "summary": {
                    "type": "string",
                    "description": "Tóm tắt tổng quan về nội dung chính của video/âm thanh"
                },
                "highlights": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Các điểm nổi bật quan trọng nhất"
                },
                "key_insights": {
                    "type": "array", 
                    "items": {"type": "string"},
                    "description": "Những hiểu biết và bài học chính"
                },
                "conclusion": {
                    "type": "string",
                    "description": "Kết luận tổng thể"
                }
            },
            "required": ["summary", "highlights", "key_insights", "conclusion"]
        }
        
        # Vietnamese prompt for comprehensive transcription summary
        messages = [
            {
                "role": "system",
                "content": """Bạn là một chuyên gia phân tích nội dung video/âm thanh. Nhiệm vụ của bạn là tạo một bản tóm tắt toàn diện, có cấu trúc và dễ hiểu về toàn bộ nội dung transcript.

HƯỚNG DẪN:
- Phân tích toàn bộ transcript để hiểu nội dung chính
- Tạo tóm tắt bằng tiếng Việt, dễ hiểu và mạch lạc
- Tập trung vào những thông tin quan trọng và hữu ích nhất
- Cung cấp cái nhìn tổng thể về chủ đề và nội dung

CẤU TRÚC PHẢN HỒI:
- summary: Tóm tắt tổng quan chi tiết (200-400 từ)
- highlights: 5-8 điểm nổi bật quan trọng nhất
- key_insights: 4-6 hiểu biết/bài học chính
- conclusion: Kết luận ngắn gọn nhưng đầy đủ ý nghĩa

Đảm bảo nội dung phù hợp với văn hóa và ngôn ngữ Việt Nam."""
            },
            {
                "role": "user", 
                "content": f"""Hãy tạo tóm tắt toàn diện cho transcript sau:

{transcript_text}

Vui lòng tạo tóm tắt có cấu trúc theo yêu cầu."""
            }
        ]
        
        try:
            print("Đang tạo tóm tắt transcription...")
            response = self._call_ollama(messages, summary_schema)
            
            # Parse the JSON response
            result = json.loads(response)
            
            # Validate required fields
            required_fields = ["summary", "highlights", "key_insights", "conclusion"]
            for field in required_fields:
                if field not in result:
                    result[field] = []
            
            # Ensure lists are properly formatted
            if not isinstance(result.get("highlights"), list):
                result["highlights"] = []
            if not isinstance(result.get("key_insights"), list):
                result["key_insights"] = []
                
            print(f"Tạo tóm tắt transcription thành công")
            return result
            
        except json.JSONDecodeError as e:
            print(f"[ERROR] JSON parsing error for transcription summary: {str(e)}")
            # Try to parse without schema
            try:
                messages_simple = [
                    {
                        "role": "system",
                        "content": "Bạn là chuyên gia phân tích nội dung. Tạo tóm tắt toàn diện bằng tiếng Việt."
                    },
                    {
                        "role": "user",
                        "content": f"Tóm tắt nội dung chính của transcript sau:\n\n{transcript_text[:3000]}..."
                    }
                ]
                
                simple_response = self._call_ollama(messages_simple)
                
                return {
                    "summary": simple_response,
                    "highlights": ["Nội dung chính từ transcript"],
                    "key_insights": ["Phân tích từ nội dung được cung cấp"],
                    "conclusion": "Tóm tắt được tạo thành công"
                }
                
            except Exception as e2:
                print(f"[ERROR] Fallback transcription summary failed: {str(e2)}")
                return self._get_fallback_transcription_summary()
                
        except Exception as e:
            print(f"[ERROR] Error generating transcription summary: {str(e)}")
            return self._get_fallback_transcription_summary()
    
    def _get_fallback_transcription_summary(self) -> Dict:
        """Fallback summary when LLM processing fails"""
        return {
            "summary": "Không thể tạo tóm tắt tự động. Vui lòng kiểm tra lại nội dung transcript và thử lại.",
            "highlights": [
                "Lỗi xử lý tóm tắt",
                "Cần kiểm tra kết nối mô hình AI",
                "Thử lại sau"
            ],
            "key_insights": [
                "Hệ thống gặp sự cố khi phân tích nội dung",
                "Cần khắc phục vấn đề kỹ thuật"
            ],
            "conclusion": "Tóm tắt sẽ được tạo lại khi hệ thống hoạt động bình thường."
        }
