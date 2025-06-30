"""LLM service implementation for text processing and analysis."""

import json
import requests
from typing import List, Dict, Optional, Any, Union

from core.logging import get_logger
from core.exceptions import LLMProcessingError, ConfigurationError
from services.interfaces import LLMServiceInterface
from config.settings import get_settings


class LLMService(LLMServiceInterface):
    """Production-ready LLM service with enhanced error handling and monitoring."""
    
    def __init__(self, llm_model: str):
        self.logger = get_logger(__name__)
        self.settings = get_settings()
        self._initialize_model(llm_model)
    
    def _initialize_model(self, llm_model: str) -> None:
        """Initialize LLM model configuration."""
        try:
            # Find model configuration
            model_config = None
            for model in self.settings.llm_model_options:
                if model['label'] == llm_model:
                    model_config = model
                    break
            
            if not model_config:
                available_models = [m['label'] for m in self.settings.llm_model_options]
                raise ConfigurationError(
                    f"Unsupported LLM model: {llm_model}. "
                    f"Available models: {', '.join(available_models)}"
                )
            
            # Set configuration
            self.base_url = model_config.get('base_url', 'http://localhost:11434')
            self.model = model_config['model']
            self.temperature = model_config.get('temperature', 0.3)
            self.max_tokens = model_config.get('max_tokens', 4096)
            
            self.logger.info("LLM model initialized", {
                "model": self.model,
                "base_url": self.base_url,
                "temperature": self.temperature,
                "max_tokens": self.max_tokens
            })
            
        except Exception as e:
            self.logger.error("Failed to initialize LLM model", {
                "llm_model": llm_model,
                "error": str(e)
            })
            raise ConfigurationError(f"LLM initialization failed: {str(e)}") from e
    
    def _call_ollama(self, messages: List[Dict], format_schema: Optional[Dict[str, Any]] = None) -> str:
        """Make API call to Ollama with optional structured output format."""
        try:
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
                payload["format"] = format_schema
            
            self.logger.debug("Making Ollama API call", {
                "model": self.model,
                "prompt_length": len(prompt),
                "has_schema": format_schema is not None
            })
            
            # Make API request
            response = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=self.settings.llm_timeout
            )
            
            response.raise_for_status()
            result = response.json()
            
            if 'response' not in result:
                raise LLMProcessingError("Invalid response format from Ollama API")
            
            response_text = result['response']
            
            self.logger.debug("Ollama API call completed", {
                "response_length": len(response_text),
                "tokens_used": result.get('eval_count', 0)
            })
            
            return response_text
            
        except requests.exceptions.Timeout as e:
            error_msg = f"Ollama API request timed out after {self.settings.llm_timeout}s"
            self.logger.error(error_msg, {"model": self.model})
            raise LLMProcessingError(error_msg) from e
        
        except requests.exceptions.ConnectionError as e:
            error_msg = f"Failed to connect to Ollama API at {self.base_url}"
            self.logger.error(error_msg, {"model": self.model})
            raise LLMProcessingError(error_msg) from e
        
        except requests.exceptions.HTTPError as e:
            error_msg = f"Ollama API returned error: {e.response.status_code} - {e.response.text}"
            self.logger.error(error_msg, {"model": self.model})
            raise LLMProcessingError(error_msg) from e
        
        except Exception as e:
            self.logger.error("Unexpected error during Ollama API call", {
                "model": self.model,
                "error": str(e)
            })
            raise LLMProcessingError(f"LLM API call failed: {str(e)}") from e
    
    def process_transcript(self, transcript_text: str, processing_type: str = "summarize") -> str:
        """Process transcript with specified processing type."""
        try:
            self.logger.info("Processing transcript", {
                "processing_type": processing_type,
                "transcript_length": len(transcript_text)
            })
            
            if not transcript_text.strip():
                raise LLMProcessingError("Empty transcript provided")
            
            # Define processing prompts
            system_prompts = {
                "summarize": "You are an expert at summarizing video transcripts. Provide a concise, accurate summary that captures the main points and key information.",
                "extract_keywords": "You are an expert at extracting key topics and keywords from text. Extract the most important keywords and phrases from the transcript.",
                "sentiment_analysis": "You are an expert at sentiment analysis. Analyze the sentiment and tone of the transcript content.",
                "topic_extraction": "You are an expert at topic modeling. Identify and extract the main topics discussed in the transcript.",
                "highlight_moments": "You are an expert at identifying key moments in video content. Identify the most important or interesting segments that should be highlighted."
            }
            
            if processing_type not in system_prompts:
                raise LLMProcessingError(f"Unsupported processing type: {processing_type}")
            
            messages = [
                {"role": "system", "content": system_prompts[processing_type]},
                {"role": "user", "content": f"Please process this transcript:\n\n{transcript_text}"}
            ]
            
            result = self._call_ollama(messages)
            
            self.logger.info("Transcript processing completed", {
                "processing_type": processing_type,
                "result_length": len(result)
            })
            
            return result
            
        except Exception as e:
            self.logger.error("Transcript processing failed", {
                "processing_type": processing_type,
                "error": str(e)
            })
            if isinstance(e, LLMProcessingError):
                raise
            raise LLMProcessingError(f"Transcript processing failed: {str(e)}") from e
    
    def analyze_segments(self, segments: List[Dict], analysis_type: str = "importance") -> List[Dict]:
        """Analyze video segments and return enhanced segment data."""
        try:
            self.logger.info("Analyzing segments", {
                "analysis_type": analysis_type,
                "segments_count": len(segments)
            })
            
            if not segments:
                raise LLMProcessingError("No segments provided for analysis")
            
            # Prepare segment analysis prompt
            segments_text = ""
            for i, segment in enumerate(segments):
                text = segment.get('text', '')
                start = segment.get('start', 0)
                end = segment.get('end', 0)
                segments_text += f"Segment {i+1} ({start:.2f}s - {end:.2f}s): {text}\n\n"
            
            analysis_prompts = {
                "importance": "Analyze each segment and rate its importance on a scale of 1-10. Consider factors like information density, uniqueness, and potential viewer interest.",
                "sentiment": "Analyze the sentiment of each segment (positive, negative, neutral) and provide confidence scores.",
                "topics": "Identify the main topics discussed in each segment.",
                "action_items": "Extract any action items, conclusions, or key takeaways from each segment.",
                "questions": "Identify any questions raised or answered in each segment."
            }
            
            if analysis_type not in analysis_prompts:
                raise LLMProcessingError(f"Unsupported analysis type: {analysis_type}")
            
            messages = [
                {"role": "system", "content": f"{analysis_prompts[analysis_type]} Respond in JSON format."},
                {"role": "user", "content": f"Analyze these video segments:\n\n{segments_text}"}
            ]
            
            # Request structured JSON output
            format_schema = {
                "type": "object",
                "properties": {
                    "analysis": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "segment_index": {"type": "integer"},
                                "score": {"type": "number"},
                                "analysis": {"type": "string"},
                                "metadata": {"type": "object"}
                            }
                        }
                    }
                }
            }
            
            result = self._call_ollama(messages, format_schema)
            
            # Parse JSON response
            try:
                analysis_data = json.loads(result)
                enhanced_segments = []
                
                for i, segment in enumerate(segments):
                    enhanced_segment = segment.copy()
                    
                    # Find corresponding analysis
                    analysis_item = None
                    if 'analysis' in analysis_data:
                        for item in analysis_data['analysis']:
                            if item.get('segment_index') == i + 1:
                                analysis_item = item
                                break
                    
                    if analysis_item:
                        enhanced_segment[f'{analysis_type}_score'] = analysis_item.get('score', 0)
                        enhanced_segment[f'{analysis_type}_analysis'] = analysis_item.get('analysis', '')
                        enhanced_segment[f'{analysis_type}_metadata'] = analysis_item.get('metadata', {})
                    
                    enhanced_segments.append(enhanced_segment)
                
                self.logger.info("Segment analysis completed", {
                    "analysis_type": analysis_type,
                    "enhanced_segments": len(enhanced_segments)
                })
                
                return enhanced_segments
                
            except json.JSONDecodeError as e:
                self.logger.warning("Failed to parse JSON response, using raw text", {
                    "analysis_type": analysis_type,
                    "error": str(e)
                })
                # Fallback: add raw analysis to each segment
                enhanced_segments = []
                for segment in segments:
                    enhanced_segment = segment.copy()
                    enhanced_segment[f'{analysis_type}_analysis'] = result
                    enhanced_segments.append(enhanced_segment)
                return enhanced_segments
            
        except Exception as e:
            self.logger.error("Segment analysis failed", {
                "analysis_type": analysis_type,
                "error": str(e)
            })
            if isinstance(e, LLMProcessingError):
                raise
            raise LLMProcessingError(f"Segment analysis failed: {str(e)}") from e
    
    def generate_highlights(self, transcript_data: Dict, max_highlights: int = 5) -> List[Dict]:
        """Generate highlight segments from transcript data."""
        try:
            self.logger.info("Generating highlights", {
                "max_highlights": max_highlights,
                "has_segments": 'segments' in transcript_data
            })
            
            if 'segments' not in transcript_data:
                raise LLMProcessingError("No segments found in transcript data")
            
            segments = transcript_data['segments']
            
            # Create summary of all segments for context
            segments_summary = ""
            for i, segment in enumerate(segments):
                text = segment.get('text', '')
                start = segment.get('start', 0)
                end = segment.get('end', 0)
                segments_summary += f"[{start:.1f}s-{end:.1f}s]: {text}\n"
            
            messages = [
                {
                    "role": "system",
                    "content": f"You are an expert video editor. Identify the {max_highlights} most interesting, "
                               f"important, or engaging segments that would make good highlights. "
                               f"Consider entertainment value, information density, and viewer engagement. "
                               f"Respond with a JSON array of objects containing start_time, end_time, "
                               f"title, and reason for each highlight."
                },
                {
                    "role": "user",
                    "content": f"Generate highlights from this transcript:\n\n{segments_summary}"
                }
            ]
            
            format_schema = {
                "type": "object",
                "properties": {
                    "highlights": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "start_time": {"type": "number"},
                                "end_time": {"type": "number"},
                                "title": {"type": "string"},
                                "reason": {"type": "string"},
                                "importance_score": {"type": "number"}
                            }
                        }
                    }
                }
            }
            
            result = self._call_ollama(messages, format_schema)
            
            try:
                highlights_data = json.loads(result)
                highlights = highlights_data.get('highlights', [])
                
                # Validate and enhance highlights
                validated_highlights = []
                for highlight in highlights[:max_highlights]:
                    if 'start_time' in highlight and 'end_time' in highlight:
                        # Ensure valid time range
                        start_time = max(0, float(highlight['start_time']))
                        end_time = float(highlight['end_time'])
                        
                        if end_time > start_time:
                            validated_highlights.append({
                                'start': start_time,
                                'end': end_time,
                                'title': highlight.get('title', f'Highlight {len(validated_highlights) + 1}'),
                                'reason': highlight.get('reason', ''),
                                'importance_score': highlight.get('importance_score', 5.0),
                                'type': 'highlight'
                            })
                
                self.logger.info("Highlights generated successfully", {
                    "requested_highlights": max_highlights,
                    "generated_highlights": len(validated_highlights)
                })
                
                return validated_highlights
                
            except json.JSONDecodeError as e:
                self.logger.warning("Failed to parse highlights JSON, creating fallback", {
                    "error": str(e)
                })
                # Fallback: use first few segments as highlights
                fallback_highlights = []
                for i, segment in enumerate(segments[:max_highlights]):
                    fallback_highlights.append({
                        'start': segment.get('start', 0),
                        'end': segment.get('end', 10),
                        'title': f'Highlight {i + 1}',
                        'reason': 'Auto-generated from transcript',
                        'importance_score': 5.0,
                        'type': 'highlight'
                    })
                return fallback_highlights
            
        except Exception as e:
            self.logger.error("Highlight generation failed", {
                "max_highlights": max_highlights,
                "error": str(e)
            })
            if isinstance(e, LLMProcessingError):
                raise
            raise LLMProcessingError(f"Highlight generation failed: {str(e)}") from e
    
    def health_check(self) -> Dict[str, Any]:
        """Check if the LLM service is healthy and responsive."""
        try:
            self.logger.debug("Performing LLM health check")
            
            # Simple test query
            messages = [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Respond with 'OK' if you can process this message."}
            ]
            
            start_time = time.time()
            response = self._call_ollama(messages)
            response_time = time.time() - start_time
            
            health_status = {
                "status": "healthy",
                "model": self.model,
                "base_url": self.base_url,
                "response_time_ms": round(response_time * 1000, 2),
                "response_preview": response[:50] if response else "No response"
            }
            
            self.logger.info("LLM health check passed", health_status)
            return health_status
            
        except Exception as e:
            health_status = {
                "status": "unhealthy",
                "model": self.model,
                "base_url": self.base_url,
                "error": str(e)
            }
            
            self.logger.error("LLM health check failed", health_status)
            return health_status


# Import time for health check
import time
