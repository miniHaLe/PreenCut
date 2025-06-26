import json
import requests
from config import LLM_MODEL_OPTIONS
from typing import List, Dict, Optional
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

    def _call_ollama(self, messages: List[Dict], format_json: bool = True) -> str:
        """Make API call to Ollama"""
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
        
        # Add JSON format constraint if needed
        if format_json:
            payload["format"] = "json"
            
        print(f"[DEBUG] Sending request to {self.base_url}/api/generate")
        print(f"[DEBUG] Model: {self.model}, Format JSON: {format_json}")
            
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
        
        # Build system prompt with explicit JSON format instructions
        system_prompt = (
            "You are a professional video editing assistant. You must analyze subtitle content and return video segments. "
            "CRITICAL INSTRUCTIONS:\n"
            "1. You must respond with ONLY a valid JSON array\n"
            "2. No explanations, no markdown, no code blocks, no thinking out loud\n"
            "3. Do not use <think> tags or any other XML tags\n"
            "4. Start your response immediately with [ and end with ]\n"
            "5. Each object in the array must have exactly these 4 keys: start, end, summary, tags\n"
            "6. Times should be in seconds as numbers\n"
            "Example of correct response: "
            '[{"start": 0, "end": 30, "summary": "Video introduction", "tags": ["intro"]}, {"start": 30, "end": 60, "summary": "Main content", "tags": ["content"]}]'
        )

        # User prompt (used if there is a custom prompt)
        user_prompt = prompt or (
            "Analyze the subtitle content and create up to 10 video segments. "
            "Each segment needs: start time (seconds), end time (seconds), summary (one sentence), tags (1-3 words). "
            "Return ONLY the JSON array, nothing else. Start immediately with [ and end with ]."
        )

        # Combined complete prompt
        full_prompt = f"{user_prompt}\n\nSubtitle content:\n{subtitle_text}"

        print(f"[DEBUG] Calling Ollama with model: {self.model}")
        print(f"[DEBUG] Subtitle length: {len(subtitle_text)} characters")

        # Try with JSON format first
        try:
            result = self._call_ollama([
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": full_prompt}
            ], format_json=True)
            
            print(f"[DEBUG] Raw Ollama response (first 500 chars): {result[:500]}")
            
            segments = self._parse_and_validate_response(result)
            if segments:
                print(f"[DEBUG] Successfully parsed {len(segments)} segments")
                return segments
                
        except Exception as e:
            print(f"[DEBUG] JSON format failed: {str(e)}")
            
        # Fallback: Try without JSON format constraint but with stricter prompt
        try:
            print("[DEBUG] Trying fallback without JSON format constraint...")
            
            # More aggressive prompt for fallback
            strict_prompt = (
                "IMPORTANT: Respond only with a JSON array. Do not think out loud. "
                "Do not use <think> tags. Start immediately with [ and end with ]. "
                f"{user_prompt}\n\nSubtitle content:\n{subtitle_text}"
            )
            
            result = self._call_ollama([
                {"role": "user", "content": strict_prompt}
            ], format_json=False)
            
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
            
            # Try to find JSON array in the response
            start_idx = result.find('[')
            end_idx = result.rfind(']')
            
            if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                json_str = result[start_idx:end_idx + 1]
                print(f"[DEBUG] Extracted JSON: {json_str[:200]}...")
            else:
                json_str = result
                
            # Parse JSON
            segments = json.loads(json_str)
            
            # Validate the structure
            if not isinstance(segments, list):
                print(f"[DEBUG] Response is not a list: {type(segments)}")
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
                segment.setdefault('summary', f"Segment {i+1}")
                segment.setdefault('tags', ['segment'])
                
                # Type conversion and validation
                try:
                    segment['start'] = float(segment['start'])
                    segment['end'] = float(segment['end'])
                    if not isinstance(segment['summary'], str):
                        segment['summary'] = str(segment['summary'])
                    if not isinstance(segment['tags'], list):
                        segment['tags'] = [str(segment['tags'])] if segment['tags'] else ['segment']
                    
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
                "summary": f"Video segment {i + 1}",
                "tags": ["segment", f"part{i + 1}"]
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