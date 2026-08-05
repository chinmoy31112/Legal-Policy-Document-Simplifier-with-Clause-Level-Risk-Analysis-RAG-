"""
LLM service using Google GenAI SDK.

Wrapper around Gemini 2.5 Flash for executing the reasoning pipeline
with structured JSON output constraints.
"""

import json
from typing import Any

from google import genai
from google.genai import types

from app.config import get_settings
from app.core.exceptions import AIServiceError
from app.core.logging import get_logger
from app.ai.prompts import SYSTEM_INSTRUCTION

logger = get_logger(__name__)


class LLMService:
    """Service for interacting with Gemini for reasoning tasks."""

    def __init__(self):
        self.settings = get_settings()
        if not self.settings.google_api_key:
            logger.warning("google_api_key_missing", message="GOOGLE_API_KEY is not set.")
            
        self.client = genai.Client(api_key=self.settings.google_api_key)
        self.model = self.settings.gemini_llm_model

    async def generate_structured_analysis(self, prompt: str, schema_class: Any) -> dict[str, Any]:
        """
        Generate a structured JSON response from Gemini using the new SDK.
        
        Args:
            prompt: The formatted prompt string containing the clause and references.
            schema_class: The Pydantic model class defining the expected JSON structure.
            
        Returns:
            A dictionary parsed from the LLM's JSON output.
            
        Raises:
            AIServiceError: If the API call fails or parsing fails.
        """
        try:
            # We use the sync client here. 
            # In a production async environment, we should run this in a threadpool 
            # or use `client.aio` if the SDK exposes it.
            
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_INSTRUCTION,
                    temperature=self.settings.gemini_temperature,
                    max_output_tokens=self.settings.gemini_max_output_tokens,
                    response_mime_type="application/json",
                    response_schema=schema_class,
                ),
            )
            
            if not response.text:
                raise AIServiceError("Received empty response from LLM.")
                
            # Parse the JSON response
            try:
                # The SDK usually returns a string containing the JSON
                result_dict = json.loads(response.text)
                return result_dict
            except json.JSONDecodeError as e:
                logger.error("json_decode_error", response=response.text, error=str(e))
                raise AIServiceError(f"Failed to parse LLM response as JSON: {e}")
                
        except Exception as e:
            logger.error("llm_generation_failed", error=str(e))
            raise AIServiceError(f"LLM generation failed: {e}")
