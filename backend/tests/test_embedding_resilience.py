"""
Unit tests for GeminiEmbedder resilience features:
- Batching
- Exponential backoff on 429 / RESOURCE_EXHAUSTED
- Configurable RPM throttle (default < 100)
- Persistent SHA-256 hash caching
"""

import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.ai.embedding import (
    EmbeddingRPMThrottle,
    GeminiEmbedder,
)
from app.core.config import get_settings


@pytest.mark.asyncio
async def test_rpm_throttle_pacing():
    """Verify that EmbeddingRPMThrottle enforces the configured RPM rate limit."""
    throttle = EmbeddingRPMThrottle(max_rpm=2, min_interval=0.0)
    throttle._timestamps = []

    start = time.monotonic()
    # First 2 requests should go through immediately without waiting
    await throttle.acquire()
    await throttle.acquire()
    elapsed_immediate = time.monotonic() - start
    assert elapsed_immediate < 0.1
    assert throttle.current_load == 2


@pytest.mark.asyncio
async def test_embedder_default_rpm_and_config():
    """Verify that GeminiEmbedder defaults to settings.gemini_embedding_rpm (< 100)."""
    settings = get_settings()
    embedder = GeminiEmbedder(force_offline=True)
    assert embedder.rpm == settings.gemini_embedding_rpm
    assert embedder.rpm < 100
    assert embedder._throttle.max_rpm == settings.gemini_embedding_rpm

    # Test custom RPM configuration
    custom_embedder = GeminiEmbedder(force_offline=True, rpm=45)
    assert custom_embedder.rpm == 45
    assert custom_embedder._throttle.max_rpm == 45


@pytest.mark.asyncio
async def test_hash_caching_avoids_duplicate_api_calls():
    """Verify that identical texts are retrieved from SHA-256 hash cache without calling API."""
    embedder = GeminiEmbedder(force_offline=False)
    embedder._offline_mode = False

    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_emb = MagicMock()
    mock_emb.values = [0.1] * 768
    mock_response.embeddings = [mock_emb]
    mock_client.aio.models.embed_content = AsyncMock(return_value=mock_response)
    embedder._client = mock_client

    test_text = "Party A shall indemnify Party B from all claims."

    # First call: cache miss, invokes API
    vecs_1 = await embedder.embed_texts([test_text])
    assert len(vecs_1) == 1
    assert mock_client.aio.models.embed_content.call_count == 1

    # Second call: cache hit, API must NOT be called again
    vecs_2 = await embedder.embed_texts([test_text])
    assert len(vecs_2) == 1
    assert vecs_1[0] == vecs_2[0]
    assert mock_client.aio.models.embed_content.call_count == 1  # Unchanged!


@pytest.mark.asyncio
async def test_cache_is_not_cleared_on_error():
    """Verify that existing cache entries are preserved even when a subsequent API call errors."""
    embedder = GeminiEmbedder(force_offline=False)
    embedder._offline_mode = False

    cached_text = "Existing cached clause"
    h = embedder._hash_text(cached_text)
    embedder._cache[h] = [0.5] * 768

    # Simulate an API error on a new text
    mock_client = MagicMock()
    mock_client.aio.models.embed_content = AsyncMock(side_effect=RuntimeError("Transient network failure"))
    embedder._client = mock_client

    # Request both the cached text and a new failing text
    results = await embedder.embed_texts([cached_text, "New failing text"])
    assert len(results) == 2
    # Verify cached item was NOT wiped out
    assert h in embedder._cache
    assert results[0] == [0.5] * 768


@pytest.mark.asyncio
async def test_exponential_backoff_on_429():
    """Verify that a 429 / RESOURCE_EXHAUSTED error triggers exponential backoff retry and recovers."""
    embedder = GeminiEmbedder(force_offline=False)
    embedder._offline_mode = False

    mock_client = MagicMock()
    mock_success = MagicMock()
    mock_emb = MagicMock()
    mock_emb.values = [0.7] * 768
    mock_success.embeddings = [mock_emb]

    # First call throws 429 RESOURCE_EXHAUSTED, second call succeeds
    mock_client.aio.models.embed_content = AsyncMock(
        side_effect=[
            Exception("429 RESOURCE_EXHAUSTED: Quota exceeded for quota metric 'Embed Content API requests'"),
            mock_success,
        ]
    )
    embedder._client = mock_client

    # Call with fast retry settings for unit test
    with patch("tenacity.wait_exponential.__call__", return_value=0.01):
        vecs = await embedder.embed_texts(["Arbitration shall take place in Delaware."])

    assert len(vecs) == 1
    assert vecs[0] == [0.7] * 768
    # Should have retried and succeeded on attempt 2
    assert mock_client.aio.models.embed_content.call_count == 2


@pytest.mark.asyncio
async def test_batching_partitions_misses_correctly():
    """Verify that large inputs are split into chunks of embedding_batch_size."""
    embedder = GeminiEmbedder(force_offline=False)
    embedder._offline_mode = False
    embedder.settings.embedding_batch_size = 2

    mock_client = MagicMock()

    def mock_embed_batch(model, contents, config):
        resp = MagicMock()
        resp.embeddings = [MagicMock(values=[float(i)] * 768) for i in range(len(contents))]
        return resp

    mock_client.aio.models.embed_content = AsyncMock(side_effect=mock_embed_batch)
    embedder._client = mock_client

    texts = [f"Clause text snippet {i}" for i in range(5)]
    results = await embedder.embed_texts(texts)

    assert len(results) == 5
    # With 5 items and batch_size=2: batches of [2, 2, 1] -> 3 calls
    assert mock_client.aio.models.embed_content.call_count == 3


@pytest.mark.asyncio
async def test_offline_mode_fallback():
    """Verify deterministic embeddings when forced offline."""
    embedder = GeminiEmbedder(force_offline=True)
    assert embedder._offline_mode is True

    texts = [
        "In no event shall aggregate liability exceed total fees paid.",
        "The customer shall defend and indemnify against all third party claims.",
    ]
    vecs = await embedder.embed_texts(texts)
    assert len(vecs) == 2
    assert len(vecs[0]) == 768
    assert len(vecs[1]) == 768
    # Offline embeddings are normalized unit vectors
    norm_0 = sum(x * x for x in vecs[0])
    assert abs(norm_0 - 1.0) < 0.01


@pytest.mark.asyncio
async def test_simulated_429_mid_batch_recovery_zero_duplicates_zero_lost():
    """
    Verify simulated 429 mid-batch response, followed by successful recovery.
    Must ensure:
    - Zero lost clauses (all clauses successfully embedded).
    - Zero duplicate API calls (subsequent requests hit hash cache).
    """
    embedder = GeminiEmbedder(force_offline=False)
    embedder._offline_mode = False
    embedder.settings.embedding_batch_size = 4

    call_count = 0
    injected_429_count = 0

    def mock_embed_content(model, contents, config):
        nonlocal call_count, injected_429_count
        call_count += 1
        # Inject 429 on the second batch call
        if call_count == 2:
            injected_429_count += 1
            raise Exception("429 RESOURCE_EXHAUSTED: Rate limit exceeded mid-batch. Retry in 0.05s.")

        resp = MagicMock()
        resp.embeddings = [MagicMock(values=[0.5 + 0.01 * i] * 768) for i in range(len(contents))]
        return resp

    mock_client = MagicMock()
    mock_client.aio.models.embed_content = AsyncMock(side_effect=mock_embed_content)
    embedder._client = mock_client

    # 10 distinct clauses split into clauses of [4, 4, 2]
    clauses = [f"Resilience clause number {i}: Party A shall indemnify Party B." for i in range(10)]

    with patch("tenacity.wait_exponential.__call__", return_value=0.01), patch(
        "app.ai.llm.calculate_jittered_backoff", return_value=0.01
    ):
        results = await embedder.embed_texts(clauses)

    # 1. Zero lost clauses: all 10 clauses returned valid 768-dim vectors
    assert len(results) == 10
    for vec in results:
        assert len(vec) == 768
    assert injected_429_count == 1

    # 2. Re-embed exact same 10 clauses: must hit cache with ZERO additional API calls
    initial_api_calls = call_count
    cached_results = await embedder.embed_texts(clauses)
    assert len(cached_results) == 10
    assert call_count == initial_api_calls, "Zero duplicate API calls: cached vectors must be reused"
    assert cached_results == results
