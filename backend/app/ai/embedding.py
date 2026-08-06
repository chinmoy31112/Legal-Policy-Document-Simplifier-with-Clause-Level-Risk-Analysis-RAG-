"""
Embedding service using Google GenAI SDK.

Wrapper around gemini-embedding-2 for generating vector embeddings
from legal clause text. Uses the async client for non-blocking IO.
"""

from typing import Sequence

from google import genai
from google.genai import types

from app.config import get_settings
from app.core.exceptions import AIServiceError
from app.core.logging import get_logger

logger = get_logger(__name__)


class EmbeddingService:
    """Service for generating vector embeddings using Google GenAI."""

    def __init__(self):
        self.settings = get_settings()
        if not self.settings.google_api_key:
            logger.warning("google_api_key_missing", message="GOOGLE_API_KEY is not set.")
            
        self.client = genai.Client(api_key=self.settings.google_api_key)
        self.model = self.settings.gemini_embedding_model
        
    def _create_batches(self, texts: Sequence[str], batch_size: int) -> list[Sequence[str]]:
        """Split a list of texts into smaller batches."""
        return [texts[i:i + batch_size] for i in range(0, len(texts), batch_size)]

    async def generate_embeddings(
        self, texts: Sequence[str], task_type: str = "RETRIEVAL_DOCUMENT"
    ) -> list[list[float]]:
        """
        Generate embeddings for a list of texts using the async client.
        
        Args:
            texts: List of strings to embed.
            task_type: Type of task for the embedding model.
                Use "RETRIEVAL_DOCUMENT" when indexing into the DB.
                Use "RETRIEVAL_QUERY" when searching.
                
        Returns:
            A list of embedding vectors (list of floats).
            
        Raises:
            AIServiceError: If the Google API call fails.
        """
        if not texts:
            return []
            
        try:
            embeddings_list = []
            
            # Process in batches to avoid exceeding API limits
            batches = self._create_batches(texts, self.settings.embedding_batch_size)
            
            for i, batch in enumerate(batches):
                logger.debug("generating_embeddings_batch", batch=i+1, total=len(batches), size=len(batch))
                
                # Use the async client for non-blocking IO
                response = await self.client.aio.models.embed_content(
                    model=self.model,
                    contents=list(batch),
                    config=types.EmbedContentConfig(
                        task_type=task_type,
                    )
                )
                
                if hasattr(response, 'embeddings'):
                    for emb in response.embeddings:
                        embeddings_list.append(emb.values)
                else:
                    raise AIServiceError(f"Unexpected response from embedding model: {type(response)}")

            logger.info("embeddings_generated", count=len(embeddings_list), model=self.model)
            return embeddings_list

        except AIServiceError:
            raise
        except Exception as e:
            logger.error("embedding_generation_failed", error=str(e))
            raise AIServiceError(f"Failed to generate embeddings: {e}")

    async def embed_query(self, query: str) -> list[float]:
        """
        Generate a single embedding for a search query.
        """
        embeddings = await self.generate_embeddings([query], task_type="RETRIEVAL_QUERY")
        return embeddings[0] if embeddings else []
