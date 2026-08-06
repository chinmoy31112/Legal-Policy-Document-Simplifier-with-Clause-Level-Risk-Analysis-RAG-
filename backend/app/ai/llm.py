"""
LLM service using Google GenAI SDK.

Wrapper around Gemini for executing the reasoning pipeline
with structured JSON output constraints.
Uses the async client (client.aio) for non-blocking IO.
Includes retry logic with exponential backoff for rate limits.
"""

import asyncio
import json
import random
from typing import Any

from google import genai
from google.genai import types

from app.config import get_settings
from app.core.exceptions import AIServiceError
from app.core.logging import get_logger
from app.ai.prompts import SYSTEM_INSTRUCTION

logger = get_logger(__name__)

MAX_RETRIES = 5
BASE_DELAY = 2.0  # seconds


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
        Generate a structured JSON response from Gemini using the async client.
        Includes retry logic with exponential backoff for 429/503 errors.
        """
        last_error = None
        
        for attempt in range(MAX_RETRIES):
            try:
                response = await self.client.aio.models.generate_content(
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
                    
                try:
                    result_dict = json.loads(response.text)
                    return result_dict
                except json.JSONDecodeError as e:
                    logger.error("json_decode_error", response=response.text, error=str(e))
                    raise AIServiceError(f"Failed to parse LLM response as JSON: {e}")
                    
            except AIServiceError:
                raise
            except Exception as e:
                last_error = e
                error_str = str(e)
                
                # Check if it's a retryable error (429 rate limit or 503 unavailable)
                is_retryable = any(code in error_str for code in ["429", "503", "RESOURCE_EXHAUSTED", "UNAVAILABLE"])
                
                if is_retryable and attempt < MAX_RETRIES - 1:
                    # Exponential backoff with jitter
                    delay = BASE_DELAY * (2 ** attempt) + random.uniform(0, 1)
                    logger.warning(
                        "llm_retrying", 
                        attempt=attempt + 1, 
                        max_retries=MAX_RETRIES,
                        delay=f"{delay:.1f}s",
                        error=error_str[:200]
                    )
                    await asyncio.sleep(delay)
                    continue
                else:
                    logger.error("llm_generation_failed", error=error_str, attempt=attempt + 1)
                    raise AIServiceError(f"LLM generation failed: {e}")
        
        # Should not reach here, but just in case
        raise AIServiceError(f"LLM generation failed after {MAX_RETRIES} retries: {last_error}")
