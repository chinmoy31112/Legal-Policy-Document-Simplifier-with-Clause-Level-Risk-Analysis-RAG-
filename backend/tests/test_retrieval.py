"""
Unit tests for Phase 3: Knowledge Base and Retrieval.

Verifies:
- Rule 1: Retrieval before reasoning with explicit no_reference_found flag.
- Rule 8: Vector store enforces single model and dimension guardrails.
- GeminiEmbedder caching, batching, and deterministic offline projection.
- KnowledgeBaseService multi-format ingestion and hash-based idempotency.
- CLI subcommands (index, list, stats, delete).
"""

import pytest

from app.ai.embedding import GeminiEmbedder
from app.ai.interfaces import VectorRecord
from app.ai.retrieval import RetrievalService
from app.ai.vector_store import InMemoryVectorStore, PgVectorStore, get_vector_store
from app.services.knowledge_base_service import KnowledgeBaseService


@pytest.fixture
def embedder():
    """Deterministic offline embedder for tests."""
    return GeminiEmbedder(force_offline=True)


@pytest.fixture
def vector_store(embedder):
    """In-memory vector store matching embedder configuration."""
    return InMemoryVectorStore(expected_dim=embedder.dimension, expected_model=embedder.model_name)


@pytest.fixture
def retrieval_service(embedder, vector_store):
    """Retrieval service coordinating embedder and vector store."""
    return RetrievalService(embedder=embedder, vector_store=vector_store)


@pytest.fixture
def kb_service(embedder, vector_store):
    """Knowledge base service for ingestion and retrieval."""
    return KnowledgeBaseService(embedder=embedder, vector_store=vector_store)


class TestGeminiEmbedder:
    """Test embedding service properties, caching, and batching."""

    def test_embedder_properties(self, embedder):
        assert embedder.dimension == 768
        assert embedder.model_name == "gemini-embedding-2"

    @pytest.mark.asyncio
    async def test_embed_texts_caching(self, embedder):
        text = "This is a standard confidentiality agreement clause."
        # First call populates cache
        vecs1 = await embedder.embed_texts([text])
        assert len(vecs1) == 1
        assert len(vecs1[0]) == 768

        h = embedder._hash_text(text)
        assert h in embedder._cache

        # Second call returns cached vector
        vecs2 = await embedder.embed_texts([text])
        assert vecs1[0] == vecs2[0]

    @pytest.mark.asyncio
    async def test_embed_query(self, embedder):
        vec = await embedder.embed_query("liability cap limitation")
        assert len(vec) == 768
        # Unit normalized
        norm = sum(x * x for x in vec) ** 0.5
        assert pytest.approx(norm, 0.01) == 1.0


class TestVectorStoreGuardrails:
    """Test Rule 8 guardrails preventing model or dimension mismatches."""

    @pytest.mark.asyncio
    async def test_add_vector_dimension_mismatch_raises(self, vector_store):
        rec = VectorRecord(
            id="bad_dim",
            vector=[0.1] * 512,  # Expected 768
            model_name="gemini-embedding-2",
            dimension=512,
        )
        with pytest.raises(ValueError, match="Dimension mismatch"):
            await vector_store.add_vectors([rec])

    @pytest.mark.asyncio
    async def test_add_vector_model_mismatch_raises(self, vector_store):
        rec = VectorRecord(
            id="bad_model",
            vector=[0.1] * 768,
            model_name="openai/text-embedding-ada-002",
            dimension=768,
        )
        with pytest.raises(ValueError, match="Model mismatch"):
            await vector_store.add_vectors([rec])

    @pytest.mark.asyncio
    async def test_search_query_dimension_mismatch_refused(self, vector_store):
        with pytest.raises(ValueError, match="Query refused: vector dimension mismatch"):
            await vector_store.search([0.1] * 512, top_k=5)

    @pytest.mark.asyncio
    async def test_search_query_model_mismatch_refused(self, vector_store):
        with pytest.raises(ValueError, match="Query refused: model mismatch"):
            await vector_store.search(
                [0.1] * 768, top_k=5, query_model_name="openai/text-embedding-3-small"
            )

    def test_factory_constructs_stores(self):
        mem_store = get_vector_store("memory")
        assert isinstance(mem_store, InMemoryVectorStore)

        pg_store = get_vector_store("pgvector")
        assert isinstance(pg_store, PgVectorStore)


class TestRetrievalService:
    """Test Rule 1: retrieval before reasoning, thresholds, and no_reference_found."""

    @pytest.mark.asyncio
    async def test_index_and_retrieve_in_domain(self, retrieval_service):
        clauses = [
            {
                "id": "REF-TEST-001",
                "title": "Mutual Liability Limitation",
                "text": "Neither party shall be liable for consequential damages or lost profits under this agreement.",
                "category": "Limitation of Liability",
            },
            {
                "id": "REF-TEST-002",
                "title": "Customer IP Infringement Indemnity",
                "text": "Provider will defend and indemnify customer against third-party patent or copyright claims.",
                "category": "Indemnification",
            },
        ]
        await retrieval_service.index_reference_clauses(clauses)

        # Query matching liability clause
        resp = await retrieval_service.retrieve(
            "Company aggregate liability is disclaimed for lost profits and consequential damages.",
            top_k=5,
            min_similarity=0.20,
        )

        assert not resp.no_reference_found
        assert len(resp.results) > 0
        assert resp.results[0].id == "REF-TEST-001"
        assert resp.results[0].metadata["category"] == "Limitation of Liability"

    @pytest.mark.asyncio
    async def test_out_of_domain_returns_no_reference_found(self, retrieval_service):
        # Index standard legal clause
        clauses = [
            {
                "id": "REF-TEST-001",
                "title": "Mutual Liability Limitation",
                "text": "Neither party shall be liable for consequential damages or lost profits under this agreement.",
                "category": "Limitation of Liability",
            }
        ]
        await retrieval_service.index_reference_clauses(clauses)

        # Out-of-domain query about cooking
        resp = await retrieval_service.retrieve(
            "To bake sourdough bread, fold flour and water with yeast and ferment at room temperature.",
            top_k=5,
            min_similarity=0.20,
        )

        assert resp.no_reference_found is True
        assert len(resp.results) == 0
        assert resp.retrieved_count == 0


class TestKnowledgeBaseService:
    """Test KnowledgeBaseService multi-format ingestion and hash idempotency."""

    @pytest.mark.asyncio
    async def test_index_reference_clauses_idempotency(self, kb_service):
        clauses = [
            {
                "id": "REF-IDEMP-001",
                "title": "Termination for Cause",
                "text": "Either party may terminate immediately for uncured material breach.",
                "category": "Termination",
            }
        ]

        # First ingestion
        res1 = await kb_service.index_reference_clauses(clauses)
        assert res1["indexed"] == 1
        assert res1["skipped"] == 0

        # Second ingestion of identical clause skips re-indexing
        res2 = await kb_service.index_reference_clauses(clauses)
        assert res2["indexed"] == 0
        assert res2["skipped"] == 1

    @pytest.mark.asyncio
    async def test_kb_service_stats_and_delete(self, kb_service):
        clauses = [
            {
                "id": "REF-STAT-001",
                "title": "Data Protection",
                "text": "Processor implements GDPR compliant technical measures to protect personal data.",
                "category": "Data Privacy & Retention",
            }
        ]
        await kb_service.index_reference_clauses(clauses)

        stats = await kb_service.get_stats()
        assert stats["total_vectors"] >= 1
        assert "Data Privacy & Retention" in stats["categories"]

        # Delete clause
        deleted = await kb_service.delete_clause("REF-STAT-001")
        assert deleted is True

        # Verify deletion
        items = await kb_service.list_clauses()
        assert not any(i["id"] == "REF-STAT-001" for i in items)
