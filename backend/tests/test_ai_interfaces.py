"""
Unit tests for AI interface definitions and Fake test doubles.
"""

import pytest
from pydantic import BaseModel

from app.ai.interfaces import (
    FakeEmbedder,
    FakeLLMClient,
    FakeVectorStore,
    VectorRecord,
)


class MockAnalysisResult(BaseModel):
    summary: str
    risk_level: str
    score: int


@pytest.mark.asyncio
async def test_fake_embedder_determinism():
    """Verify FakeEmbedder generates deterministic normalized vectors of expected dimension."""
    embedder = FakeEmbedder(model_name="gemini-embedding-2", dimension=768)
    assert embedder.model_name == "gemini-embedding-2"
    assert embedder.dimension == 768

    texts = ["Clause 1: Limitation of liability", "Clause 2: Governing law"]
    vectors = await embedder.embed_texts(texts)

    assert len(vectors) == 2
    assert len(vectors[0]) == 768
    assert len(vectors[1]) == 768
    assert embedder.call_count == 1

    # Identical text must produce identical vector
    v1_repeat = await embedder.embed_query("Clause 1: Limitation of liability")
    assert vectors[0] == v1_repeat


@pytest.mark.asyncio
async def test_fake_llm_structured_output():
    """Verify FakeLLMClient generates valid structured output conforming to response schema."""
    canned = MockAnalysisResult(
        summary="Capped liability at 12 months fees.",
        risk_level="LOW",
        score=20,
    )
    llm = FakeLLMClient(model_name="gemini-3.5-flash-lite", canned_response=canned)
    assert llm.model_name == "gemini-3.5-flash-lite"

    result = await llm.generate_structured(
        prompt="Analyze this clause",
        response_model=MockAnalysisResult,
        system_instruction="You are a legal assistant",
    )

    assert result.risk_level == "LOW"
    assert result.score == 20
    assert len(llm.prompts_received) == 1
    assert llm.system_instructions_received[0] == "You are a legal assistant"


@pytest.mark.asyncio
async def test_fake_vector_store_workflow():
    """Verify FakeVectorStore validates dimensions, persists records, and calculates cosine similarity."""
    store = FakeVectorStore(expected_dim=4, expected_model="gemini-embedding-2")

    # Mismatched dimension must raise error
    with pytest.raises(ValueError, match="Dimension mismatch"):
        await store.add_vectors(
            [
                VectorRecord(
                    id="bad_dim",
                    vector=[0.1, 0.2],  # only 2 dimensions
                    dimension=2,
                )
            ]
        )

    # Add valid records
    records = [
        VectorRecord(
            id="r1", vector=[1.0, 0.0, 0.0, 0.0], dimension=4, metadata={"cat": "liability"}
        ),
        VectorRecord(
            id="r2", vector=[0.0, 1.0, 0.0, 0.0], dimension=4, metadata={"cat": "privacy"}
        ),
        VectorRecord(
            id="r3", vector=[0.7071, 0.7071, 0.0, 0.0], dimension=4, metadata={"cat": "liability"}
        ),
    ]
    await store.add_vectors(records)

    # Search with query close to r1
    results = await store.search(query_vector=[1.0, 0.0, 0.0, 0.0], top_k=2)
    assert len(results) == 2
    assert results[0].id == "r1"
    assert results[0].score == 1.0
    assert results[1].id == "r3"

    # Search with metadata filter
    filtered = await store.search(
        query_vector=[1.0, 0.0, 0.0, 0.0],
        top_k=5,
        filters={"cat": "privacy"},
    )
    assert len(filtered) == 1
    assert filtered[0].id == "r2"

    # Delete
    await store.delete_vectors(["r1"])
    after_del = await store.search(query_vector=[1.0, 0.0, 0.0, 0.0], top_k=2)
    assert all(r.id != "r1" for r in after_del)
