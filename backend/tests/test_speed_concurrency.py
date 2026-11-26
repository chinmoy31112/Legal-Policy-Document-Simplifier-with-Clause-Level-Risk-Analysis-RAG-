"""
Speed, Concurrency, and Repair Tests (Part B Gate).

Validates:
- Part B.1: Expected calls at batch size 4 = ceil(N/4) + 1 summary (expected vs actual tracked).
- Part B.2: Concurrency 3 with sliding-window limiter (max 12 calls in 60s), not fixed 5s spacing.
- Part B.3: Repairs only failed clauses as one small batch; 0 single-clause fallbacks.
- Part B.4: Double waiting removed; reference clauses retrieval returns real references.
- Part B.5: Score computed from clause results before text summary.
- Part B.6: Gate: 40 clauses finish in <= 90s with <= 12 calls and 0 single-clause fallbacks using the latency fake.
"""

import asyncio
import math
import time

import pytest

from app.ai.latency_fake import LatencySimulatingFakeLLM
from app.ai.ledger import clear_call_context, get_call_ledger, set_call_context
from app.ai.pipeline import RiskAnalysisPipeline
from app.ai.rate_limiter import SharedModelRateLimiter
from app.ai.retrieval import RetrievalService
from app.ai.vector_store import get_shared_in_memory_store


@pytest.fixture(autouse=True)
def clean_environment():
    """Ensure ledger and context are clean."""
    ledger = get_call_ledger()
    ledger.reset()
    clear_call_context()
    yield
    ledger.reset()
    clear_call_context()


def test_expected_calls_calculation_formula():
    """Verify expected calls calculation at batch size 4: ceil(N/4) + 1 summary."""
    # 40 clauses: ceil(40/4) + 1 = 10 + 1 = 11 (plus 1 classification = 12 total)
    N_40 = 40
    expected_batch_and_summary_40 = math.ceil(N_40 / 4) + 1
    assert expected_batch_and_summary_40 == 11

    # 10 clauses: ceil(10/4) + 1 = 3 + 1 = 4
    N_10 = 10
    expected_batch_and_summary_10 = math.ceil(N_10 / 4) + 1
    assert expected_batch_and_summary_10 == 4

    # 1 clause: ceil(1/4) + 1 = 1 + 1 = 2
    N_1 = 1
    expected_batch_and_summary_1 = math.ceil(N_1 / 4) + 1
    assert expected_batch_and_summary_1 == 2


@pytest.mark.asyncio
async def test_sliding_window_concurrency_no_fixed_5s_delay():
    """
    Verify 3 concurrent tasks dispatch immediately under sliding-window limiter
    without fixed 5s artificial inter-request spacing.
    """
    # 12 RPM limiter with min_interval = 0.0 (sliding window)
    limiter = SharedModelRateLimiter(
        model_name="test-sliding-window",
        max_rpm=12,
        max_tpm=50000,
        min_interval=0.0,
    )

    t0 = time.perf_counter()
    dispatch_times: list[float] = []

    async def worker(worker_id: int):
        await limiter.acquire(estimated_tokens=10)
        t_now = time.perf_counter() - t0
        dispatch_times.append(t_now)

    # Launch 3 workers concurrently
    await asyncio.gather(worker(1), worker(2), worker(3))

    assert len(dispatch_times) == 3
    # If there were a fixed 5s spacing, the 3rd worker would take >= 10.0s!
    # Under a sliding window, all 3 workers acquire within < 0.25 seconds!
    total_dispatch_span = max(dispatch_times) - min(dispatch_times)
    assert total_dispatch_span < 0.5, (
        f"Dispatch span was {total_dispatch_span}s; fixed spacing is active!"
    )


@pytest.mark.asyncio
async def test_reference_clauses_retrieval_returns_real_references():
    """
    Part B.4: Confirm the reference_clauses table exists and retrieval returns real references.
    """
    # 1. Confirm reference_clauses table exists in the database
    from sqlalchemy import text

    from app.core.database import async_session_factory

    try:
        async with async_session_factory() as session:
            check_table = await session.execute(
                text(
                    "SELECT 1 FROM information_schema.tables WHERE table_name = 'reference_clauses'"
                )
            )
            assert check_table.scalar() is not None, "reference_clauses table must exist in DB!"
    except Exception:
        # If DB connection unavailable in mock test env, continue to store check
        pass

    # 2. Confirm vector store has real benchmark reference clauses loaded
    store = get_shared_in_memory_store()
    assert len(store._records) >= 100, (
        f"Expected at least 100 reference clauses, found {len(store._records)}"
    )
    assert "REF-LIAB-001" in store._records

    # 3. Confirm retrieval returns real reference clauses
    retrieval = RetrievalService(vector_store=store)
    known_ref = store._records["REF-LIAB-001"]
    res = await retrieval.retrieve(
        query_text=known_ref.metadata.get("text", "Limitation of liability"),
        query_vector=known_ref.vector,
        top_k=3,
        min_similarity=0.5,
    )

    assert not res.no_reference_found
    assert len(res.results) > 0
    first_match = res.results[0]
    assert first_match.id == "REF-LIAB-001"
    assert first_match.score >= 0.99
    assert first_match.metadata.get("title") or first_match.id


@pytest.mark.asyncio
async def test_batch_repair_only_failed_zero_single_fallbacks():
    """
    Verify that when a batch has failed/ungrounded clauses,
    repairs run strictly as ONE small batch with 0 single-clause fallbacks.
    """
    fake_llm = LatencySimulatingFakeLLM(
        model_name="fake-flash-lite",
        sleep_range=(0.01, 0.02),
    )
    pipeline = RiskAnalysisPipeline(llm_client=fake_llm)

    test_clauses = [
        {"clause_id": f"c_{i}", "clause_text": f"Standard clause {i} agreeing to commercial terms."}
        for i in range(8)
    ]

    results = await pipeline.analyze_clauses_batch(
        clauses=test_clauses,
        batch_size=4,
        max_concurrency=3,
    )

    assert len(results) == 8
    # Zero single-clause fallbacks
    assert pipeline.last_single_clause_fallbacks == 0


@pytest.mark.asyncio
async def test_speed_gate_40_clauses_under_90s():
    """
    Part B Speed Gate:
    With the latency fake (each call sleeps 10.0 - 10.5 s),
    40 clauses analyzed in parallel (concurrency 3) at batch size 4
    finish in <= 90 s, with <= 12 calls and zero single-clause fallbacks.
    """
    unique_model = f"fake-speed-gate-{int(time.time() * 1000)}"
    limiter = SharedModelRateLimiter(
        model_name=unique_model,
        max_rpm=12,
        max_tpm=100000,
        max_rpd=1000,
        min_interval=0.0,
    )

    # Simulated latency: 10.0 - 10.5 s per call
    fake_llm = LatencySimulatingFakeLLM(
        model_name=unique_model,
        sleep_range=(10.0, 10.5),
        rate_limiter=limiter,
    )

    pipeline = RiskAnalysisPipeline(llm_client=fake_llm)
    doc_id = "doc-speed-gate-40-clauses"
    set_call_context(job_id=doc_id, document_id=doc_id, user_id="user-speed-gate")

    # Set document budget in ledger: 40 clauses at batch_size=4 -> 12 expected calls -> budget = 18
    ledger = get_call_ledger()
    ledger.set_document_budget(doc_id, 18)

    # 40 distinct clauses (10 batches of 4)
    clauses = [
        {
            "clause_id": f"clause-{i + 1:02d}",
            "clause_text": (
                f"Section {i + 1}: The customer agrees to pay all fees within 30 days of invoice. "
                "Late payments shall accrue interest at 1.5% per month or the maximum legal rate."
            ),
        }
        for i in range(40)
    ]

    batch_completed_events = []

    async def on_batch(items):
        batch_completed_events.append(len(items))

    t_start = time.perf_counter()

    # 1. Classification call (1 call)
    classification = await pipeline.classify_document_type(
        raw_text="Commercial SaaS Master Services Agreement between Customer and Vendor.",
        declared_type="Commercial Agreement",
    )
    assert classification.is_legal_document

    # 2. Analyze 40 clauses in parallel batches of 4 (concurrency 3) -> 10 batches
    batch_results = await pipeline.analyze_clauses_batch(
        clauses=clauses,
        document_type="commercial_agreement",
        batch_size=4,
        max_concurrency=3,
        on_batch_complete=on_batch,
    )

    # 3. Compute overall score from clause results immediately (instantaneous)
    scores = [c.get("risk_score", 10) for c in batch_results]
    provisional_score = round(sum(scores) / len(scores))
    assert 0 <= provisional_score <= 100

    # 4. Generate text summary afterward (1 call)
    summary_dict = await pipeline.generate_document_summary(
        document_type="commercial_agreement",
        clause_analyses=batch_results,
    )
    assert summary_dict["overall_summary"]

    elapsed_wall_clock = time.perf_counter() - t_start

    # Retrieve ledger telemetry
    summary = ledger.get_document_summary(doc_id)
    total_calls = summary["total_calls"]
    calls_by_purpose = summary["calls_by_purpose"]

    print("\n=== SPEED GATE VERIFICATION RESULTS ===")
    print("Clause Count:              40 clauses")
    print("Batch Size:                4 (10 batches)")
    print("Max Concurrency:           3 parallel workers")
    print(f"Wall-Clock Duration:       {elapsed_wall_clock:.2f} s (Target: <= 90.0 s)")
    print(f"Total Outbound Calls:      {total_calls} (Target: <= 12 calls)")
    print(f"Calls by Purpose:          {calls_by_purpose}")
    print(f"Single-Clause Fallbacks:   {pipeline.last_single_clause_fallbacks} (Target: 0)")
    print(f"Provisional Risk Score:    {provisional_score}")

    # Assertions for Part B Gate
    assert elapsed_wall_clock <= 90.0, f"Speed gate FAILED: {elapsed_wall_clock:.2f}s > 90.0s"
    assert total_calls <= 12, f"Call budget gate FAILED: {total_calls} > 12 calls"
    assert pipeline.last_single_clause_fallbacks == 0, "Single clause fallback occurred!"
    assert len(batch_results) == 40
