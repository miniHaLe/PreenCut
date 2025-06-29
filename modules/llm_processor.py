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
            "Đối với mỗi phân đoạn, hãy:\n"
            "1. Xác định thời gian chính xác (tối thiểu 15 giây)\n"
            "2. Đánh giá relevance_score (chỉ lấy ≥ 5)\n"
            "3. Đánh giá engagement_score (khả năng thu hút)\n"
            "4. Viết summary ngắn và detailed_summary dài\n"
            "5. Tạo hook_text hấp dẫn\n"
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
            
            print(f"[DEBUG] Enhanced LLM response: {result[:300]}...")
            
            # Parse the enhanced result
            try:
                parsed_result = json.loads(result)
                segments_data = parsed_result.get('relevant_segments', [])
                
                if not segments_data:
                    print("[DEBUG] No segments found in enhanced LLM response")
                    return []
                
                # Convert to enhanced segments format
                enhanced_segments = []
                for seg_data in segments_data:
                    relevance_score = seg_data.get('relevance_score', 5)
                    engagement_score = seg_data.get('engagement_score', 5)
                    
                    # Only include segments with good relevance
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
            
            # Add context information to the summary if available
            if "context" in segment and segment["context"] and segment["context"] != segment["summary"]:
                # Include context in the summary for better understanding
                standard_segment["summary"] = f"{segment['summary']} - {segment['context']}"
                
            # Add relevance score to tags if available
            if "relevance" in segment:
                relevance = int(segment["relevance"])
                if relevance >= 8:
                    standard_segment["tags"].append("độ_liên_quan_cao")
                elif relevance >= 6:
                    standard_segment["tags"].append("độ_liên_quan_trung_bình")
                    
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

    def segment_video_for_social_media(self, subtitles, platform: str = "general", prompt: Optional[str] = None) -> List[Dict]:
        """
        Enhanced video segmentation optimized for social media platforms
        Takes Instagram Reels, TikTok, YouTube Shorts as reference
        """
        print(f"[DEBUG] Starting social media optimization for platform: {platform}")
        
        # Platform-specific constraints
        platform_configs = {
            "tiktok": {
                "max_duration": 180,  # 3 minutes max
                "optimal_duration": 30,  # 30 seconds sweet spot
                "engagement_focus": "viral_hooks",
                "content_style": "trendy"
            },
            "instagram": {
                "max_duration": 90,  # 90 seconds max for Reels
                "optimal_duration": 25,  # 15-30 seconds optimal
                "engagement_focus": "visual_appeal",
                "content_style": "aesthetic"
            },
            "youtube_shorts": {
                "max_duration": 60,  # 60 seconds max
                "optimal_duration": 45,  # 30-60 seconds optimal
                "engagement_focus": "retention",
                "content_style": "informative"
            },
            "general": {
                "max_duration": 120,
                "optimal_duration": 40,
                "engagement_focus": "balanced",
                "content_style": "engaging"
            }
        }
        
        config = platform_configs.get(platform, platform_configs["general"])
        
        # Handle subtitle input
        if isinstance(subtitles, list):
            subtitle_text = '\n'.join(str(item) for item in subtitles)
        else:
            subtitle_text = str(subtitles)
        
        # Social media optimized system prompt
        system_prompt = (
            f"Bạn là chuyên gia tạo nội dung viral cho {platform.upper()}. "
            "Hãy phân tích video và tạo các clip ngắn có tiềm năng thu hút khán giả cao. "
            "YÊU CẦU:\n"
            "1. Mỗi clip phải có hook mạnh mẽ (câu mở đầu hấp dẫn)\n"
            f"2. Thời lượng tối ưu: {config['optimal_duration']} giây\n"
            f"3. Tối đa {config['max_duration']} giây\n"
            "4. Tập trung vào moments có viral potential\n"
            "5. Tóm tắt phải clickbait nhưng trung thực\n"
            "6. Tags phải trending và SEO-friendly\n"
            "7. Đánh giá engagement_score (1-10) cho mỗi clip\n"
            "8. Thêm viral_potential (low/medium/high)\n"
            "Trả về JSON với các fields: start, end, summary, tags, word_count, engagement_score, viral_potential, hook_text"
        )
        
        # Platform-specific user prompt
        user_prompt = (
            f"Phân tích video và tạo tối đa 8 clips cho {platform}. "
            f"Tìm những khoảnh khắc: {config['engagement_focus']}. "
            f"Style: {config['content_style']}. "
            "Mỗi clip cần:\n"
            "- start/end (giây)\n"
            "- summary: Tiêu đề clickbait (20-40 từ)\n"
            "- tags: 5-7 hashtags trending\n"
            "- word_count: số từ trong clip\n"
            "- engagement_score: điểm thu hút (1-10)\n"
            "- viral_potential: khả năng viral (low/medium/high)\n"
            "- hook_text: câu mở đầu hấp dẫn (10-15 từ)\n"
            f"Prompt người dùng: {prompt or 'Tìm nội dung viral nhất'}"
        )
        
        full_prompt = f"{user_prompt}\n\nNội dung video:\n{subtitle_text}"
        
        print(f"[DEBUG] Optimizing for {platform} with {config['optimal_duration']}s target")
        
        try:
            result = self._call_ollama([
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": full_prompt}
            ], format_json=True)
            
            print(f"[DEBUG] Social media response (first 500 chars): {result[:500]}")
            
            segments = self._parse_and_validate_social_media_response(result, config)
            if segments:
                # Sort by engagement score (highest first)
                segments.sort(key=lambda x: x.get('engagement_score', 0), reverse=True)
                print(f"[DEBUG] Generated {len(segments)} social media optimized segments")
                return segments
                
        except Exception as e:
            print(f"[DEBUG] Social media optimization failed: {str(e)}")
        
        # Fallback to enhanced regular segmentation
        return self.segment_video(subtitles, prompt)

    def _parse_and_validate_social_media_response(self, result: str, config: Dict) -> List[Dict]:
        """Parse and validate social media optimized segments"""
        try:
            # Clean and parse JSON
            result = result.strip()
            result = re.sub(r'<think>.*?</think>', '', result, flags=re.DOTALL)
            
            if result.startswith("```json"):
                result = result[7:-3] if result.endswith("```") else result[7:]
            elif result.startswith("```"):
                result = result[3:-3] if result.endswith("```") else result[3:]
            
            # Find JSON array
            start_idx = result.find('[')
            end_idx = result.rfind(']')
            
            if start_idx != -1 and end_idx != -1:
                json_str = result[start_idx:end_idx + 1]
                segments = json.loads(json_str)
            else:
                segments = json.loads(result)
            
            if not isinstance(segments, list):
                return []
            
            # Validate and enhance segments
            valid_segments = []
            for i, segment in enumerate(segments):
                if not isinstance(segment, dict):
                    continue
                
                # Required fields validation
                if 'start' not in segment or 'end' not in segment:
                    continue
                
                try:
                    segment['start'] = float(segment['start'])
                    segment['end'] = float(segment['end'])
                    duration = segment['end'] - segment['start']
                    
                    # Skip segments that are too long for the platform
                    if duration > config['max_duration']:
                        continue
                    
                    # Set defaults for missing fields
                    segment.setdefault('summary', f"Clip viral #{i+1}")
                    segment.setdefault('tags', ['viral', 'trending', 'hot'])
                    segment.setdefault('word_count', len(segment.get('summary', '').split()))
                    segment.setdefault('engagement_score', 5)
                    segment.setdefault('viral_potential', 'medium')
                    segment.setdefault('hook_text', "Bạn có biết...")
                    
                    # Validate engagement_score
                    if not isinstance(segment.get('engagement_score'), (int, float)):
                        segment['engagement_score'] = 5
                    segment['engagement_score'] = max(1, min(10, segment['engagement_score']))
                    
                    # Validate viral_potential
                    if segment.get('viral_potential') not in ['low', 'medium', 'high']:
                        segment['viral_potential'] = 'medium'
                    
                    valid_segments.append(segment)
                    
                except (ValueError, TypeError) as e:
                    print(f"[DEBUG] Error processing social media segment {i}: {e}")
                    continue
            
            return valid_segments
            
        except (json.JSONDecodeError, Exception) as e:
            print(f"[DEBUG] Social media parsing error: {e}")
            return []

    def get_best_clips_for_platform(self, segments: List[Dict], platform: str, max_clips: int = 5) -> List[Dict]:
        """
        Select the best clips for a specific platform based on engagement and viral potential
        """
        if not segments:
            return []
        
        # Platform-specific scoring weights
        scoring_weights = {
            "tiktok": {
                "engagement_score": 0.4,
                "viral_potential": 0.4,
                "duration_match": 0.2,
                "optimal_duration": 30
            },
            "instagram": {
                "engagement_score": 0.3,
                "viral_potential": 0.3,
                "duration_match": 0.4,
                "optimal_duration": 25
            },
            "youtube_shorts": {
                "engagement_score": 0.5,
                "viral_potential": 0.2,
                "duration_match": 0.3,
                "optimal_duration": 45
            }
        }
        
        weights = scoring_weights.get(platform, scoring_weights["tiktok"])
        
        # Calculate composite scores
        scored_segments = []
        for segment in segments:
            duration = segment.get('end', 0) - segment.get('start', 0)
            
            # Duration score (closer to optimal = higher score)
            duration_diff = abs(duration - weights['optimal_duration'])
            duration_score = max(0, 10 - (duration_diff / 5))
            
            # Viral potential score
            viral_scores = {'low': 3, 'medium': 6, 'high': 10}
            viral_score = viral_scores.get(segment.get('viral_potential', 'medium'), 6)
            
            # Engagement score
            engagement = segment.get('engagement_score', 5)
            
            # Calculate composite score
            composite_score = (
                engagement * weights['engagement_score'] +
                viral_score * weights['viral_potential'] +
                duration_score * weights['duration_match']
            )
            
            segment_copy = segment.copy()
            segment_copy['composite_score'] = round(composite_score, 2)
            segment_copy['duration'] = round(duration, 1)
            scored_segments.append(segment_copy)
        
        # Sort by composite score and return top clips
        scored_segments.sort(key=lambda x: x['composite_score'], reverse=True)
        best_clips = scored_segments[:max_clips]
        
        print(f"[DEBUG] Selected {len(best_clips)} best clips for {platform}")
        for i, clip in enumerate(best_clips):
            print(f"  Clip {i+1}: Score {clip['composite_score']}, Duration {clip['duration']}s, Viral: {clip.get('viral_potential', 'N/A')}")
        
        return best_clips