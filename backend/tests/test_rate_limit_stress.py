"""
Simulated-429 Stress Test: 20 Concurrent Documents.

Pass Criteria:
- Zero failed jobs across all 20 concurrent documents.
- Zero unhandled 429 / RESOURCE_EXHAUSTED exceptions.
- All documents complete successfully.
- Pacing, batching, caching, and backoff with jitter prevent quota failure.
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
import tenacity

# Ensure backend root is on sys.path for standalone IDE runner / static analyzer
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.ai.embedding import GeminiEmbedder
from app.ai.llm import GeminiLLMClient
from app.ai.pipeline import RiskAnalysisPipeline
from app.ai.rate_limiter import SharedModelRateLimiter
from app.ai.vector_store import InMemoryVectorStore


@pytest.mark.asyncio
async def test_20_concurrent_documents_stress_with_simulated_429():
    """
    Simulate 20 concurrent documents under intense 429 rate-limit injection.
    Pass only if all 20 documents succeed with zero unhandled 429s and zero failed jobs.
    """
    total_docs = 20
    clauses_per_doc = 3

    # Set up fast test limiters against a simulated 100 RPM limit
    embed_limiter = SharedModelRateLimiter(model_name="stress-embed-100", max_rpm=100, min_interval=0.0)
    llm_limiter = SharedModelRateLimiter(model_name="stress-llm-100", max_rpm=100, min_interval=0.0)

    # Set up pipeline with in-memory vector store
    embedder = GeminiEmbedder(force_offline=False)
    embedder._offline_mode = False
    embedder._dimension = 768
    embedder._rate_limiter = embed_limiter
    embedder._throttle = embed_limiter
    # Configure instant retry wait for stress test
    if hasattr(embedder._call_api_batch, "retry"):
        embedder._call_api_batch.retry.wait = tenacity.wait_none()

    vector_store = InMemoryVectorStore(expected_dim=768, expected_model=embedder.model_name)
    llm_client = GeminiLLMClient(force_offline=False)
    llm_client._force_offline = False
    llm_client._rate_limiter = llm_limiter

    pipeline = RiskAnalysisPipeline(
        llm_client=llm_client,
        embedder=embedder,
        vector_store=vector_store,
    )

    # 429 Injection counters
    embedding_call_count = 0
    embedding_429_count = 0
    llm_call_count = 0
    llm_429_count = 0

    # Mock embed_content to simulate 429s on every other call
    async def mock_embed_content(*args, **kwargs):
        nonlocal embedding_call_count, embedding_429_count
        embedding_call_count += 1
        if embedding_call_count % 3 == 1:
            embedding_429_count += 1
            raise Exception("429 RESOURCE_EXHAUSTED: Embed content requests per minute limit exceeded. Please retry in 0.05s.")

        resp = MagicMock()
        contents = kwargs.get("contents") or (args[1] if len(args) > 1 else ["test"])
        resp.embeddings = [MagicMock(values=[0.1] * 768) for _ in range(len(contents))]
        return resp

    # Mock generate_content to simulate 429s on every other call
    async def mock_generate_content(*args, **kwargs):
        nonlocal llm_call_count, llm_429_count
        llm_call_count += 1
        if llm_call_count % 3 == 1:
            llm_429_count += 1
            raise Exception("429 RESOURCE_EXHAUSTED: Generate content requests per minute limit exceeded. Please retry in 0.05s.")

        resp = MagicMock()
        contents = str(kwargs.get("contents", ""))
        if "CLAUSE-LEVEL FINDINGS" in contents or "Synthesize" in contents or "executive summary" in contents.lower():
            resp.text = json.dumps({
                "overall_risk_score": 30,
                "overall_risk_level": "MEDIUM",
                "overall_summary": "Standard agreement with minor concerns.",
                "executive_summary": "Standard agreement with minor concerns.",
                "key_risks": ["Review liability limit."],
                "category_breakdown": {"liability": 1},
                "negotiation_priorities": [],
                "disclaimer": "Legal disclaimer text.",
            })
        else:
            resp.text = json.dumps({
                "risk_level": "LOW",
                "risk_score": 15,
                "confidence": 0.95,
                "plain_english": "Standard mutual clause.",
                "risk_reasons": ['Standard clause quoting "mutual indemnification".'],
                "missing_protections": [],
                "suggested_rewrite": None,
                "legal_review_note": None,
            })
        return resp

    mock_client = MagicMock()
    mock_client.aio.models.embed_content = AsyncMock(side_effect=mock_embed_content)
    mock_client.aio.models.generate_content = AsyncMock(side_effect=mock_generate_content)

    embedder._client = mock_client
    llm_client._client = mock_client

    # Concurrent document simulation task
    async def process_simulated_document(doc_idx: int) -> dict[str, Any]:
        doc_id = str(uuid4())
        clause_texts = [
            f"Doc {doc_idx} Clause {c_idx}: Each party shall defend and indemnify the other party against claims."
            for c_idx in range(clauses_per_doc)
        ]

        # 1. Batch-embed all clauses up front (reused for storage & retrieval)
        vectors = await embedder.embed_texts(clause_texts)

        # 2. Analyze clauses concurrently or sequentially within the document
        clause_results = []
        for c_idx, c_text in enumerate(clause_texts):
            res = await pipeline.analyze_clause(
                clause_text=c_text,
                document_type="Service Agreement",
                clause_vector=vectors[c_idx],
            )
            clause_results.append(res)

        # 3. Document summary
        summary = await pipeline.generate_document_summary(
            document_type="Service Agreement",
            clause_analyses=clause_results,
        )

        return {
            "doc_id": doc_id,
            "status": "completed",
            "clauses_count": len(clause_results),
            "summary_score": summary["overall_risk_score"],
        }

    # Execute all 20 documents concurrently under 429 stress
    with patch("app.ai.llm.calculate_jittered_backoff", return_value=0.01), patch(
        "tenacity.wait_exponential.__call__", return_value=0.01
    ):
        results = await asyncio.gather(*[
            process_simulated_document(i) for i in range(total_docs)
        ], return_exceptions=True)

    # ─────────────────────────────────────────────────────────────────────────
    # Verification & Assertions
    # ─────────────────────────────────────────────────────────────────────────
    failed_jobs = []
    unhandled_429s = []
    completed_jobs = []

    for r in results:
        if isinstance(r, Exception):
            failed_jobs.append(r)
            if "429" in str(r) or "RESOURCE_EXHAUSTED" in str(r):
                unhandled_429s.append(r)
        elif isinstance(r, dict) and r.get("status") == "completed":
            completed_jobs.append(r)
        else:
            failed_jobs.append(r)

    # Criteria 1: Zero unhandled 429s
    assert len(unhandled_429s) == 0, f"Found unhandled 429 errors: {unhandled_429s}"

    # Criteria 2: Zero failed jobs
    assert len(failed_jobs) == 0, f"Found failed jobs: {failed_jobs}"

    # Criteria 3: All 20 documents completed successfully
    assert len(completed_jobs) == 20
    for doc in completed_jobs:
        assert doc["clauses_count"] == clauses_per_doc

    # Criteria 4: Confirm 429s were actually injected and survived
    assert embedding_429_count > 0, "Stress test must trigger simulated 429 embedding errors"
    assert llm_429_count > 0, "Stress test must trigger simulated 429 LLM errors"
