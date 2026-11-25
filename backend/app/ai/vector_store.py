"""
Vector Store implementation behind abstract interface.

Adheres to Rule 8: One embedding model, model name & dimension stored per vector,
refuses to query on mismatch.
Adheres to Rule 9: Vector store behind an abstract interface.
"""

import json
import math
from pathlib import Path
from typing import Any

from sqlalchemy import text

from app.ai.interfaces import RetrievalResult, VectorRecord, VectorStore
from app.core.config import get_settings
from app.core.database import async_session_factory
from app.core.logging import get_logger

logger = get_logger(__name__)


class InMemoryVectorStore(VectorStore):
    """
    In-memory vector store computing exact cosine similarity.
    Enforces Rule 8 (refuses query on model/dimension mismatch).
    Automatically loads cached benchmark reference clauses from disk when available.
    """

    def __init__(
        self,
        expected_dim: int = 768,
        expected_model: str = "gemini-embedding-2",
        auto_load: bool = True,
    ):
        self.expected_dim = expected_dim
        self.expected_model = expected_model
        self._records: dict[str, VectorRecord] = {}
        if auto_load:
            self._load_cached_reference_records()

    def _load_cached_reference_records(self) -> None:
        """Load pre-embedded reference clauses if available and not already loaded."""
        if self._records:
            return
        cache_path = (
            Path(__file__).resolve().parent.parent.parent
            / "knowledge_base"
            / "reference_clauses_embeddings.json"
        )
        if not cache_path.exists():
            return
        try:
            raw = json.loads(cache_path.read_text(encoding="utf-8"))
            for item in raw:
                rec = VectorRecord(
                    id=item["id"],
                    vector=item["vector"],
                    model_name=item.get("model_name", self.expected_model),
                    dimension=item.get("dimension", self.expected_dim),
                    metadata=item.get("metadata", {}),
                )
                self._records[rec.id] = rec
            logger.info("loaded_cached_reference_clauses", count=len(self._records))
        except Exception as e:
            logger.warning("failed_loading_cached_reference_clauses", error=str(e))

    @property
    def dimension(self) -> int:
        return self.expected_dim

    @property
    def model_name(self) -> str:
        return self.expected_model

    async def add_vectors(self, records: list[VectorRecord]) -> None:
        """Add dense vectors validating model name and dimension."""
        for rec in records:
            if rec.dimension != self.expected_dim:
                raise ValueError(
                    f"Dimension mismatch for vector '{rec.id}': expected {self.expected_dim}, got {rec.dimension}."
                )
            if rec.model_name != self.expected_model:
                raise ValueError(
                    f"Model mismatch for vector '{rec.id}': expected {self.expected_model}, got {rec.model_name}."
                )
            self._records[rec.id] = rec
        logger.debug("in_memory_vectors_added", count=len(records), total=len(self._records))

    async def search(
        self,
        query_vector: list[float],
        top_k: int = 5,
        filters: dict[str, Any] | None = None,
        query_model_name: str | None = None,
    ) -> list[RetrievalResult]:
        """
        Execute cosine similarity search. Refuses to query on model or dimension mismatch.
        """
        # Rule 8: Guardrail on dimension mismatch
        if len(query_vector) != self.expected_dim:
            raise ValueError(
                f"Query refused: vector dimension mismatch. Expected {self.expected_dim}, received {len(query_vector)}."
            )

        # Rule 8: Guardrail on model name mismatch
        if query_model_name and query_model_name != self.expected_model:
            raise ValueError(
                f"Query refused: model mismatch. Expected '{self.expected_model}', received '{query_model_name}'."
            )

        scored: list[tuple[float, VectorRecord]] = []
        for rec in self._records.values():
            # Apply metadata filters
            if filters:
                match = True
                for k, v in filters.items():
                    if v is not None and rec.metadata.get(k) != v:
                        match = False
                        break
                if not match:
                    continue

            # Compute cosine similarity
            dot = sum(a * b for a, b in zip(query_vector, rec.vector, strict=False))
            norm_q = math.sqrt(sum(a * a for a in query_vector)) or 1.0
            norm_r = math.sqrt(sum(b * b for b in rec.vector)) or 1.0
            sim = dot / (norm_q * norm_r)
            scored.append((sim, rec))

        # Sort descending by similarity
        scored.sort(key=lambda x: x[0], reverse=True)

        return [
            RetrievalResult(
                id=rec.id,
                score=round(score, 4),
                metadata=rec.metadata,
            )
            for score, rec in scored[:top_k]
        ]

    async def delete_vectors(self, ids: list[str]) -> None:
        """Remove vectors from memory."""
        for vid in ids:
            self._records.pop(vid, None)


_shared_in_memory_store: InMemoryVectorStore | None = None


def get_shared_in_memory_store(
    expected_dim: int = 768, expected_model: str = "gemini-embedding-2"
) -> InMemoryVectorStore:
    """Return a shared singleton InMemoryVectorStore with cached reference records preloaded."""
    global _shared_in_memory_store
    if _shared_in_memory_store is None:
        _shared_in_memory_store = InMemoryVectorStore(
            expected_dim=expected_dim, expected_model=expected_model
        )
    return _shared_in_memory_store


class PgVectorStore(VectorStore):
    """
    PostgreSQL vector store using the pgvector extension (ADR 001).
    Falls back gracefully to InMemoryVectorStore when DB is offline, pgvector is uninstalled, or in lightweight mode.
    """

    _pgvector_available: bool | None = None

    def __init__(self, expected_dim: int = 768, expected_model: str = "gemini-embedding-2"):
        self.expected_dim = expected_dim
        self.expected_model = expected_model
        self._fallback = get_shared_in_memory_store(expected_dim, expected_model)

    async def add_vectors(self, records: list[VectorRecord]) -> None:
        # Update fallback store
        await self._fallback.add_vectors(records)

    async def search(
        self,
        query_vector: list[float],
        top_k: int = 5,
        filters: dict[str, Any] | None = None,
        query_model_name: str | None = None,
    ) -> list[RetrievalResult]:
        # Enforce Rule 8 validation before querying
        if len(query_vector) != self.expected_dim:
            raise ValueError(
                f"Query refused: vector dimension mismatch. Expected {self.expected_dim}, received {len(query_vector)}."
            )
        if query_model_name and query_model_name != self.expected_model:
            raise ValueError(
                f"Query refused: model mismatch. Expected '{self.expected_model}', received '{query_model_name}'."
            )

        # Try executing in PostgreSQL if available, otherwise use in-memory store
        if PgVectorStore._pgvector_available is not False:
            try:
                async with async_session_factory() as session:
                    # Query table reference_clauses with pgvector cosine distance operator <=>
                    filter_clause = ""
                    params: dict[str, Any] = {"q_vec": str(query_vector), "limit": top_k}
                    if filters and "category" in filters and filters["category"]:
                        filter_clause = "WHERE category = :cat"
                        params["cat"] = filters["category"]

                    sql = f"""
                        SELECT id, title, category, document_type, text, why_standard_or_risky,
                               1 - (embedding <=> :q_vec::vector) as similarity
                        FROM reference_clauses
                        {filter_clause}
                        ORDER BY embedding <=> :q_vec::vector
                        LIMIT :limit
                    """
                    res = await session.execute(text(sql), params)
                    rows = res.fetchall()
                    if rows:
                        PgVectorStore._pgvector_available = True
                        return [
                            RetrievalResult(
                                id=row[0],
                                score=round(float(row[6]), 4),
                                metadata={
                                    "title": row[1],
                                    "category": row[2],
                                    "document_type": row[3],
                                    "text": row[4],
                                    "why_standard_or_risky": row[5],
                                },
                            )
                            for row in rows
                        ]
            except Exception as exc:
                if PgVectorStore._pgvector_available is None:
                    logger.warning(
                        "pgvector_unavailable_falling_back_to_in_memory",
                        reason=str(exc)[:150],
                    )
                PgVectorStore._pgvector_available = False

        return await self._fallback.search(
            query_vector,
            top_k=top_k,
            filters=filters,
            query_model_name=query_model_name,
        )

    async def delete_vectors(self, ids: list[str]) -> None:
        await self._fallback.delete_vectors(ids)


def get_vector_store(store_type: str | None = None) -> VectorStore:
    """Factory to construct the configured vector store."""
    settings = get_settings()
    st = store_type or settings.vector_store_type
    dim = settings.embedding_dimension
    model = settings.gemini_embedding_model

    if st == "pgvector":
        return PgVectorStore(expected_dim=dim, expected_model=model)
    return get_shared_in_memory_store(expected_dim=dim, expected_model=model)
