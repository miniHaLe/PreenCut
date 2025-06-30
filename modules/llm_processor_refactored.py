"""Refactored LLM processor using the new service architecture."""

import json
from typing import List, Dict, Optional, Any, Union

from core.logging import get_logger
from core.dependency_injection import get_container
from core.exceptions import LLMProcessingError, ConfigurationError
from services.interfaces import LLMServiceInterface
from config.settings import get_settings


class LLMProcessorRefactored:
    """Refactored LLM processor using dependency injection and new architecture."""
    
    def __init__(self, llm_model: str = None):
        self.logger = get_logger(__name__)
        self.container = get_container()
        self.settings = get_settings()
        
        try:
            if llm_model:
                # Create specific LLM service instance for this model
                from services.llm_service import LLMService
                self.llm_service = LLMService(llm_model)
            else:
                # Use the default registered service
                self.llm_service = self.container.get_service(LLMServiceInterface)
            
            self.logger.info("LLM processor initialized", {
                "model": getattr(self.llm_service, 'model', 'unknown')
            })
            
        except Exception as e:
            self.logger.error("Failed to initialize LLM processor", {"error": str(e)})
            raise ConfigurationError(f"LLM processor initialization failed: {str(e)}") from e
    
    def process_text(self, text: str, processing_type: str = "summarize", 
                     options: Dict[str, Any] = None) -> str:
        """Process text using LLM with specified processing type."""
        try:
            self.logger.info("Processing text with LLM", {
                "processing_type": processing_type,
                "text_length": len(text),
                "options": options or {}
            })
            
            if not text.strip():
                raise LLMProcessingError("Empty text provided for processing")
            
            # Use the service to process transcript
            result = self.llm_service.process_transcript(text, processing_type)
            
            self.logger.info("Text processing completed", {
                "processing_type": processing_type,
                "result_length": len(result)
            })
            
            return result
            
        except Exception as e:
            self.logger.error("Text processing failed", {
                "processing_type": processing_type,
                "text_length": len(text),
                "error": str(e)
            })
            if isinstance(e, LLMProcessingError):
                raise
            raise LLMProcessingError(f"Text processing failed: {str(e)}") from e
    
    def summarize_transcript(self, transcript_text: str, max_length: int = None) -> str:
        """Summarize transcript text."""
        try:
            self.logger.info("Summarizing transcript", {
                "transcript_length": len(transcript_text),
                "max_length": max_length
            })
            
            # Add length constraint to the prompt if specified
            if max_length:
                enhanced_prompt = f"Summarize the following transcript in no more than {max_length} words:\n\n{transcript_text}"
                result = self.llm_service.process_transcript(enhanced_prompt, "summarize")
            else:
                result = self.llm_service.process_transcript(transcript_text, "summarize")
            
            self.logger.info("Transcript summarization completed", {
                "original_length": len(transcript_text),
                "summary_length": len(result)
            })
            
            return result
            
        except Exception as e:
            self.logger.error("Transcript summarization failed", {
                "transcript_length": len(transcript_text),
                "error": str(e)
            })
            raise LLMProcessingError(f"Summarization failed: {str(e)}") from e
    
    def extract_keywords(self, text: str, max_keywords: int = 20) -> List[str]:
        """Extract keywords from text."""
        try:
            self.logger.info("Extracting keywords", {
                "text_length": len(text),
                "max_keywords": max_keywords
            })
            
            enhanced_prompt = f"Extract the top {max_keywords} most important keywords and phrases from this text. Return as a JSON array:\n\n{text}"
            result = self.llm_service.process_transcript(enhanced_prompt, "extract_keywords")
            
            # Try to parse as JSON
            try:
                keywords = json.loads(result)
                if isinstance(keywords, list):
                    keywords = [str(kw).strip() for kw in keywords[:max_keywords]]
                else:
                    # Fallback: split by common delimiters
                    keywords = [kw.strip() for kw in result.replace('\n', ',').split(',') if kw.strip()][:max_keywords]
            except json.JSONDecodeError:
                # Fallback: split by common delimiters
                keywords = [kw.strip() for kw in result.replace('\n', ',').split(',') if kw.strip()][:max_keywords]
            
            self.logger.info("Keyword extraction completed", {
                "keywords_count": len(keywords)
            })
            
            return keywords
            
        except Exception as e:
            self.logger.error("Keyword extraction failed", {
                "text_length": len(text),
                "error": str(e)
            })
            raise LLMProcessingError(f"Keyword extraction failed: {str(e)}") from e
    
    def analyze_sentiment(self, text: str) -> Dict[str, Any]:
        """Analyze sentiment of text."""
        try:
            self.logger.info("Analyzing sentiment", {"text_length": len(text)})
            
            result = self.llm_service.process_transcript(text, "sentiment_analysis")
            
            # Try to extract structured sentiment data
            sentiment_data = {
                "analysis": result,
                "sentiment": "neutral",
                "confidence": 0.5,
                "emotions": []
            }
            
            # Simple keyword-based sentiment detection as fallback
            result_lower = result.lower()
            if any(word in result_lower for word in ["positive", "happy", "good", "excellent", "great"]):
                sentiment_data["sentiment"] = "positive"
                sentiment_data["confidence"] = 0.7
            elif any(word in result_lower for word in ["negative", "sad", "bad", "terrible", "awful"]):
                sentiment_data["sentiment"] = "negative"
                sentiment_data["confidence"] = 0.7
            
            self.logger.info("Sentiment analysis completed", {
                "sentiment": sentiment_data["sentiment"],
                "confidence": sentiment_data["confidence"]
            })
            
            return sentiment_data
            
        except Exception as e:
            self.logger.error("Sentiment analysis failed", {
                "text_length": len(text),
                "error": str(e)
            })
            raise LLMProcessingError(f"Sentiment analysis failed: {str(e)}") from e
    
    def generate_title(self, text: str, max_length: int = 60) -> str:
        """Generate a title for the given text."""
        try:
            self.logger.info("Generating title", {
                "text_length": len(text),
                "max_length": max_length
            })
            
            prompt = f"Generate a concise, engaging title (max {max_length} characters) for this content:\n\n{text[:1000]}..."
            result = self.llm_service.process_transcript(prompt, "summarize")
            
            # Clean up the result
            title = result.strip().strip('"').strip("'")
            if len(title) > max_length:
                title = title[:max_length-3] + "..."
            
            self.logger.info("Title generation completed", {"title": title})
            
            return title
            
        except Exception as e:
            self.logger.error("Title generation failed", {
                "text_length": len(text),
                "error": str(e)
            })
            raise LLMProcessingError(f"Title generation failed: {str(e)}") from e
    
    def analyze_segments(self, segments: List[Dict], analysis_type: str = "importance") -> List[Dict]:
        """Analyze video segments using the LLM service."""
        try:
            self.logger.info("Analyzing segments", {
                "segments_count": len(segments),
                "analysis_type": analysis_type
            })
            
            enhanced_segments = self.llm_service.analyze_segments(segments, analysis_type)
            
            self.logger.info("Segment analysis completed", {
                "enhanced_segments": len(enhanced_segments)
            })
            
            return enhanced_segments
            
        except Exception as e:
            self.logger.error("Segment analysis failed", {
                "segments_count": len(segments),
                "analysis_type": analysis_type,
                "error": str(e)
            })
            raise LLMProcessingError(f"Segment analysis failed: {str(e)}") from e
    
    def generate_highlights(self, transcript_data: Dict, max_highlights: int = 5,
                           criteria: List[str] = None) -> List[Dict]:
        """Generate highlight segments from transcript data."""
        try:
            self.logger.info("Generating highlights", {
                "max_highlights": max_highlights,
                "criteria": criteria or ["importance", "engagement"]
            })
            
            highlights = self.llm_service.generate_highlights(transcript_data, max_highlights)
            
            # Enhance highlights with additional metadata
            enhanced_highlights = []
            for i, highlight in enumerate(highlights):
                enhanced_highlight = {
                    **highlight,
                    "id": f"highlight_{i+1}",
                    "created_by": "llm_processor",
                    "criteria": criteria or ["importance", "engagement"]
                }
                enhanced_highlights.append(enhanced_highlight)
            
            self.logger.info("Highlight generation completed", {
                "highlights_generated": len(enhanced_highlights)
            })
            
            return enhanced_highlights
            
        except Exception as e:
            self.logger.error("Highlight generation failed", {
                "max_highlights": max_highlights,
                "error": str(e)
            })
            raise LLMProcessingError(f"Highlight generation failed: {str(e)}") from e
    
    def generate_social_media_content(self, text: str, platform: str = "general",
                                     length_limit: int = None) -> Dict[str, str]:
        """Generate social media content from text."""
        try:
            self.logger.info("Generating social media content", {
                "text_length": len(text),
                "platform": platform,
                "length_limit": length_limit
            })
            
            # Platform-specific prompts and limits
            platform_configs = {
                "twitter": {"limit": 280, "style": "concise and engaging with hashtags"},
                "facebook": {"limit": 500, "style": "conversational and detailed"},
                "instagram": {"limit": 150, "style": "visual-focused with hashtags"},
                "linkedin": {"limit": 700, "style": "professional and informative"},
                "general": {"limit": length_limit or 300, "style": "engaging and shareable"}
            }
            
            config = platform_configs.get(platform, platform_configs["general"])
            
            prompt = (f"Create {config['style']} social media content for {platform} "
                     f"(max {config['limit']} characters) based on this content:\n\n{text}")
            
            result = self.llm_service.process_transcript(prompt, "summarize")
            
            # Generate additional variations
            variations = {
                "main": result[:config['limit']],
                "short": result[:config['limit']//2] if len(result) > config['limit']//2 else result,
                "hashtags": self._extract_hashtags(result),
                "platform": platform,
                "character_count": len(result)
            }
            
            self.logger.info("Social media content generated", {
                "platform": platform,
                "character_count": variations["character_count"]
            })
            
            return variations
            
        except Exception as e:
            self.logger.error("Social media content generation failed", {
                "platform": platform,
                "error": str(e)
            })
            raise LLMProcessingError(f"Social media content generation failed: {str(e)}") from e
    
    def _extract_hashtags(self, text: str) -> List[str]:
        """Extract hashtags from text."""
        import re
        hashtags = re.findall(r'#\w+', text)
        return hashtags[:10]  # Limit to 10 hashtags
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the current LLM model."""
        try:
            info = {
                "model": getattr(self.llm_service, 'model', 'unknown'),
                "base_url": getattr(self.llm_service, 'base_url', 'unknown'),
                "temperature": getattr(self.llm_service, 'temperature', 0.3),
                "max_tokens": getattr(self.llm_service, 'max_tokens', 4096),
                "service_type": type(self.llm_service).__name__
            }
            
            self.logger.debug("Model info retrieved", info)
            return info
            
        except Exception as e:
            self.logger.error("Failed to get model info", {"error": str(e)})
            return {"error": str(e)}
    
    def health_check(self) -> Dict[str, Any]:
        """Perform health check on LLM processing capabilities."""
        try:
            self.logger.debug("Performing LLM processor health check")
            
            # Check LLM service health
            llm_health = self.llm_service.health_check()
            
            health_status = {
                "status": "healthy",
                "llm_service": llm_health,
                "model_info": self.get_model_info(),
                "capabilities": [
                    "text_processing",
                    "summarization", 
                    "keyword_extraction",
                    "sentiment_analysis",
                    "title_generation",
                    "segment_analysis",
                    "highlight_generation",
                    "social_media_content"
                ]
            }
            
            # Overall status based on LLM service health
            if llm_health.get("status") != "healthy":
                health_status["status"] = "degraded"
            
            self.logger.info("LLM processor health check completed", {
                "status": health_status["status"]
            })
            
            return health_status
            
        except Exception as e:
            health_status = {
                "status": "unhealthy",
                "error": str(e)
            }
            
            self.logger.error("LLM processor health check failed", health_status)
            return health_status
