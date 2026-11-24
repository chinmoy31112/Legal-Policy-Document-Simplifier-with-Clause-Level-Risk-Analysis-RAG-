"""
Retrieval Service coordinating Embedder and VectorStore.

Enforces Rule 1: Retrieval before reasoning, with explicit no_reference_found flag.
Enforces Rule 8: Guardrails preventing dimension or model mismatch.
"""

from typing import Any

from pydantic import BaseModel, Field

from app.ai.embedding import GeminiEmbedder
from app.ai.interfaces import Embedder, RetrievalResult, VectorRecord, VectorStore
from app.ai.vector_store import get_vector_store
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class RetrievalResponse(BaseModel):
    """Encapsulates vector search results, similarity thresholding, and no_reference_found."""

    query_text: str
    results: list[RetrievalResult] = Field(default_factory=list)
    no_reference_found: bool = False
    best_score: float = 0.0
    retrieved_count: int = 0
    similarity_threshold: float = 0.70


class RetrievalService:
    """
    Coordinates embedding generation and vector similarity search.
    Provides top-k search, category filtering, and threshold enforcement.
    """

    def __init__(
        self,
        embedder: Embedder | None = None,
        vector_store: VectorStore | None = None,
    ):
        self.settings = get_settings()
        self.embedder = embedder or GeminiEmbedder()
        self.vector_store = vector_store or get_vector_store()

    async def index_reference_clauses(
        self,
        clauses: list[dict[str, Any]],
    ) -> int:
        """
        Embed and persist reference clauses with full metadata.
        """
        if not clauses:
            return 0

        texts = [c["text"] for c in clauses]
        vectors = await self.embedder.embed_texts(texts, task_type="RETRIEVAL_DOCUMENT")

        records: list[VectorRecord] = []
        for i, c in enumerate(clauses):
            rec = VectorRecord(
                id=c["id"],
                vector=vectors[i],
                model_name=self.embedder.model_name,
                dimension=self.embedder.dimension,
                metadata={
                    "clause_id": c["id"],
                    "title": c.get("title", ""),
                    "category": c.get("category", "General"),
                    "document_type": c.get("document_type", ""),
                    "source_document": c.get("source", ""),
                    "jurisdiction": c.get("jurisdiction", "General"),
                    "version": c.get("version", "1.0.0"),
                    "language": c.get("language", "en"),
                    "why_standard_or_risky": c.get("why_standard_or_risky", ""),
                    "text": c["text"],
                },
            )
            records.append(rec)

        await self.vector_store.add_vectors(records)
        logger.info("indexed_reference_clauses", count=len(records))
        return len(records)

    async def retrieve(
        self,
        query_text: str,
        top_k: int | None = None,
        category: str | None = None,
        min_similarity: float | None = None,
        query_vector: list[float] | None = None,
    ) -> RetrievalResponse:
        """
        Retrieve standard or risky reference clauses matching the query clause text.
        Reuses query_vector when provided to avoid duplicate embeddings (Rule: single embedding reused).

        Enforces:
        - Similarity threshold filtering.
        - Sets no_reference_found = True if zero matches clear the threshold.
        """
        k = top_k or self.settings.retrieval_top_k
        threshold = (
            min_similarity
            if min_similarity is not None
            else self.settings.retrieval_similarity_threshold
        )

        filters: dict[str, Any] = {}
        if category:
            filters["category"] = category

        # 1. Use provided query embedding or generate once from embedder
        if query_vector is None:
            query_vector = await self.embedder.embed_query(query_text)

        # 2. Query VectorStore with model/dimension guardrail
        raw_results = await self.vector_store.search(
            query_vector=query_vector,
            top_k=k,
            filters=filters or None,
            query_model_name=self.embedder.model_name,
        )

        # 3. Apply similarity threshold
        filtered_results = [r for r in raw_results if r.score >= threshold]
        best_score = (
            filtered_results[0].score
            if filtered_results
            else (raw_results[0].score if raw_results else 0.0)
        )

        # Rule 1: Explicit flag when nothing clears the similarity threshold
        no_ref_found = len(filtered_results) == 0

        logger.debug(
            "retrieval_completed",
            raw_hits=len(raw_results),
            filtered_hits=len(filtered_results),
            no_reference_found=no_ref_found,
            best_score=best_score,
            threshold=threshold,
        )

        return RetrievalResponse(
            query_text=query_text,
            results=filtered_results,
            no_reference_found=no_ref_found,
            best_score=best_score,
            retrieved_count=len(filtered_results),
            similarity_threshold=threshold,
        )
