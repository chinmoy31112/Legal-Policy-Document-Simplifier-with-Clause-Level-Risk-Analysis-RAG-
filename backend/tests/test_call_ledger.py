"""
Unit and Integration Tests for Call Ledger, Budget Enforcement, and Latency-Simulating Fake LLM.

Validates:
- Part A.1: Outbound Gemini request recording with all required fields (time, job_id, document_id,
            user_id, purpose, attempt_number, status, latency, tokens, model_name).
- Part A.2: Post-job summary logging (calls per purpose, retries, repairs, limiter wait time, total time).
- Part A.3: Retries and repairs counted against daily budget and logged.
- Part A.4: Per-document call budget enforcement with fast-fail CallBudgetExceededError.
- Part A.5: CLI tool and admin endpoint showing today's calls by purpose.
- Latency fake: rate-limit obedience and injection of 429, 503, and invalid JSON.
"""

import json
from datetime import UTC, datetime

import pytest
from httpx import ASGITransport, AsyncClient

from app.ai.latency_fake import LatencySimulatingFakeLLM
from app.ai.ledger import (
    CallBudgetExceededError,
    CallLedger,
    CallRecord,
    call_purpose,
    clear_call_context,
    get_call_context,
    get_call_ledger,
    set_call_context,
)
from app.ai.rate_limiter import DailyQuotaExceededError, SharedModelRateLimiter
from app.ai.response_parser import LLMClauseAnalysis
from app.core.exceptions import AIServiceError
from app.main import create_app


@pytest.fixture(autouse=True)
def clean_ledger():
    """Ensure ledger and context are completely clean before and after each test."""
    ledger = get_call_ledger()
    ledger.reset()
    clear_call_context()
    yield
    ledger.reset()
    clear_call_context()


def test_call_record_model_validation():
    """Verify CallRecord schema and required fields."""
    record = CallRecord(
        job_id="job-123",
        document_id="doc-456",
        user_id="user-789",
        purpose="analyze",
        attempt_number=1,
        status="ok",
        latency=1.234,
        tokens=350,
        model_name="gemini-3.5-flash-lite",
    )
    assert record.purpose == "analyze"
    assert record.status == "ok"
    assert record.attempt_number == 1
    assert record.latency == 1.234
    assert record.tokens == 350
    assert record.job_id == "job-123"
    assert record.document_id == "doc-456"
    assert record.user_id == "user-789"
    assert isinstance(record.timestamp, datetime)


def test_call_context_propagation():
    """Verify contextvars propagate tracing metadata across tasks."""
    set_call_context(
        job_id="job-1",
        document_id="doc-1",
        user_id="user-1",
        purpose="classify",
    )
    ctx = get_call_context()
    assert ctx["job_id"] == "job-1"
    assert ctx["document_id"] == "doc-1"
    assert ctx["purpose"] == "classify"

    with call_purpose("repair"):
        inner_ctx = get_call_context()
        assert inner_ctx["purpose"] == "repair"

    outer_ctx = get_call_context()
    assert outer_ctx["purpose"] == "classify"


def test_per_document_call_budget_calculation_and_enforcement():
    """Verify expected call formula and strict 1.5x budget stopping with CallBudgetExceededError."""
    # 40 clauses at batch_size=4: 1 classify + 1 embed + 10 analyze + 1 summary = 13 expected calls
    expected_40 = CallLedger.calculate_expected_calls(40, batch_size=4, embed_batch_size=100)
    assert expected_40 == 13

    # Budget is ceil(13 * 1.5) = 20
    budget_40 = CallLedger.calculate_document_budget(40, multiplier=1.5, batch_size=4)
    assert budget_40 == 20

    # 10 clauses at batch_size=4: 1 classify + 1 embed + 3 analyze + 1 summary = 6 expected calls
    expected_10 = CallLedger.calculate_expected_calls(10, batch_size=4, embed_batch_size=100)
    assert expected_10 == 6
    budget_10 = CallLedger.calculate_document_budget(10, multiplier=1.5, batch_size=4)
    assert budget_10 == 9

    # Enforce budget in ledger
    ledger = get_call_ledger()
    doc_id = "test-doc-budget-123"
    ledger.set_document_budget(doc_id, 3)

    # First 3 calls succeed
    for i in range(3):
        ledger.record_call(document_id=doc_id, purpose="analyze", status="ok", attempt_number=i + 1)

    assert ledger.get_document_calls_count(doc_id) == 3

    # 4th call must raise CallBudgetExceededError immediately
    with pytest.raises(CallBudgetExceededError) as exc_info:
        ledger.record_call(document_id=doc_id, purpose="analyze", status="ok", attempt_number=4)

    err = str(exc_info.value)
    assert "Call budget exceeded for document" in err
    assert "3 calls dispatched exceeding budget of 3" in err


def test_post_job_summary_logging():
    """Verify post-job summary collates purpose, retries, repairs, limiter wait, and total time."""
    ledger = get_call_ledger()
    doc_id = "test-doc-summary-999"
    ledger.set_document_budget(doc_id, 20)

    # Record diverse calls
    ledger.record_call(document_id=doc_id, purpose="classify", status="ok", latency=0.5, tokens=100)
    ledger.record_call(document_id=doc_id, purpose="embed", status="ok", latency=0.2, tokens=50)
    ledger.record_call(document_id=doc_id, purpose="analyze", status="ok", latency=1.0, tokens=300)
    ledger.record_call(
        document_id=doc_id,
        purpose="retry",
        status="429 minute",
        latency=0.1,
        tokens=0,
        attempt_number=2,
    )
    ledger.record_call(
        document_id=doc_id,
        purpose="repair",
        status="invalid JSON",
        latency=0.0,
        tokens=50,
        attempt_number=2,
    )
    ledger.record_call(document_id=doc_id, purpose="summary", status="ok", latency=0.8, tokens=200)

    summary = ledger.log_job_summary(
        document_id=doc_id,
        total_time=5.432,
        limiter_wait_time=1.234,
    )

    assert summary["document_id"] == doc_id
    assert summary["total_calls"] == 6
    assert summary["calls_by_purpose"]["classify"] == 1
    assert summary["calls_by_purpose"]["embed"] == 1
    assert summary["calls_by_purpose"]["analyze"] == 1
    assert summary["calls_by_purpose"]["retry"] == 1
    assert summary["calls_by_purpose"]["repair"] == 1
    assert summary["calls_by_purpose"]["summary"] == 1
    assert summary["retries"] >= 1
    assert summary["repairs"] >= 1
    assert summary["total_time_seconds"] == 5.432
    assert summary["limiter_wait_time_seconds"] == 1.234


def test_today_summary_and_cli_format():
    """Verify today's calls by purpose table matches AI Studio comparison format."""
    ledger = get_call_ledger()
    today_str = datetime.now(UTC).strftime("%Y-%m-%d")

    ledger.record_call(purpose="embed", status="ok", tokens=100, latency=0.1)
    ledger.record_call(purpose="classify", status="ok", tokens=150, latency=0.2)
    ledger.record_call(purpose="analyze", status="ok", tokens=500, latency=1.5)
    ledger.record_call(purpose="repair", status="invalid JSON", tokens=100, latency=0.0)
    ledger.record_call(purpose="retry", status="429 minute", tokens=0, latency=0.05)
    ledger.record_call(purpose="summary", status="ok", tokens=300, latency=1.0)

    summary = ledger.get_today_summary()
    assert summary["date"] == today_str
    assert summary["total_calls"] == 6
    assert summary["calls_by_purpose"]["embed"] == 1
    assert summary["calls_by_purpose"]["classify"] == 1
    assert summary["calls_by_purpose"]["analyze"] == 1
    assert summary["calls_by_purpose"]["repair"] == 1
    assert summary["calls_by_purpose"]["retry"] == 1
    assert summary["calls_by_purpose"]["summary"] == 1
    assert summary["total_tokens"] == 1150

    cli_table = ledger.format_today_table()
    assert f"GEMINI CALL LEDGER [{today_str} UTC]" in cli_table
    assert "Total Outbound Requests: 6" in cli_table
    assert "Calls by Purpose" in cli_table
    assert "Calls by Status" in cli_table
    assert "AI Studio" in cli_table


@pytest.mark.asyncio
async def test_latency_simulating_fake_llm_and_injections():
    """Verify latency-simulating fake LLM obeys rate limits and injects 429, 503, invalid JSON."""
    limiter = SharedModelRateLimiter(
        model_name="fake-test-model", max_rpm=100, max_tpm=50000, max_rpd=1000
    )
    # Using small sleep range (0.01 - 0.02s) for fast unit test execution
    fake = LatencySimulatingFakeLLM(
        model_name="fake-test-model",
        sleep_range=(0.01, 0.02),
        rate_limiter=limiter,
    )

    prompt = "<<<UNTRUSTED_DOCUMENT_CLAUSE>>>Customer shall defend and indemnify Provider against all claims.<<<END_UNTRUSTED_DOCUMENT_CLAUSE>>>"

    # 1. Normal execution
    res = await fake.generate_structured(prompt, LLMClauseAnalysis)
    assert res.risk_level in ("HIGH", "LOW", "MEDIUM", "CRITICAL")
    ledger = get_call_ledger()
    assert ledger.get_today_summary()["total_calls"] == 1

    # 2. Injected 429 minute rate limit
    fake.set_injections(inject_429_minute=1)
    with pytest.raises(AIServiceError) as exc_429:
        await fake.generate_structured(prompt, LLMClauseAnalysis)
    assert "429 RESOURCE_EXHAUSTED" in str(exc_429.value)
    today_sum = ledger.get_today_summary()
    assert today_sum["calls_by_status"].get("429 minute") == 1

    # 3. Injected 503 Service Unavailable
    fake.set_injections(inject_503=1)
    with pytest.raises(AIServiceError) as exc_503:
        await fake.generate_structured(prompt, LLMClauseAnalysis)
    assert "503 Service Unavailable" in str(exc_503.value)
    today_sum = ledger.get_today_summary()
    assert today_sum["calls_by_status"].get("503") == 1

    # 4. Injected Invalid JSON
    fake.set_injections(inject_invalid_json=1)
    with pytest.raises(json.JSONDecodeError):
        await fake.generate_structured(prompt, LLMClauseAnalysis)
    today_sum = ledger.get_today_summary()
    assert today_sum["calls_by_status"].get("invalid JSON") == 1

    # 5. Injected 429 Daily Quota Exhaustion
    fake.set_injections(inject_429_day=True)
    with pytest.raises(DailyQuotaExceededError):
        await fake.generate_structured(prompt, LLMClauseAnalysis)
    today_sum = ledger.get_today_summary()
    assert today_sum["calls_by_status"].get("429 day") == 1


@pytest.mark.asyncio
async def test_admin_ledger_endpoints():
    """Verify HTTP endpoints /api/v1/admin/ledger/today and document summary."""
    app = create_app()
    ledger = get_call_ledger()
    doc_id = "11111111-2222-3333-4444-555555555555"

    ledger.record_call(document_id=doc_id, purpose="classify", status="ok", tokens=100)
    ledger.record_call(document_id=doc_id, purpose="analyze", status="ok", tokens=300)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Admin today endpoint
        resp_today = await client.get("/api/v1/admin/ledger/today")
        assert resp_today.status_code == 200
        data_today = resp_today.json()
        assert data_today["total_calls"] == 2
        assert data_today["calls_by_purpose"]["classify"] == 1
        assert data_today["calls_by_purpose"]["analyze"] == 1

        # 2. Document summary endpoint
        resp_doc = await client.get(f"/api/v1/admin/ledger/document/{doc_id}")
        assert resp_doc.status_code == 200
        data_doc = resp_doc.json()
        assert data_doc["document_id"] == doc_id
        assert data_doc["total_calls"] == 2
        assert data_doc["total_tokens"] == 400
