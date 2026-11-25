"""
AI Interface Abstractions & Test Doubles.

Strictly follows Phase 1 requirements:
- Provides abstract contracts for Embedder, LLMClient, and VectorStore.
- Provides robust, deterministic Fake implementations for unit tests and local evaluation.
- Prevents coupling of domain logic to specific cloud or vendor SDK implementations.
"""

import hashlib
import math
from abc import ABC, abstractmethod
from typing import Any, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T", bound=BaseModel)


# ── Data Transfer Objects (DTOs) ──────────────────────────────────────────────


class VectorRecord(BaseModel):
    """Represents a vector record to be persisted in a vector store."""

    id: str
    vector: list[float]
    metadata: dict[str, Any] = Field(default_factory=dict)
    model_name: str = "gemini-embedding-2"
    dimension: int = 768


class RetrievalResult(BaseModel):
    """Result returned from a vector similarity search."""

    id: str
    score: float
    metadata: dict[str, Any] = Field(default_factory=dict)


# ── Embedder Interface & Fake ─────────────────────────────────────────────────


class Embedder(ABC):
    """Abstract interface for text embedding generation."""

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Name of the embedding model."""
        pass

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Dimensionality of produced vectors."""
        pass

    @abstractmethod
    async def embed_texts(
        self, texts: list[str], task_type: str = "RETRIEVAL_DOCUMENT"
    ) -> list[list[float]]:
        """Generate dense vector embeddings for a batch of texts."""
        pass

    @abstractmethod
    async def embed_query(self, text: str) -> list[float]:
        """Generate a dense vector embedding for a single search query."""
        pass


class FakeEmbedder(Embedder):
    """Deterministic, offline Embedder implementation for testing."""

    def __init__(self, model_name: str = "gemini-embedding-2", dimension: int = 768):
        self._model_name = model_name
        self._dimension = dimension
        self.call_count: int = 0
        self.embedded_texts_history: list[str] = []

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def dimension(self) -> int:
        return self._dimension

    def _generate_deterministic_vector(self, text: str) -> list[float]:
        """Generate a deterministic unit-normalized vector from text hash."""
        hash_bytes = hashlib.sha256(text.encode("utf-8")).digest()
        # Seed pseudo vector from hash bytes
        raw_vals: list[float] = []
        for i in range(self._dimension):
            byte_val = hash_bytes[i % len(hash_bytes)]
            val = ((byte_val + i * 17) % 256) / 128.0 - 1.0
            raw_vals.append(val)

        norm = math.sqrt(sum(v * v for v in raw_vals)) or 1.0
        return [round(v / norm, 6) for v in raw_vals]

    async def embed_texts(
        self, texts: list[str], task_type: str = "RETRIEVAL_DOCUMENT"
    ) -> list[list[float]]:
        self.call_count += 1
        self.embedded_texts_history.extend(texts)
        return [self._generate_deterministic_vector(t) for t in texts]

    async def embed_query(self, text: str) -> list[float]:
        self.call_count += 1
        self.embedded_texts_history.append(text)
        return self._generate_deterministic_vector(text)


# ── LLM Client Interface & Fake ───────────────────────────────────────────────


class LLMClient(ABC):
    """Abstract interface for structured reasoning models."""

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Identifier of the reasoning model."""
        pass

    @abstractmethod
    async def generate_structured(
        self,
        prompt: str,
        response_model: type[T],
        system_instruction: str | None = None,
    ) -> T:
        """Generate a response strictly validated against a Pydantic schema."""
        pass

    @abstractmethod
    async def generate_text(
        self,
        prompt: str,
        system_instruction: str | None = None,
    ) -> str:
        """Generate freeform textual response."""
        pass


class FakeLLMClient(LLMClient):
    """Deterministic, offline LLM client for tests and evaluation."""

    def __init__(
        self,
        model_name: str = "gemini-3.5-flash-lite",
        canned_response: Any | None = None,
        canned_text: str = "Fake LLM Text Response",
    ):
        self._model_name = model_name
        self.canned_response = canned_response
        self.canned_text = canned_text
        self.prompts_received: list[str] = []
        self.system_instructions_received: list[str | None] = []

    @property
    def model_name(self) -> str:
        return self._model_name

    async def generate_structured(
        self,
        prompt: str,
        response_model: type[T],
        system_instruction: str | None = None,
    ) -> T:
        self.prompts_received.append(prompt)
        self.system_instructions_received.append(system_instruction)

        if isinstance(self.canned_response, response_model):
            return self.canned_response
        if isinstance(self.canned_response, dict):
            return response_model.model_validate(self.canned_response)

        # Default fallback: construct a minimal instance
        try:
            return response_model()  # type: ignore
        except Exception:
            # Construct empty fields
            fields = {k: "sample" for k in response_model.model_fields.keys()}
            return response_model.model_validate(fields)

    async def generate_text(
        self,
        prompt: str,
        system_instruction: str | None = None,
    ) -> str:
        self.prompts_received.append(prompt)
        self.system_instructions_received.append(system_instruction)
        return self.canned_text


# ── Vector Store Interface & Fake ─────────────────────────────────────────────


class VectorStore(ABC):
    """Abstract interface for vector similarity search engines."""

    @abstractmethod
    async def add_vectors(self, records: list[VectorRecord]) -> None:
        """Store dense vector records with associated metadata."""
        pass

    @abstractmethod
    async def search(
        self,
        query_vector: list[float],
        top_k: int = 5,
        filters: dict[str, Any] | None = None,
        query_model_name: str | None = None,
    ) -> list[RetrievalResult]:
        """Retrieve the top-K most similar records to a query vector."""
        pass

    @abstractmethod
    async def delete_vectors(self, ids: list[str]) -> None:
        """Delete vector records by their unique IDs."""
        pass


class FakeVectorStore(VectorStore):
    """In-memory, exact-cosine-similarity VectorStore for tests."""

    def __init__(self, expected_dim: int = 768, expected_model: str = "gemini-embedding-2"):
        self.expected_dim = expected_dim
        self.expected_model = expected_model
        self._store: dict[str, VectorRecord] = {}

    async def add_vectors(self, records: list[VectorRecord]) -> None:
        for rec in records:
            if rec.dimension != self.expected_dim:
                raise ValueError(
                    f"Dimension mismatch: expected {self.expected_dim}, got {rec.dimension}"
                )
            if rec.model_name != self.expected_model:
                raise ValueError(
                    f"Model mismatch: expected {self.expected_model}, got {rec.model_name}"
                )
            self._store[rec.id] = rec

    async def search(
        self,
        query_vector: list[float],
        top_k: int = 5,
        filters: dict[str, Any] | None = None,
        query_model_name: str | None = None,
    ) -> list[RetrievalResult]:
        if len(query_vector) != self.expected_dim:
            raise ValueError(
                f"Query vector dimension {len(query_vector)} does not match expected {self.expected_dim}"
            )

        results: list[tuple[float, VectorRecord]] = []
        for rec in self._store.values():
            # Check metadata filter matching
            if filters:
                match = all(rec.metadata.get(k) == v for k, v in filters.items())
                if not match:
                    continue

            # Compute cosine similarity
            dot_product = sum(a * b for a, b in zip(query_vector, rec.vector))
            norm_a = math.sqrt(sum(a * a for a in query_vector)) or 1.0
            norm_b = math.sqrt(sum(b * b for b in rec.vector)) or 1.0
            similarity = dot_product / (norm_a * norm_b)
            results.append((similarity, rec))

        # Sort descending by similarity score
        results.sort(key=lambda x: x[0], reverse=True)

        return [
            RetrievalResult(
                id=rec.id,
                score=round(score, 4),
                metadata=rec.metadata,
            )
            for score, rec in results[:top_k]
        ]

    async def delete_vectors(self, ids: list[str]) -> None:
        for item_id in ids:
            self._store.pop(item_id, None)
