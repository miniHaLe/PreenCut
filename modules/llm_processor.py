import json
import os

from openai import OpenAI
from config import LLM_MODEL_OPTIONS
from typing import List, Dict, Optional


class LLMProcessor:
    def __init__(self, llm_model: str):
        for model in LLM_MODEL_OPTIONS:
            if model['label'] == llm_model:
                self.api_key = os.getenv(model['api_key_env_name'])
                self.client = OpenAI(
                    api_key=self.api_key,
                    base_url=model['base_url'],
                )
                self.model = model['model']
                self.temperature = model.get('temperature', 0.3)
                self.max_tokens = model.get('max_tokens', 4096)
                break

        if not hasattr(self, 'client'):
            raise ValueError(
                f"Unsupported LLM model: {llm_model}. Available models: "
                f"{', '.join([m['label'] for m in LLM_MODEL_OPTIONS])}"
            )

    def segment_video(self, subtitles: str,
                      prompt: Optional[str] = None) -> \
            List[Dict]:
        """Use a large model to segment videos based on subtitle content"""
        if not self.api_key:
            raise ValueError("OpenAI API key is not set")

        # Build system prompt
        system_prompt = (
            "You are a professional video editing assistant who needs to process the video into segments based on the subtitle content provided and user requirements."
            "Each snippet should contain the following information: start time (seconds), end time (seconds), a one-sentence summary, and 1-3 topic tags."
            "The lengths of different segments should not differ too much, and the longest single segment should not exceed 30% of the total length, but thematic coherence should still be given priority."
            "The return format must be JSON, containing a list of dictionaries, each dictionary has four keys: start, end, summary, tags."
        )

        # User prompt (used if there is a custom prompt)
        user_prompt = prompt or (
            "Please divide the video into no more than 10 meaningful segments based on the subtitle content below."
            "Each segment should contain coherent topic content, a one-sentence summary and 1-3 topic tags."
            "The time information needs to be accurate to the second."
        )

        # Combined complete prompt
        full_prompt = f"{user_prompt}\n\Subtitle content:\n{subtitles}"

        # Calling the OpenAI API
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": full_prompt}
            ],
            temperature=self.temperature,
            max_tokens=self.max_tokens
        )

        # Parsing the response
        result = response.choices[0].message.content

        # Try to extract JSON content
        try:
            # Remove possible code block markers
            if result.startswith("```json"):
                result = result[7:-3].strip()
            elif result.startswith("```"):
                result = result[3:-3].strip()

            segments = json.loads(result)
            return segments
        except json.JSONDecodeError:
            # Try parsing directly as JSON
            try:
                segments = json.loads(result)
                return segments
            except:
                raise ValueError(
                    f"An error occurred while processing the large model. The large model returns:{result}"
                )
