"""
Unit and integration tests for fast-fail daily quota handling and clean job resume.

Tests cover:
1. Exact error-based daily quota detection (checking per-day quota metric names, not just retryDelay).
2. Shared quota-exhausted flag across concurrent batches.
3. Rapid abort of sibling batches on daily 429.
4. Resuming at clause 13: verifying finished clauses 1-12 are NOT re-sent to the LLM after quota reset.
"""

import uuid
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from app.ai.llm import GeminiLLMClient, is_daily_quota_error
from app.ai.pipeline import RiskAnalysisPipeline
from app.ai.rate_limiter import (
    DailyQuotaExceededError,
    SharedModelRateLimiter,
)
from app.core.database import async_session_factory
from app.document_processing.schema import Clause as ProcessedClause
from app.document_processing.schema import ExtractionResult
from app.models.analysis import AnalysisResult
from app.models.clause import Clause
from app.models.document import Document
from app.models.user import User
from app.services.analysis_service import AnalysisService


def test_is_daily_quota_error_detection():
    """Verify daily quota errors are distinguished from transient per-minute (RPM) rate limits."""
    # Real Google AI Studio daily quota error messages
    daily_error_1 = (
        "429 RESOURCE_EXHAUSTED. Quota exceeded for metric: "
        "generativelanguage.googleapis.com/generate_content_free_tier_requests, limit: 500, "
        "model: gemini-3.5-flash-lite, description: Generate content requests per day limit exceeded on Free Tier. "
        "Please retry in 34m59s."
    )
    daily_error_2 = (
        "QuotaFailure: violations: [{'quotaMetric': 'generativelanguage.googleapis.com/generate_content_free_tier_requests', "
        "'quotaId': 'GenerateRequestsPerDayPerProjectPerModel-FreeTier'}]"
    )
    daily_error_3 = "Generate content requests per day limit exceeded on Free Tier."

    assert is_daily_quota_error(daily_error_1) is True
    assert is_daily_quota_error(daily_error_2) is True
    assert is_daily_quota_error(daily_error_3) is True

    # Transient per-minute rate limit (RPM) or temporary service unavailable: should NOT be marked daily
    transient_rpm_1 = "429 RESOURCE_EXHAUSTED: Rate limit exceeded. Please retry in 2.5s."
    transient_rpm_2 = "503 The model is temporarily overloaded. retryDelay: '3s'"
    transient_rpm_3 = "RESOURCE_EXHAUSTED: Per-minute request quota exhausted. retry in 1.2s"

    # Crucial discriminator test: Google's shared metric name with per-minute quota ID MUST NOT trip daily flag
    transient_rpm_shared_metric_1 = (
        "429 RESOURCE_EXHAUSTED. Quota exceeded for metric: "
        "generativelanguage.googleapis.com/generate_content_free_tier_requests, limit: 15, "
        "model: gemini-3.5-flash-lite, quotaId: GenerateRequestsPerMinutePerProjectPerModel-FreeTier, "
        "description: Generate content requests per minute limit exceeded on Free Tier. "
        "Please retry in 2.5s."
    )
    transient_rpm_shared_metric_2 = (
        "QuotaFailure: violations: [{'quotaMetric': 'generativelanguage.googleapis.com/generate_content_free_tier_requests', "
        "'quotaId': 'GenerateRequestsPerMinutePerProjectPerModel-FreeTier'}]"
    )

    assert is_daily_quota_error(transient_rpm_1) is False
    assert is_daily_quota_error(transient_rpm_2) is False
    assert is_daily_quota_error(transient_rpm_3) is False
    assert is_daily_quota_error(transient_rpm_shared_metric_1) is False
    assert is_daily_quota_error(transient_rpm_shared_metric_2) is False


@pytest.mark.asyncio
async def test_per_minute_429_with_free_tier_metric_retries_and_succeeds():
    """
    Verify that an incoming 429 containing the shared 'generate_content_free_tier_requests' metric
    along with a per-minute quotaId retries for a few seconds and succeeds, without fast-failing
    or tripping the daily quota exhausted flag.
    """
    client = GeminiLLMClient(force_offline=False)
    client._force_offline = False
    client._rate_limiter._redis_available = False
    client._rate_limiter.reset_daily_quota_exhausted()

    rpm_429_error = (
        "429 RESOURCE_EXHAUSTED. Quota exceeded for metric: "
        "generativelanguage.googleapis.com/generate_content_free_tier_requests, limit: 15, "
        "model: gemini-3.5-flash-lite, quotaId: GenerateRequestsPerMinutePerProjectPerModel-FreeTier, "
        "description: Generate content requests per minute limit exceeded. Please retry in 0.05s."
    )

    call_count = 0
    from unittest.mock import MagicMock

    async def mock_generate_content(*args: Any, **kwargs: Any) -> Any:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise Exception(rpm_429_error)
        resp = MagicMock()
        resp.text = '{"status": "ok"}'
        return resp

    mock_client = MagicMock()
    mock_client.aio.models.generate_content = AsyncMock(side_effect=mock_generate_content)
    client._client = mock_client

    result = await client._call_content_api(
        contents="Test prompt",
        sys_inst="Test sys inst",
        response_mime_type="application/json",
    )

    # Must retry and return the valid response
    assert result == '{"status": "ok"}'
    assert call_count == 2
    # The daily quota flag MUST NOT have been tripped
    assert client._rate_limiter.is_daily_quota_exhausted is False


@pytest.mark.asyncio
async def test_shared_quota_flag_auto_expires_and_clears_on_success():
    """Verify shared quota flag auto-expires on day change and clears on confirmed success."""
    limiter = SharedModelRateLimiter(
        model_name="test-expiry-model",
        max_rpm=10,
        max_tpm=1000,
        max_rpd=100,
    )
    limiter._redis_available = False

    # 1. Mark exhausted on a prior date
    limiter.mark_daily_quota_exhausted(notice="Yesterday's quota limit reached")
    assert limiter._daily_quota_exhausted is True
    limiter._daily_quota_date = "2020-01-01"

    # Accessing property auto-detects date change and expires the flag
    assert limiter.is_daily_quota_exhausted is False
    assert limiter._daily_quota_exhausted is False
    assert limiter._daily_quota_date is None

    # 2. Mark exhausted today
    limiter.mark_daily_quota_exhausted(notice="Today's quota limit reached")
    assert limiter.is_daily_quota_exhausted is True

    # 3. Confirmed successful call calls record_success() and clears the flag
    limiter.record_success()
    assert limiter.is_daily_quota_exhausted is False
    assert limiter._daily_quota_exhausted is False


@pytest.mark.asyncio
async def test_shared_quota_exhausted_flag():
    """Verify SharedModelRateLimiter shares a single exhausted flag across all tasks."""
    limiter = SharedModelRateLimiter(
        model_name="test-shared-quota-model",
        max_rpm=10,
        max_tpm=1000,
        max_rpd=100,
    )
    limiter._redis_available = False

    # Initially not exhausted
    assert limiter.is_daily_quota_exhausted is False

    # Mark daily quota exhausted
    limiter.mark_daily_quota_exhausted(notice="Daily limit reached in batch 1")
    assert limiter.is_daily_quota_exhausted is True

    # Any subsequent acquire call fails immediately with DailyQuotaExceededError
    with pytest.raises(DailyQuotaExceededError) as exc_info:
        await limiter.acquire(estimated_tokens=10)

    assert "Daily limit reached in batch 1" in str(
        exc_info.value
    ) or "Daily API quota reached" in str(exc_info.value)

    # Reset clears the flag cleanly
    limiter.reset_daily_quota_exhausted()
    assert limiter.is_daily_quota_exhausted is False


@pytest.mark.asyncio
async def test_pipeline_aborts_sibling_batches_on_daily_quota():
    """Verify that when one batch encounters a daily quota error, sibling batches abort immediately."""
    offline_llm = GeminiLLMClient(force_offline=True)
    pipeline = RiskAnalysisPipeline(llm_client=offline_llm)
    dummy_vec = [0.0] * 768
    pipeline.embedder.embed_query = AsyncMock(return_value=dummy_vec)
    pipeline.embedder.embed_texts = AsyncMock(return_value=[dummy_vec] * 12)

    clauses_input = [
        {"clause_id": f"c_{i}", "clause_text": f"Clause {i} content", "clause_vector": dummy_vec}
        for i in range(12)
    ]

    call_count = 0

    async def mock_generate_structured(*args: Any, **kwargs: Any) -> Any:
        nonlocal call_count
        call_count += 1
        if call_count >= 2:
            offline_llm._rate_limiter.mark_daily_quota_exhausted()
            raise DailyQuotaExceededError(
                model_name=offline_llm.model_name,
                notice="Daily API quota reached.",
            )
        return offline_llm._generate_offline_reasoning(
            kwargs.get("prompt", ""), kwargs.get("response_model")
        )

    with patch.object(offline_llm, "generate_structured", side_effect=mock_generate_structured):
        with pytest.raises(DailyQuotaExceededError):
            await pipeline.analyze_clauses_batch(
                clauses=clauses_input,
                batch_size=4,
                max_concurrency=2,
            )

    # Clean up rate limiter state
    offline_llm._rate_limiter.reset_daily_quota_exhausted()


@pytest.mark.asyncio
async def test_resume_at_clause_13_without_resent():
    """
    Test that finished clauses (1-12) are committed and NEVER re-sent to the LLM on resume.
    Only remaining unanalyzed clauses (13-15) are processed.
    """
    async with async_session_factory() as session:
        # 1. Create a test user
        user = User(
            email=f"resume_user_{uuid.uuid4().hex[:8]}@example.com",
            hashed_password="hashed_pwd",
            full_name="Test Resume User",
        )
        session.add(user)
        await session.flush()

        # 2. Create a test document
        doc = Document(
            user_id=user.id,
            filename="resume_test_contract.pdf",
            original_filename="resume_test_contract.pdf",
            file_path="uploads/test_contract.pdf",
            file_size=1024,
            file_type="pdf",
            status="uploaded",
            document_type="terms_and_conditions",
        )
        session.add(doc)
        await session.commit()

        # 3. Create 15 clauses for this document
        clauses = [
            Clause(
                id=uuid.uuid4(),
                document_id=doc.id,
                clause_index=i,
                clause_number=str(i),
                title=f"Clause {i}",
                content=f"This is the contractual text of clause {i}.",
                category="general",
                start_page=1,
                end_page=1,
            )
            for i in range(1, 16)
        ]
        session.add_all(clauses)
        await session.commit()

        # 4. Pre-populate clauses 1 to 12 as already analyzed in DB (simulating previous run before quota)
        for c in clauses[:12]:
            analysis = AnalysisResult(
                clause_id=c.id,
                document_id=doc.id,
                plain_english_summary=f"Plain English for clause {c.clause_index}.",
                risk_score=20,
                risk_category="LOW",
                risk_reasons=["Standard commercial term."],
                confidence_score=0.95,
                raw_llm_response={
                    "plain_english": f"Plain English for clause {c.clause_index}.",
                    "risk_level": "LOW",
                    "risk_score": 20,
                },
            )
            session.add(analysis)
        doc.status = "waiting for quota"
        await session.commit()

        # 5. Resume analysis using AnalysisService with instrumented pipeline
        service = AnalysisService(session)
        offline_llm = GeminiLLMClient(force_offline=True)
        offline_llm._rate_limiter.reset_daily_quota_exhausted()
        service.pipeline.clause_llm = offline_llm
        service.pipeline.summary_llm = offline_llm
        dummy_vec = [0.0] * 768
        service.pipeline.embedder.embed_texts = AsyncMock(return_value=[dummy_vec] * 15)
        service.pipeline.embedder.embed_query = AsyncMock(return_value=dummy_vec)

        sent_to_pipeline_clause_ids: list[str] = []
        original_analyze_batch = service.pipeline.analyze_clauses_batch

        async def tracking_analyze_batch(*args: Any, **kwargs: Any) -> list[dict[str, Any]]:
            clauses_arg = kwargs.get("clauses") or (args[0] if args else [])
            for c in clauses_arg:
                sent_to_pipeline_clause_ids.append(str(c.get("clause_id")))
            return await original_analyze_batch(*args, **kwargs)

        fake_segments = [
            ProcessedClause(
                id=f"seg_{i}",
                order=i,
                title=f"Clause {i}",
                text=f"This is the contractual text of clause {i}.",
                page=1,
            )
            for i in range(1, 16)
        ]
        fake_extraction = ExtractionResult(
            raw_text="COMMERCIAL CONTRACT. IN WITNESS WHEREOF, the parties hereby agree to the terms, limitation of liability, and indemnification and hold harmless.",
            is_scanned=False,
        )

        with (
            patch("app.services.analysis_service.extract_document", return_value=fake_extraction),
            patch(
                "app.document_processing.segmenter.DocumentSegmenter.segment",
                return_value=fake_segments,
            ),
            patch.object(
                service.pipeline, "analyze_clauses_batch", side_effect=tracking_analyze_batch
            ),
        ):
            await service._run_analysis_task(doc.id)

        # 6. Verify the resume behavior:
        # Clauses 1..12 MUST NOT have been sent to analyze_clauses_batch
        analyzed_1_to_12_ids = {str(c.id) for c in clauses[:12]}
        analyzed_13_to_15_ids = {str(c.id) for c in clauses[12:]}

        # Assert no finished clause was re-sent
        re_sent_clauses = analyzed_1_to_12_ids.intersection(set(sent_to_pipeline_clause_ids))
        assert len(re_sent_clauses) == 0, (
            f"Finished clauses were re-sent to pipeline: {re_sent_clauses}"
        )

        # Assert only clauses 13, 14, 15 were sent
        assert set(sent_to_pipeline_clause_ids) == analyzed_13_to_15_ids

        # 7. Verify final document state
        refreshed_doc = await service.document_repo.get_by_id(doc.id)
        assert refreshed_doc is not None
        assert refreshed_doc.status == "completed"

        # Verify all 15 clauses have analysis records in DB
        all_analyses = await service.analysis_repo.get_by_document(doc.id)
        assert len(all_analyses) == 15


@pytest.mark.asyncio
async def test_waiting_quota_jobs_auto_restart_after_flag_expires():
    """
    Part F.1: Verify the daily quota flag is stored with UTC-reset expiry and
    JobService.resume_waiting_for_quota_jobs() restarts waiting_for_quota jobs
    once the quota-exhausted flag expires/clears.
    """
    from app.ai.rate_limiter import get_model_rate_limiter
    from app.core.config import get_settings
    from app.models.job import Job
    from app.services.job_service import JobService

    settings = get_settings()
    clause_limiter = get_model_rate_limiter(settings.gemini_clause_model)
    summary_limiter = get_model_rate_limiter(settings.gemini_summary_model)
    embed_limiter = get_model_rate_limiter(settings.gemini_embedding_model)

    async with async_session_factory() as session:
        user = User(
            email=f"auto_resume_{uuid.uuid4().hex[:8]}@example.com",
            hashed_password="pwd",
            full_name="Auto Resume",
        )
        session.add(user)
        await session.flush()

        doc = Document(
            user_id=user.id,
            filename="waiting_doc.pdf",
            original_filename="waiting_doc.pdf",
            file_path="uploads/waiting_doc.pdf",
            file_size=512,
            file_type="pdf",
            status="waiting for quota",
            document_type="terms_and_conditions",
        )
        session.add(doc)
        await session.flush()

        job = Job(
            id=uuid.uuid4(),
            document_id=doc.id,
            user_id=user.id,
            status="waiting_for_quota",
            stage="waiting_for_quota",
            total_clauses=10,
            completed_clauses=4,
            cancel_requested=False,
        )
        session.add(job)
        await session.commit()

        job_service = JobService(session)
        try:
            # While daily quota flag is active, cron/service MUST NOT restart waiting jobs
            clause_limiter.mark_daily_quota_exhausted(notice="Daily cap hit")
            resumed_while_exhausted = await job_service.resume_waiting_for_quota_jobs()
            assert resumed_while_exhausted == 0

            # Once reset happens (flag expires / clears), waiting job is re-queued cleanly
            clause_limiter.reset_daily_quota_exhausted()
            summary_limiter.reset_daily_quota_exhausted()
            embed_limiter.reset_daily_quota_exhausted()

            resumed_count = await job_service.resume_waiting_for_quota_jobs()
            assert resumed_count >= 1

            await session.refresh(job)
            await session.refresh(doc)
            assert job.status == "queued"
            assert job.stage == "queued"
            assert doc.status == "uploaded"
        finally:
            clause_limiter.reset_daily_quota_exhausted()
            summary_limiter.reset_daily_quota_exhausted()
            embed_limiter.reset_daily_quota_exhausted()


@pytest.mark.asyncio
async def test_per_minute_429_with_latency_fake_retries_and_completes():
    """
    Part F.2: Per-minute 429 (with quotaId or transient RESOURCE_EXHAUSTED) must
    just retry and succeed without setting daily quota exhaustion.
    """
    from app.ai.latency_fake import LatencySimulatingFakeLLM
    from app.ai.response_parser import LLMClauseAnalysis

    rpm_only_err = (
        "429 RESOURCE_EXHAUSTED. Quota exceeded for metric: "
        "generativelanguage.googleapis.com/generate_content_free_tier_requests, limit: 15, "
        "quotaId: GenerateRequestsPerMinutePerProjectPerModel-FreeTier. Please retry in 0.05s."
    )
    assert is_daily_quota_error(rpm_only_err) is False

    limiter = SharedModelRateLimiter(
        model_name=f"rpm-retry-{uuid.uuid4().hex[:8]}",
        max_rpm=12,
        min_interval=0.0,
    )
    fake_llm = LatencySimulatingFakeLLM(
        model_name=limiter.model_name,
        sleep_range=(0.05, 0.08),
        rate_limiter=limiter,
        inject_429_minute=2,
    )

    pipeline = RiskAnalysisPipeline(llm_client=fake_llm)
    dummy_vec = [0.0] * 768
    pipeline.embedder.embed_query = AsyncMock(return_value=dummy_vec)

    # Simulate client retry wrapper around transient per-minute 429s
    attempts = 0
    analysis = None
    for _ in range(4):
        attempts += 1
        try:
            analysis = await fake_llm.generate_structured(
                prompt="<<<UNTRUSTED_DOCUMENT_CLAUSE>>>\nVendor liability is capped at $100.\n<<<END_UNTRUSTED_DOCUMENT_CLAUSE>>>",
                response_model=LLMClauseAnalysis,
            )
            break
        except Exception:
            assert limiter.is_daily_quota_exhausted is False

    assert attempts == 3
    assert analysis is not None
    assert limiter.is_daily_quota_exhausted is False


@pytest.mark.asyncio
async def test_non_legal_document_classification_returns_no_score():
    """
    Part F.3: Check document type before analysis; if non-legal (setup guide / README),
    say so cleanly and persist DocumentAnalysis with overall_risk_score=None and 0 clauses.
    """
    async with async_session_factory() as session:
        user = User(
            email=f"nonlegal_{uuid.uuid4().hex[:8]}@example.com",
            hashed_password="pwd",
            full_name="Non Legal User",
        )
        session.add(user)
        await session.flush()

        doc = Document(
            user_id=user.id,
            filename="setup_guide.pdf",
            original_filename="setup_guide.pdf",
            file_path="uploads/setup_guide.pdf",
            file_size=512,
            file_type="pdf",
            status="uploaded",
            document_type="other",
        )
        session.add(doc)
        await session.commit()

        service = AnalysisService(session)
        offline_llm = GeminiLLMClient(force_offline=True)
        offline_llm._rate_limiter.reset_daily_quota_exhausted()
        service.pipeline.clause_llm = offline_llm
        service.pipeline.summary_llm = offline_llm

        non_legal_extraction = ExtractionResult(
            raw_text=(
                "QUICKSTART & SETUP GUIDE\n"
                "Prerequisites: Python 3.12 and Node 20.\n"
                "Run pip install -r requirements.txt and npm install to start the dev server."
            ),
            is_scanned=False,
        )

        with patch(
            "app.services.analysis_service.extract_document", return_value=non_legal_extraction
        ):
            await service._run_analysis_task(doc.id)

        refreshed = await service.document_repo.get_by_id(doc.id)
        assert refreshed is not None
        assert refreshed.status == "completed"
        assert refreshed.document_type == "non_legal"

        doc_analysis = await service.doc_analysis_repo.get_by_document(doc.id)
        assert doc_analysis is not None
        assert doc_analysis.overall_risk_score is None
        assert "doesn't look like a legal" in (doc_analysis.overall_summary or "").lower()

        clauses = await service.analysis_repo.get_by_document(doc.id)
        assert len(clauses) == 0


@pytest.mark.asyncio
async def test_summary_reference_wording_enforced():
    """
    Part F.4: Summary may say "aligns with typical standards" only if references were
    retrieved; otherwise it MUST NOT claim alignment and must say "no close reference found".
    """
    from app.ai.response_parser import DocumentRiskAnalysis

    # 1. No retrieved references -> pipeline strips any hallucinated "aligns with typical standards"
    # and guarantees "no close reference found"
    fake_llm = GeminiLLMClient(force_offline=True)
    pipeline = RiskAnalysisPipeline(llm_client=fake_llm)

    hallucinated_response = DocumentRiskAnalysis(
        overall_risk_score=15,
        overall_risk_level="LOW",
        executive_summary="This contract aligns with typical standards in the industry.",
        key_risks=[],
        category_breakdown={},
        negotiation_priorities=[],
    )
    no_ref_clauses = [
        {
            "clause_id": "c1",
            "risk_score": 15,
            "risk_level": "LOW",
            "plain_english": "Standard payment schedule.",
            "risk_reasons": [],
            "retrieved_references": [],
        }
    ]

    with patch.object(fake_llm, "generate_structured", return_value=hallucinated_response):
        res_no_ref = await pipeline.aggregate_document(no_ref_clauses)

    summary_lower = res_no_ref.executive_summary.lower()
    assert "aligns with typical standards" not in summary_lower
    assert "no close reference found" in summary_lower

    # 2. Real retrieved references + standard clauses -> allowed to state "aligns with typical standards"
    with_ref_clauses = [
        {
            "clause_id": "c2",
            "risk_score": 10,
            "risk_level": "LOW",
            "plain_english": "Standard termination notice.",
            "risk_reasons": [],
            "retrieved_references": [{"id": "REF-TERM-001", "title": "Termination", "score": 0.91}],
        }
    ]
    res_with_ref = await pipeline.aggregate_document(with_ref_clauses)
    assert "aligns with typical standards" in res_with_ref.executive_summary.lower()
    assert "no close reference found" not in res_with_ref.executive_summary.lower()
