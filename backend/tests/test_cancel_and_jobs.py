"""
Part C Reliability Tests: Cancellation, Delete Cleanup, Limiter Slot Release,
Persistent ARQ Queueing, Startup Recovery, and Orphan Job Reaper.

Uses LatencySimulatingFakeLLM (10-14s sleep) to prove mid-run cancellation stops
outbound calls within < 2s without consuming live Gemini quota.
"""

import asyncio
import os
import signal
import subprocess
import sys
import time
import uuid
from pathlib import Path

import fitz
import pytest
from httpx import AsyncClient
from sqlalchemy import select, text

from app.ai.latency_fake import LatencySimulatingFakeEmbedder, LatencySimulatingFakeLLM
from app.ai.ledger import clear_call_context, get_call_ledger, set_call_context
from app.ai.rate_limiter import SharedModelRateLimiter
from app.api.v1.endpoints.documents import _active_analysis_tasks
from app.core.cancellation import (
    JobCancelledError,
    _cancelled_acks,
    _cancelled_documents,
    _cancelled_jobs,
    _cancelled_users,
    clear_cancelled,
    mark_cancelled,
    record_cache_key,
)
from app.core.database import async_session_factory
from app.models.analysis import AnalysisResult, DocumentAnalysis
from app.models.clause import Clause
from app.models.document import Document
from app.models.job import JOB_STATES, Job
from app.models.user import User
from app.services.analysis_service import AnalysisService
from app.services.job_service import (
    JobService,
    register_active_worker_task,
    unregister_active_worker_task,
)


def _build_legal_pdf(num_clauses: int = 16) -> bytes:
    doc = fitz.open()
    lines = ["COMMERCIAL MASTER SERVICES AGREEMENT\n"]
    for i in range(1, num_clauses + 1):
        lines.append(
            f"{i}. Clause Number {i}\n"
            f"Vendor's total liability under section {i} shall not exceed one hundred dollars ($100), "
            f"and Customer agrees to indemnify Vendor for any third-party claims arising herein.\n"
        )
    text_body = "\n".join(lines)
    # Split across pages if long
    page = doc.new_page()
    page.insert_text((50, 50), text_body[:3000], fontsize=9)
    if len(text_body) > 3000:
        page2 = doc.new_page()
        page2.insert_text((50, 50), text_body[3000:], fontsize=9)
    raw = doc.tobytes()
    doc.close()
    return raw


@pytest.fixture(autouse=True)
def clean_cancel_and_ledger_state():
    _cancelled_documents.clear()
    _cancelled_jobs.clear()
    _cancelled_users.clear()
    _cancelled_acks.clear()
    clear_call_context()
    get_call_ledger().reset()
    yield
    _cancelled_documents.clear()
    _cancelled_jobs.clear()
    _cancelled_users.clear()
    _cancelled_acks.clear()
    clear_call_context()
    get_call_ledger().reset()


@pytest.mark.asyncio
async def test_upload_enqueues_persistent_worker_job_not_in_api_process(client: AsyncClient):
    """
    Part C.1 & C.4 Proof: Uploading a document creates a persistent 'queued' Job in DB
    and does NOT execute analysis inside the API server process.
    """
    assert "queued" in JOB_STATES
    assert "waiting_for_quota" in JOB_STATES
    assert "cancelling" in JOB_STATES
    assert "cancelled" in JOB_STATES

    email = f"queue_proof_{uuid.uuid4().hex[:8]}@example.com"
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "Password123!", "full_name": "Queue Proof"},
    )
    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "Password123!"},
    )
    token = login_res.json()["data"]["access_token"]
    header = {"Authorization": f"Bearer {token}"}

    pdf_bytes = _build_legal_pdf(num_clauses=4)
    up = await client.post(
        "/api/v1/documents",
        headers=header,
        files={"file": ("worker_queue_proof.pdf", pdf_bytes, "application/pdf")},
    )
    assert up.status_code == 201
    doc_id = uuid.UUID(up.json()["data"]["id"])

    # API process must NOT spawn an internal BackgroundTasks analysis task
    assert doc_id not in _active_analysis_tasks

    # Persistent Job row must exist in PostgreSQL in queued state
    async with async_session_factory() as session:
        res = await session.execute(select(Job).where(Job.document_id == doc_id))
        job = res.scalar_one_or_none()
        assert job is not None
        assert job.status == "queued"
        assert job.arq_job_id is not None

    # Status endpoint reflects job metadata cleanly
    st = await client.get(f"/api/v1/documents/{doc_id}/status", headers=header)
    assert st.status_code == 200
    assert st.json()["data"]["job_status"] == "queued"

    # Cleanup
    del_res = await client.delete(f"/api/v1/documents/{doc_id}", headers=header)
    assert del_res.status_code == 204


@pytest.mark.asyncio
async def test_cancel_while_waiting_in_limiter_releases_slots():
    """
    Part C.3: Checking cancel flag while waiting in SharedModelRateLimiter exits promptly
    and releases any limiter slots rather than holding capacity.
    """
    limiter = SharedModelRateLimiter(
        model_name=f"cancel-limiter-{uuid.uuid4().hex[:8]}",
        max_rpm=1,
        max_tpm=10000,
        max_rpd=100,
        min_interval=0.0,
    )
    limiter._redis_available = False

    doc_id = f"doc-limiter-{uuid.uuid4().hex[:8]}"
    await clear_cancelled(document_id=doc_id)

    # First call consumes the single 1 RPM slot
    set_call_context(job_id=doc_id, document_id=doc_id, user_id="u-lim")
    slot1 = await limiter.acquire(estimated_tokens=10)
    assert len(limiter._local_history) == 1

    # Release slot cleanly checks slot removal & RPD refund
    await limiter.release_slot(member_id=slot1, refund_rpd=True)
    assert len(limiter._local_history) == 0

    # Re-occupy the 1 RPM slot so second acquire must block waiting on the 60s window
    await limiter.acquire(estimated_tokens=10)
    assert len(limiter._local_history) == 1

    t0 = time.perf_counter()

    async def trigger_cancel():
        await asyncio.sleep(0.3)
        await mark_cancelled(document_id=doc_id)

    cancel_task = asyncio.create_task(trigger_cancel())
    with pytest.raises(JobCancelledError):
        await limiter.acquire(estimated_tokens=10)

    elapsed = time.perf_counter() - t0
    await cancel_task

    assert elapsed < 2.0, f"Limiter waited too long after cancel: {elapsed:.2f}s"
    # Second request must NOT have been added to limiter history
    assert len(limiter._local_history) == 1


@pytest.mark.asyncio
async def test_delete_document_mid_run_latency_fake_stops_within_2s_zero_orphans(
    client: AsyncClient,
):
    """
    Part C.2, C.3, C.5, C.6:
    Start an analysis run using LatencySimulatingFakeLLM (10-12s sleep per call).
    Delete the document mid-run via DELETE /api/v1/documents/{id}.
    Verify:
    - Cancellation stops execution and DELETE returns cleanly with confirmation headers
    - Zero Gemini calls occur after cancel (within 2s)
    - Zero orphan jobs, clauses, analysis_results, document_analyses, or cached AI entries remain
    """
    email = f"mid_del_{uuid.uuid4().hex[:8]}@example.com"
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "Password123!", "full_name": "Mid Delete User"},
    )
    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "Password123!"},
    )
    token = login_res.json()["data"]["access_token"]
    header = {"Authorization": f"Bearer {token}"}

    pdf_bytes = _build_legal_pdf(num_clauses=16)
    up = await client.post(
        "/api/v1/documents",
        headers=header,
        files={"file": ("mid_run_cancel.pdf", pdf_bytes, "application/pdf")},
    )
    assert up.status_code == 201
    doc_id = uuid.UUID(up.json()["data"]["id"])

    limiter = SharedModelRateLimiter(
        model_name=f"fake-cancel-{uuid.uuid4().hex[:8]}",
        max_rpm=12,
        max_tpm=250000,
        max_rpd=500,
        min_interval=0.0,
    )
    fake_llm = LatencySimulatingFakeLLM(
        model_name=limiter.model_name,
        sleep_range=(10.0, 12.0),
        rate_limiter=limiter,
    )
    fake_embedder = LatencySimulatingFakeEmbedder(sleep_range=(0.05, 0.1))

    worker_started = asyncio.Event()

    async def run_worker_simulation():
        async with async_session_factory() as session:
            svc = AnalysisService(session)
            svc.pipeline.clause_llm = fake_llm
            svc.pipeline.summary_llm = fake_llm
            svc.pipeline.embedder = fake_embedder
            svc.pipeline.retrieval_service.embedder = fake_embedder

            async def _run():
                current_task = asyncio.current_task()
                if current_task is not None:
                    register_active_worker_task(doc_id, current_task)
                worker_started.set()
                try:
                    await svc._run_analysis_task(doc_id)
                finally:
                    unregister_active_worker_task(doc_id)

            await _run()

    worker_task = asyncio.create_task(run_worker_simulation())
    await worker_started.wait()
    # Allow classification + embedding + batch dispatch into 10-12s sleep
    await asyncio.sleep(0.8)

    calls_before_delete = len(get_call_ledger().get_records())
    t_del = time.perf_counter()

    del_resp = await client.delete(f"/api/v1/documents/{doc_id}", headers=header)
    del_elapsed = time.perf_counter() - t_del
    assert del_resp.status_code == 204
    assert "X-Purged-Summary" in del_resp.headers
    assert "X-Kept-Summary" in del_resp.headers
    assert del_elapsed < 5.0

    # Wait for worker task to finish unwinding
    with pytest.raises((asyncio.CancelledError, JobCancelledError)):
        await worker_task

    # Give 2s window to ensure ZERO subsequent Gemini calls happen
    await asyncio.sleep(2.0)
    calls_after_cancel = len(get_call_ledger().get_records())
    assert calls_after_cancel <= calls_before_delete, (
        f"Calls continued after cancel! before={calls_before_delete}, after={calls_after_cancel}"
    )

    # Verify zero rows remain for deleted document and zero orphan jobs
    async with async_session_factory() as session:
        assert (
            await session.execute(select(Document).where(Document.id == doc_id))
        ).scalar_one_or_none() is None
        assert (
            await session.execute(select(Clause).where(Clause.document_id == doc_id))
        ).scalars().all() == []
        assert (
            await session.execute(
                select(AnalysisResult).where(AnalysisResult.document_id == doc_id)
            )
        ).scalars().all() == []
        assert (
            await session.execute(
                select(DocumentAnalysis).where(DocumentAnalysis.document_id == doc_id)
            )
        ).scalar_one_or_none() is None
        assert (
            await session.execute(select(Job).where(Job.document_id == doc_id))
        ).scalars().all() == []


@pytest.mark.asyncio
async def test_account_deletion_cancels_jobs_purges_caches_and_reports_kept(client: AsyncClient):
    """
    Part C.2, C.5, C.6:
    Account deletion cancels all running & queued jobs for the user first,
    purges documents, clauses, results, jobs, files, and AI caches, and reports what is kept.
    """
    email = f"acct_del_{uuid.uuid4().hex[:8]}@example.com"
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "Password123!", "full_name": "Account Cancel User"},
    )
    user_id = uuid.UUID(reg.json()["data"]["id"])
    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "Password123!"},
    )
    token = login_res.json()["data"]["access_token"]
    header = {"Authorization": f"Bearer {token}"}

    pdf_bytes = _build_legal_pdf(num_clauses=8)
    up1 = await client.post(
        "/api/v1/documents",
        headers=header,
        files={"file": ("acct_doc_1.pdf", pdf_bytes, "application/pdf")},
    )
    up2 = await client.post(
        "/api/v1/documents",
        headers=header,
        files={"file": ("acct_doc_2.pdf", pdf_bytes, "application/pdf")},
    )
    doc1_id = uuid.UUID(up1.json()["data"]["id"])
    doc2_id = uuid.UUID(up2.json()["data"]["id"])

    limiter = SharedModelRateLimiter(
        model_name=f"fake-acct-{uuid.uuid4().hex[:8]}",
        max_rpm=12,
        min_interval=0.0,
    )
    fake_llm = LatencySimulatingFakeLLM(
        model_name=limiter.model_name,
        sleep_range=(10.0, 12.0),
        rate_limiter=limiter,
    )
    # Seed a cached AI entry tied to user_id & doc1_id
    set_call_context(job_id=str(doc1_id), document_id=str(doc1_id), user_id=str(user_id))
    fake_llm._prompt_cache["user_test_prompt_key"] = {"cached": True}
    record_cache_key(
        "prompt", "user_test_prompt_key", document_id=str(doc1_id), user_id=str(user_id)
    )

    worker_started = asyncio.Event()

    async def run_doc1_worker():
        async with async_session_factory() as session:
            svc = AnalysisService(session)
            svc.pipeline.clause_llm = fake_llm
            svc.pipeline.summary_llm = fake_llm
            svc.pipeline.embedder = LatencySimulatingFakeEmbedder(sleep_range=(0.05, 0.1))
            svc.pipeline.retrieval_service.embedder = svc.pipeline.embedder
            current_task = asyncio.current_task()
            if current_task is not None:
                register_active_worker_task(doc1_id, current_task)
            worker_started.set()
            try:
                await svc._run_analysis_task(doc1_id)
            finally:
                unregister_active_worker_task(doc1_id)

    t1 = asyncio.create_task(run_doc1_worker())
    await worker_started.wait()
    await asyncio.sleep(0.5)

    calls_at_delete = len(get_call_ledger().get_records())
    del_resp = await client.delete("/api/v1/auth/me", headers=header)
    assert del_resp.status_code == 200
    payload = del_resp.json()["data"]
    assert payload["purged"]["documents"] == 2
    assert payload["purged"]["memory_cache_entries_purged"] >= 1
    assert "audit_logs" in payload["kept"]
    assert "call_ledger" in payload["kept"]

    with pytest.raises((asyncio.CancelledError, JobCancelledError)):
        await t1

    # Wait 2s to verify zero post-delete calls
    await asyncio.sleep(2.0)
    assert len(get_call_ledger().get_records()) <= calls_at_delete
    assert "user_test_prompt_key" not in fake_llm._prompt_cache

    async with async_session_factory() as session:
        assert (
            await session.execute(select(User).where(User.id == user_id))
        ).scalar_one_or_none() is None
        assert (
            await session.execute(select(Job).where(Job.user_id == user_id))
        ).scalars().all() == []
        assert (
            await session.execute(select(Document).where(Document.id.in_([doc1_id, doc2_id])))
        ).scalars().all() == []


@pytest.mark.asyncio
async def test_startup_marks_running_jobs_interrupted_and_reaper_removes_orphans():
    """
    Part C.4 & C.6:
    - On server/worker startup recovery, jobs left in 'running' become 'interrupted',
      and jobs left in 'cancelling' with cancel_requested=True become 'cancelled'.
    - Periodic reaper deletes orphan jobs whose document or user no longer exists.
    """
    async with async_session_factory() as session:
        user = User(
            email=f"restart_{uuid.uuid4().hex[:8]}@example.com",
            hashed_password="hash",
            full_name="Restart Test",
        )
        session.add(user)
        await session.flush()

        doc = Document(
            user_id=user.id,
            filename="restart_doc.pdf",
            original_filename="restart_doc.pdf",
            file_path="uploads/restart_doc.pdf",
            file_type="pdf",
            document_type="contract",
            file_size=512,
            status="analyzing",
        )
        session.add(doc)
        await session.flush()

        running_job = Job(
            document_id=doc.id,
            user_id=user.id,
            status="running",
            stage="analyzing",
            cancel_requested=False,
        )
        cancelling_job = Job(
            document_id=doc.id,
            user_id=user.id,
            status="cancelling",
            stage="analyzing",
            cancel_requested=True,
        )
        orphan_missing_doc_job = Job(
            document_id=uuid.uuid4(),
            user_id=user.id,
            status="queued",
            stage="queued",
        )
        orphan_missing_user_job = Job(
            document_id=doc.id,
            user_id=uuid.uuid4(),
            status="queued",
            stage="queued",
        )
        session.add_all(
            [running_job, cancelling_job, orphan_missing_doc_job, orphan_missing_user_job]
        )
        await session.commit()

        # Store plain UUIDs before expiring session objects so AsyncSession doesn't lazy-load
        running_id = running_job.id
        cancelling_id = cancelling_job.id
        orphan_doc_id = orphan_missing_doc_job.id
        orphan_user_id = orphan_missing_user_job.id
        doc_uuid = doc.id
        user_uuid = user.id

        job_svc = JobService(session)
        marked = await job_svc.mark_interrupted_on_startup()
        assert marked >= 2

        session.expire_all()
        j_run = await session.get(Job, running_id)
        j_can = await session.get(Job, cancelling_id)
        assert j_run is not None and j_run.status == "interrupted"
        assert j_can is not None and j_can.status == "cancelled"

        reap_stats = await job_svc.reap_orphan_jobs()
        assert reap_stats["db_orphans_reaped"] >= 2

        session.expire_all()
        assert await session.get(Job, orphan_doc_id) is None
        assert await session.get(Job, orphan_user_id) is None

        # Cleanup non-orphan test fixtures
        await session.execute(
            text("DELETE FROM jobs WHERE id IN (:id1, :id2)"),
            {"id1": running_id, "id2": cancelling_id},
        )
        await session.execute(text("DELETE FROM documents WHERE id = :did"), {"did": doc_uuid})
        await session.execute(text("DELETE FROM users WHERE id = :uid"), {"uid": user_uuid})
        await session.commit()


@pytest.mark.asyncio
async def test_cross_process_cancel_flag_stops_latency_fake_without_task_handle(
    client: AsyncClient,
):
    """
    Part C.2, C.3 & C.6:
    Simulate a separate worker process that does NOT share asyncio.Task handles with the API process.
    Deleting the document sets DB + Redis cancel flags, causing LatencySimulatingFakeLLM
    to abort mid-call within <= 2s, releasing limiter slots, writing 0 analysis rows, and leaving 0 orphan jobs.
    """
    email = f"xproc_{uuid.uuid4().hex[:8]}@example.com"
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "Password123!", "full_name": "Cross Proc User"},
    )
    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "Password123!"},
    )
    token = login_res.json()["data"]["access_token"]
    header = {"Authorization": f"Bearer {token}"}

    pdf_bytes = _build_legal_pdf(num_clauses=12)
    up = await client.post(
        "/api/v1/documents",
        headers=header,
        files={"file": ("xproc_cancel.pdf", pdf_bytes, "application/pdf")},
    )
    assert up.status_code == 201
    doc_id = uuid.UUID(up.json()["data"]["id"])

    limiter = SharedModelRateLimiter(
        model_name=f"xproc-fake-{uuid.uuid4().hex[:8]}",
        max_rpm=12,
        min_interval=0.0,
    )
    fake_llm = LatencySimulatingFakeLLM(
        model_name=limiter.model_name,
        sleep_range=(10.0, 12.0),
        rate_limiter=limiter,
    )
    fake_embedder = LatencySimulatingFakeEmbedder(sleep_range=(0.05, 0.1))

    async def remote_worker():
        # Deliberately do NOT register task handle in _active_worker_tasks
        async with async_session_factory() as session:
            svc = AnalysisService(session)
            svc.pipeline.clause_llm = fake_llm
            svc.pipeline.summary_llm = fake_llm
            svc.pipeline.embedder = fake_embedder
            svc.pipeline.retrieval_service.embedder = fake_embedder
            await svc._run_analysis_task(doc_id)

    worker_task = asyncio.create_task(remote_worker())
    # Wait for classify call to enter 10-12s sleep inside LatencySimulatingFakeLLM
    await asyncio.sleep(0.8)

    t_cancel = time.perf_counter()
    del_resp = await client.delete(f"/api/v1/documents/{doc_id}", headers=header)
    assert del_resp.status_code == 204
    cancel_elapsed = time.perf_counter() - t_cancel

    with pytest.raises((asyncio.CancelledError, JobCancelledError)):
        await asyncio.wait_for(worker_task, timeout=2.0)

    assert cancel_elapsed < 2.5, f"Cross-process cancel took {cancel_elapsed:.2f}s"
    # Limiter slot reserved for classify call must have been released on cancel
    assert len(limiter._local_history) == 0
    assert get_call_ledger().get_document_summary(str(doc_id))["total_calls"] == 0

    async with async_session_factory() as session:
        assert (
            await session.execute(select(Job).where(Job.document_id == doc_id))
        ).scalars().all() == []
        assert (
            await session.execute(select(Clause).where(Clause.document_id == doc_id))
        ).scalars().all() == []
        assert (
            await session.execute(
                select(AnalysisResult).where(AnalysisResult.document_id == doc_id)
            )
        ).scalars().all() == []


@pytest.mark.asyncio
async def test_worker_os_process_sigkill_and_restart_recovery(
    client: AsyncClient,
    tmp_path: Path,
):
    """
    Real separate-OS-process SIGKILL / TerminateProcess crash and restart recovery test:
    1. Spawn ARQ worker subprocess #1 (APP_ENV=test, USE_LATENCY_FAKE=true, batch_size=4).
    2. Upload a 16-clause PDF and wait until Wave 1 commits partial AnalysisResult rows
       while Wave 2 is mid-flight ('running').
    3. Hard-kill worker #1 via OS SIGKILL (POSIX) / TerminateProcess (Windows).
    4. Verify DB still shows Job.status == 'running' and partial results + Redis embedcache exist.
    5. Spawn ARQ worker subprocess #2; startup() marks stuck 'running' job as 'interrupted'.
    6. Resume via POST /api/v1/documents/{doc_id}/resume and verify worker #2 completes with
       exact clause/analysis count (zero duplicate rows).
    """
    import shutil

    from app.core.config import get_settings

    settings = get_settings()
    backend_dir = Path(__file__).resolve().parent.parent

    worker_env = os.environ.copy()
    worker_env["APP_ENV"] = "test"
    worker_env["GOOGLE_API_KEY"] = ""
    worker_env["DATABASE_URL"] = str(settings.database_url)
    worker_env["REDIS_URL"] = str(settings.redis_url)
    worker_env["UPLOAD_DIR"] = str(settings.upload_path.resolve())
    worker_env["USE_LATENCY_FAKE"] = "true"
    worker_env["LATENCY_FAKE_MIN_SECONDS"] = "3.0"
    worker_env["LATENCY_FAKE_MAX_SECONDS"] = "3.5"
    worker_env["GEMINI_ANALYSIS_BATCH_SIZE"] = "4"

    worker1: subprocess.Popen[bytes] | None = None
    worker2: subprocess.Popen[bytes] | None = None
    worker1_log_path = tmp_path / "worker1.log"
    worker2_log_path = tmp_path / "worker2.log"
    user_id: uuid.UUID | None = None
    doc_id: uuid.UUID | None = None

    try:
        with worker1_log_path.open("wb") as w1_log:
            worker1 = subprocess.Popen(
                [sys.executable, "-m", "app.workers.main"],
                cwd=str(backend_dir),
                env=worker_env,
                stdout=w1_log,
                stderr=subprocess.STDOUT,
            )

        email = f"sigkill_{uuid.uuid4().hex[:8]}@example.com"
        reg_res = await client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": "Password123!", "full_name": "SIGKILL Recovery"},
        )
        assert reg_res.status_code == 201
        user_id = uuid.UUID(reg_res.json()["data"]["id"])

        login_res = await client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": "Password123!"},
        )
        token = login_res.json()["data"]["access_token"]
        header = {"Authorization": f"Bearer {token}"}

        pdf_bytes = _build_legal_pdf(num_clauses=16)
        up = await client.post(
            "/api/v1/documents",
            headers=header,
            files={"file": ("sigkill_recovery.pdf", pdf_bytes, "application/pdf")},
        )
        assert up.status_code == 201
        doc_id = uuid.UUID(up.json()["data"]["id"])

        # Wait until worker #1 completes Wave 1 (partial rows committed) while Wave 2 sleeps
        saw_mid_flight = False
        last_diag = ""
        deadline = time.monotonic() + 45.0
        while time.monotonic() < deadline:
            assert worker1.poll() is None, (
                f"Worker #1 exited unexpectedly: {worker1_log_path.read_text(errors='ignore')[-1000:]}"
            )
            async with async_session_factory() as session:
                job = (
                    await session.execute(select(Job).where(Job.document_id == doc_id))
                ).scalar_one_or_none()
                doc_row = await session.get(Document, doc_id)
                analyzed_rows = (
                    (
                        await session.execute(
                            select(AnalysisResult).where(AnalysisResult.document_id == doc_id)
                        )
                    )
                    .scalars()
                    .all()
                )
                last_diag = (
                    f"job_status={job.status if job else None}, "
                    f"job_stage={job.stage if job else None}, "
                    f"doc_status={doc_row.status if doc_row else None}, "
                    f"analyzed={len(analyzed_rows)}"
                )
                if job and job.status == "running" and 4 <= len(analyzed_rows) < 16:
                    saw_mid_flight = True
                    break
            await asyncio.sleep(0.1)

        assert saw_mid_flight, (
            f"Did not observe worker #1 mid-flight ({last_diag}). "
            f"Log tail:\n{worker1_log_path.read_text(errors='ignore')[-1200:]}"
        )

        # Ungraceful hard kill (uncatchable OS signal)
        if hasattr(signal, "SIGKILL"):
            os.kill(worker1.pid, signal.SIGKILL)
        else:
            worker1.kill()
        worker1.wait(timeout=10)

        # Immediately after crash: Job remains 'running', partial AnalysisResult rows persisted
        async with async_session_factory() as session:
            crashed_job = (
                await session.execute(select(Job).where(Job.document_id == doc_id))
            ).scalar_one_or_none()
            partial_count = len(
                (
                    await session.execute(
                        select(AnalysisResult).where(AnalysisResult.document_id == doc_id)
                    )
                )
                .scalars()
                .all()
            )
            assert crashed_job is not None
            assert crashed_job.status == "running"
            assert 4 <= partial_count < 16

        # Faster fake timings for worker #2 resume verification
        worker_env["LATENCY_FAKE_MIN_SECONDS"] = "0.2"
        worker_env["LATENCY_FAKE_MAX_SECONDS"] = "0.3"
        with worker2_log_path.open("wb") as w2_log:
            worker2 = subprocess.Popen(
                [sys.executable, "-m", "app.workers.main"],
                cwd=str(backend_dir),
                env=worker_env,
                stdout=w2_log,
                stderr=subprocess.STDOUT,
            )

        # Wait for worker #2 startup() hook to mark the stuck 'running' job as 'interrupted'
        interrupted_detected = False
        startup_deadline = time.monotonic() + 25.0
        while time.monotonic() < startup_deadline:
            assert worker2.poll() is None, "Worker #2 exited unexpectedly during startup recovery"
            async with async_session_factory() as session:
                recovered_job = (
                    await session.execute(select(Job).where(Job.id == crashed_job.id))
                ).scalar_one_or_none()
                if recovered_job and recovered_job.status == "interrupted":
                    interrupted_detected = True
                    break
            await asyncio.sleep(0.1)

        assert interrupted_detected, "Worker #2 startup() did not mark crashed job 'interrupted'"

        # Mark document 'interrupted' matches job recovery or resume directly if already resumable
        async with async_session_factory() as session:
            await session.execute(
                text("UPDATE documents SET status = 'interrupted' WHERE id = :did"),
                {"did": doc_id},
            )
            await session.commit()

        resume_res = await client.post(f"/api/v1/documents/{doc_id}/resume", headers=header)
        assert resume_res.status_code == 200

        # Wait for worker #2 to finish all remaining clauses + summary cleanly
        completed = False
        finish_deadline = time.monotonic() + 45.0
        while time.monotonic() < finish_deadline:
            async with async_session_factory() as session:
                refreshed_doc = await session.get(Document, doc_id)
                if refreshed_doc and refreshed_doc.status == "completed":
                    completed = True
                    break
            await asyncio.sleep(0.2)

        assert completed, "Worker #2 did not complete resumed document after SIGKILL recovery"

        async with async_session_factory() as session:
            final_clauses = (
                (await session.execute(select(Clause).where(Clause.document_id == doc_id)))
                .scalars()
                .all()
            )
            final_analyses = (
                (
                    await session.execute(
                        select(AnalysisResult).where(AnalysisResult.document_id == doc_id)
                    )
                )
                .scalars()
                .all()
            )
            doc_summary = (
                await session.execute(
                    select(DocumentAnalysis).where(DocumentAnalysis.document_id == doc_id)
                )
            ).scalar_one_or_none()
            expected_total = crashed_job.total_clauses or 17
            assert expected_total >= 16
            assert len(final_clauses) == expected_total
            assert len(final_analyses) == expected_total
            assert len({a.clause_id for a in final_analyses}) == expected_total
            assert doc_summary is not None
            assert doc_summary.overall_risk_score is not None
    finally:
        for proc in (worker1, worker2):
            if proc is not None and proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
        if user_id is not None:
            async with async_session_factory() as session:
                if doc_id is not None:
                    await session.execute(
                        text("DELETE FROM jobs WHERE document_id = :did"), {"did": doc_id}
                    )
                    await session.execute(
                        text("DELETE FROM analysis_results WHERE document_id = :did"),
                        {"did": doc_id},
                    )
                    await session.execute(
                        text("DELETE FROM document_analysis WHERE document_id = :did"),
                        {"did": doc_id},
                    )
                    await session.execute(
                        text("DELETE FROM clauses WHERE document_id = :did"), {"did": doc_id}
                    )
                    await session.execute(
                        text("DELETE FROM documents WHERE id = :did"), {"did": doc_id}
                    )
                await session.execute(text("DELETE FROM users WHERE id = :uid"), {"uid": user_id})
                await session.commit()
            shutil.rmtree(settings.upload_path / str(user_id), ignore_errors=True)


@pytest.mark.asyncio
async def test_failure_status_returns_plain_english_message_without_stack_trace(
    client: AsyncClient,
):
    """
    Verify /documents/{id}/status maps raw Job.error_message exceptions into plain-English
    user messages without leaking tracebacks, SQL, or file paths.
    """
    from app.services.job_service import format_user_failure_message

    msg_503 = format_user_failure_message(
        "LLM rate limits exhausted after 5 attempts: 503 UNAVAILABLE"
    )
    assert "high demand" in msg_503
    assert "gemini" not in msg_503.lower()
    assert "google" not in msg_503.lower()
    assert "503" not in msg_503

    msg_daily = format_user_failure_message("Daily Gemini quota reached 429")
    assert "daily" in msg_daily.lower()
    assert "gemini" not in msg_daily.lower()
    assert "google" not in msg_daily.lower()

    assert "safety call limit" in format_user_failure_message(
        "Call budget exceeded for document '123'"
    )
    assert "time limit" in format_user_failure_message("504 Gateway Timeout timed out")
    assert "restarted" in format_user_failure_message(None, status="interrupted")

    generic = format_user_failure_message(
        "Traceback (most recent call last): File '/app/secret.py' SQL ERROR"
    )
    assert "Traceback" not in generic
    assert "/app/secret.py" not in generic
    assert "SQL" not in generic

    email = f"fail_msg_{uuid.uuid4().hex[:8]}@example.com"
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "Password123!", "full_name": "Fail Msg User"},
    )
    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "Password123!"},
    )
    token = login_res.json()["data"]["access_token"]
    header = {"Authorization": f"Bearer {token}"}

    pdf_bytes = _build_legal_pdf(num_clauses=4)
    up = await client.post(
        "/api/v1/documents",
        headers=header,
        files={"file": ("fail_msg_doc.pdf", pdf_bytes, "application/pdf")},
    )
    assert up.status_code == 201
    doc_id = uuid.UUID(up.json()["data"]["id"])

    async with async_session_factory() as session:
        await session.execute(
            text("UPDATE documents SET status = 'failed' WHERE id = :did"),
            {"did": doc_id},
        )
        await session.execute(
            text(
                "UPDATE jobs SET status = 'failed', stage = 'failed', "
                "error_message = '503 UNAVAILABLE: model experiencing high demand' "
                "WHERE document_id = :did"
            ),
            {"did": doc_id},
        )
        await session.commit()

    st_res = await client.get(f"/api/v1/documents/{doc_id}/status", headers=header)
    assert st_res.status_code == 200
    msg = st_res.json()["data"]["message"]
    assert msg is not None
    assert "high demand" in msg
    assert "gemini" not in msg.lower()
    assert "google" not in msg.lower()
    assert "Retry Analysis" in msg

    del_res = await client.delete(f"/api/v1/documents/{doc_id}", headers=header)
    assert del_res.status_code == 204
    await client.delete("/api/v1/auth/me", headers=header)


@pytest.mark.asyncio
async def test_pdf_and_markdown_export_renders_section_3_from_recommendations(
    client: AsyncClient,
):
    """Verify PDF and Markdown exports render Section 3 from recommendations when top_risky_clauses is empty."""
    from app.services.export_service import ExportService

    email = f"export_sec3_{uuid.uuid4().hex[:8]}@example.com"
    reg_res = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "Password123!", "full_name": "Export Sec3"},
    )
    user_id = uuid.UUID(reg_res.json()["data"]["id"])
    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "Password123!"},
    )
    header = {"Authorization": f"Bearer {login_res.json()['data']['access_token']}"}

    pdf_bytes = _build_legal_pdf(num_clauses=3)
    up = await client.post(
        "/api/v1/documents",
        headers=header,
        files={"file": ("sec3_export.pdf", pdf_bytes, "application/pdf")},
    )
    doc_id = uuid.UUID(up.json()["data"]["id"])

    async with async_session_factory() as session:
        session.add(
            DocumentAnalysis(
                document_id=doc_id,
                overall_risk_score=55,
                overall_summary="Executive summary.",
                top_risky_clauses=[],
                recommendations=["Add written consent cap before asset sale."],
                risk_distribution={},
            )
        )
        await session.commit()

        exp = ExportService(session)
        md_text = await exp.export_markdown(doc_id, user_id)
        pdf_out = await exp.export_pdf(doc_id, user_id)

    assert "## 3. Top Negotiation Priorities" in md_text
    assert "Add written consent cap before asset sale." in md_text
    assert "## 4. Clause-by-Clause Risk Analysis" in md_text

    parsed = fitz.open(stream=pdf_out, filetype="pdf")
    full_pdf_text = "\n".join(p.get_text() for p in parsed)
    parsed.close()
    assert "3. Top Negotiation Priorities" in full_pdf_text
    assert "Add written consent cap before asset sale." in full_pdf_text
    assert "4. Clause-by-Clause Risk Analysis" in full_pdf_text

    await client.delete(f"/api/v1/documents/{doc_id}", headers=header)
    await client.delete("/api/v1/auth/me", headers=header)
