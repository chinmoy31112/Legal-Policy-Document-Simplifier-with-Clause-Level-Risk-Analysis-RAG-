"""
Job management service coordinating persistent Postgres jobs and ARQ Redis worker queue.

Handles:
- Persistent job creation & ARQ enqueueing (outside API request process)
- Document & account cancellation (DB + Redis flags, abort running ARQ job, remove queued work, wait up to 5s)
- Startup recovery (marking interrupted jobs left 'running')
- Periodic orphan job reaper (removing jobs/queued tasks whose document or user no longer exists)
"""

from __future__ import annotations

import asyncio
import json
import time
import uuid
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from redis import asyncio as aioredis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cancellation import (
    _cancelled_acks,
    acknowledge_cancelled,
    clear_cancelled,
    mark_cancelled,
)
from app.core.config import get_settings
from app.core.logging import get_logger
from app.models.document import Document
from app.models.job import Job
from app.repositories.job_repo import JobRepository

logger = get_logger(__name__)

# In-process task registry kept strictly for cooperative cancellation if a worker/test holds an asyncio.Task
_active_worker_tasks: dict[str, asyncio.Task[Any]] = {}


def register_active_worker_task(document_id: str | UUID, task: asyncio.Task[Any]) -> None:
    _active_worker_tasks[str(document_id)] = task


def unregister_active_worker_task(document_id: str | UUID) -> None:
    _active_worker_tasks.pop(str(document_id), None)


async def _get_arq_pool() -> Any | None:
    """Create a short-lived ARQ Redis connection pool, returning None if Redis is unavailable."""
    try:
        from arq import create_pool
        from arq.connections import RedisSettings

        settings = get_settings()
        redis_settings = RedisSettings.from_dsn(settings.redis_url)
        redis_settings.conn_timeout = 1
        pool = await asyncio.wait_for(create_pool(redis_settings), timeout=1.5)
        return pool
    except Exception as exc:
        logger.warning("arq_redis_pool_unavailable", error=str(exc))
        return None


async def _remove_queued_arq_job(arq_job_id: str | None) -> bool:
    """Remove queued job from ARQ Redis queue (`arq:queue`) and signal abort if active."""
    if not arq_job_id:
        return False
    settings = get_settings()
    redis_client: aioredis.Redis | None = None
    removed = False
    try:
        redis_client = aioredis.from_url(
            settings.redis_url,
            socket_connect_timeout=1.0,
            socket_timeout=1.0,
        )
        await redis_client.ping()
        # 1. Remove from pending ARQ sorted-set queue so worker never picks it up
        zrem_count = await redis_client.zrem("arq:queue", arq_job_id)
        if zrem_count:
            removed = True
        # 2. Write ARQ abort signal (`arq:abort:{job_id}`) + delete job payload
        await redis_client.set(f"arq:abort:{arq_job_id}", "1", ex=3600)
        await redis_client.delete(f"arq:job:{arq_job_id}")
    except Exception as exc:
        logger.debug("arq_queue_cleanup_skipped", arq_job_id=arq_job_id, error=str(exc))
    finally:
        if redis_client is not None:
            try:
                await redis_client.aclose()
            except Exception:
                pass
    return removed


class JobService:
    """Coordinates persistent Job records, ARQ enqueueing, cancellation, recovery, and reaping."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.job_repo = JobRepository(session)

    async def enqueue_document_analysis(
        self,
        document_id: UUID,
        user_id: UUID,
    ) -> Job:
        """
        Create a persistent Job row (`status="queued"`) and enqueue work onto the ARQ Redis worker queue.
        Never executes analysis inside the API server process.
        """
        await clear_cancelled(document_id=document_id)

        job_uuid = uuid.uuid4()
        arq_job_id = f"doc_analysis:{job_uuid}"

        job = Job(
            id=job_uuid,
            document_id=document_id,
            user_id=user_id,
            arq_job_id=arq_job_id,
            status="queued",
            stage="queued",
            cancel_requested=False,
        )
        self.session.add(job)
        await self.session.commit()
        await self.session.refresh(job)

        pool = await _get_arq_pool()
        if pool is not None:
            try:
                await pool.enqueue_job(
                    "process_document_job",
                    str(document_id),
                    str(job.id),
                    _job_id=arq_job_id,
                )
                logger.info(
                    "analysis_job_enqueued_arq",
                    job_id=str(job.id),
                    document_id=str(document_id),
                    arq_job_id=arq_job_id,
                )
            except Exception as exc:
                logger.warning(
                    "analysis_job_arq_enqueue_failed",
                    job_id=str(job.id),
                    document_id=str(document_id),
                    error=str(exc),
                )
            finally:
                try:
                    await pool.aclose()
                except Exception:
                    pass
        else:
            logger.warning(
                "analysis_job_queued_in_db_redis_unavailable",
                job_id=str(job.id),
                document_id=str(document_id),
            )

        return job

    async def _is_job_stopped(
        self,
        document_id: UUID,
        job_ids: list[UUID],
    ) -> bool:
        """Check DB, Redis ack, and in-process task completion to confirm worker has stopped."""
        doc_str = str(document_id)
        # Check in-process active tasks (both job_service and documents router registry)
        t = _active_worker_tasks.get(doc_str)
        if t is not None and not t.done():
            return False

        # Check Redis ack flag
        settings = get_settings()
        redis_client: aioredis.Redis | None = None
        try:
            redis_client = aioredis.from_url(
                settings.redis_url,
                decode_responses=True,
                socket_connect_timeout=0.3,
                socket_timeout=0.3,
            )
            ack_val = await redis_client.get(f"job:ack:{doc_str}")
            if ack_val == "1":
                return True
        except Exception:
            pass
        finally:
            if redis_client is not None:
                try:
                    await redis_client.aclose()
                except Exception:
                    pass

        if doc_str in _cancelled_acks:
            return True

        # Check DB status for non-queued active jobs
        res = await self.session.execute(select(Job.status).where(Job.document_id == document_id))
        statuses = [row[0] for row in res.fetchall()]
        if not any(st in ("running", "cancelling") for st in statuses):
            return True

        return False

    async def cancel_document_jobs(
        self,
        document_id: UUID,
        timeout_seconds: float = 5.0,
        legacy_tasks_map: dict[UUID, asyncio.Task[Any]] | None = None,
    ) -> dict[str, Any]:
        """
        Part C.2:
        1. Set cancel flag in Redis + in-memory first for immediate worker wakeup, and in DB (`cancel_requested=True, status='cancelling'`).
        2. Cancel any running task & abort ARQ job.
        3. Remove queued work from Redis ARQ queue.
        4. Wait up to 5s for confirmation that running work stopped.
        """
        # Set Redis + in-memory flags FIRST so any in-flight worker loop breaks out immediately
        await mark_cancelled(document_id=document_id)
        try:
            from app.core.sse import broadcast_event

            broadcast_event(
                str(document_id),
                "cancelling",
                {"status": "cancelling", "job_status": "cancelling", "stage": "cancelling"},
            )
        except Exception:
            pass

        active_jobs = await self.job_repo.mark_cancelling_for_document(document_id)
        had_running_job = any(j.status == "running" for j in active_jobs)

        doc_res = await self.session.execute(select(Document).where(Document.id == document_id))
        doc = doc_res.scalar_one_or_none()
        if doc and doc.status in (
            "uploaded",
            "extracting",
            "segmenting",
            "analyzing",
            "waiting for quota",
        ):
            doc.status = "cancelling"

        await self.session.commit()

        for j in active_jobs:
            await mark_cancelled(job_id=j.id)
            if j.status == "queued":
                removed = await _remove_queued_arq_job(j.arq_job_id)
                if removed or not had_running_job:
                    j.status = "cancelled"
                    j.stage = "cancelled"
                    j.completed_at = datetime.now(UTC).replace(tzinfo=None)
            elif j.arq_job_id:
                await _remove_queued_arq_job(j.arq_job_id)

        await self.session.commit()

        # Cancel in-process task handles if present
        tasks_to_await: list[asyncio.Task[Any]] = []
        w_task = _active_worker_tasks.get(str(document_id))
        if w_task and not w_task.done():
            w_task.cancel()
            tasks_to_await.append(w_task)
            had_running_job = True

        if legacy_tasks_map is not None:
            l_task = legacy_tasks_map.pop(document_id, None)
            if l_task and not l_task.done():
                l_task.cancel()
                tasks_to_await.append(l_task)
                had_running_job = True

        # Wait up to timeout_seconds (5s default) for confirmation if any job was running
        confirmed = not had_running_job
        if tasks_to_await:
            try:
                await asyncio.wait_for(
                    asyncio.gather(*tasks_to_await, return_exceptions=True),
                    timeout=timeout_seconds,
                )
                confirmed = True
                await acknowledge_cancelled(document_id=document_id)
            except TimeoutError:
                logger.warning(
                    "cancel_document_task_wait_timed_out",
                    document_id=str(document_id),
                    timeout_seconds=timeout_seconds,
                )

        if not confirmed:
            deadline = time.monotonic() + timeout_seconds
            job_ids = [j.id for j in active_jobs]
            while time.monotonic() < deadline:
                # Re-query fresh DB state in a separate check via expire_all
                self.session.expire_all()
                if await self._is_job_stopped(document_id, job_ids):
                    confirmed = True
                    break
                await asyncio.sleep(0.1)

        if active_jobs and not confirmed:
            logger.warning(
                "cancel_confirmation_timeout_proceeding_cleanup",
                document_id=str(document_id),
                job_count=len(active_jobs),
            )

        return {
            "document_id": str(document_id),
            "cancelled_jobs_count": len(active_jobs),
            "had_running_job": had_running_job,
            "confirmed_stopped": confirmed,
        }

    async def cancel_user_jobs(
        self,
        user_id: UUID,
        timeout_seconds: float = 5.0,
        legacy_tasks_map: dict[UUID, asyncio.Task[Any]] | None = None,
    ) -> dict[str, Any]:
        """Cancel all queued/running jobs belonging to a user before account deletion."""
        await mark_cancelled(user_id=user_id)
        active_jobs = await self.job_repo.mark_cancelling_for_user(user_id)

        # Collect all user document IDs (including jobs and active docs)
        doc_res = await self.session.execute(select(Document.id).where(Document.user_id == user_id))
        doc_ids = {row[0] for row in doc_res.fetchall()}
        for j in active_jobs:
            if j.document_id:
                doc_ids.add(j.document_id)

        await self.session.commit()

        results = []
        for doc_id in doc_ids:
            res = await self.cancel_document_jobs(
                doc_id,
                timeout_seconds=timeout_seconds,
                legacy_tasks_map=legacy_tasks_map,
            )
            results.append(res)

        return {
            "user_id": str(user_id),
            "documents_cancelled": len(doc_ids),
            "jobs_cancelled": len(active_jobs),
            "details": results,
        }

    async def mark_interrupted_on_startup(self) -> int:
        """Mark any jobs left in 'running' state as 'interrupted' on startup."""
        count = await self.job_repo.mark_interrupted_on_startup()
        await self.session.commit()
        if count > 0:
            logger.warning("startup_marked_interrupted_jobs", count=count)
        return count

    async def reap_orphan_jobs(self) -> dict[str, int]:
        """
        Periodic reaper: clean up jobs in DB and queued ARQ items in Redis whose
        document or user no longer exists.
        """
        orphans = await self.job_repo.find_orphan_jobs()
        db_reaped = 0
        for job in orphans:
            await mark_cancelled(document_id=job.document_id, job_id=job.id, user_id=job.user_id)
            await _remove_queued_arq_job(job.arq_job_id)
            await self.session.delete(job)
            db_reaped += 1

        if db_reaped:
            await self.session.commit()
            logger.info("reaper_purged_orphan_db_jobs", count=db_reaped)

        # Also inspect pending Redis ARQ queue items for deleted documents
        redis_reaped = 0
        settings = get_settings()
        redis_client: aioredis.Redis | None = None
        try:
            redis_client = aioredis.from_url(
                settings.redis_url,
                socket_connect_timeout=0.5,
                socket_timeout=0.5,
            )
            queued_ids = await redis_client.zrange("arq:queue", 0, -1)
            for raw_jid in queued_ids:
                jid = raw_jid.decode("utf-8") if isinstance(raw_jid, bytes) else str(raw_jid)
                payload_raw = await redis_client.get(f"arq:job:{jid}")
                if not payload_raw:
                    continue
                # Extract first arg (document_id) cleanly if inspectable JSON/pickle
                doc_uuid: UUID | None = None
                try:
                    if isinstance(payload_raw, bytes) and payload_raw.startswith(b"{"):
                        parsed = json.loads(payload_raw.decode("utf-8"))
                        args = parsed.get("a") or []
                        if args:
                            doc_uuid = UUID(str(args[0]))
                except Exception:
                    pass
                if doc_uuid is not None:
                    exists_res = await self.session.execute(
                        select(Document.id).where(Document.id == doc_uuid)
                    )
                    if exists_res.scalar_one_or_none() is None:
                        await redis_client.zrem("arq:queue", jid)
                        await redis_client.set(f"arq:abort:{jid}", "1", ex=3600)
                        await redis_client.delete(f"arq:job:{jid}")
                        redis_reaped += 1
        except Exception:
            pass
        finally:
            if redis_client is not None:
                try:
                    await redis_client.aclose()
                except Exception:
                    pass

        return {"db_orphans_reaped": db_reaped, "redis_orphans_reaped": redis_reaped}

    async def resume_waiting_for_quota_jobs(self) -> int:
        """
        Automatically re-enqueue jobs paused in `waiting_for_quota` once the shared
        quota-exhausted flag expires at the daily UTC reset or clears.
        """
        from app.ai.rate_limiter import get_model_rate_limiter

        settings = get_settings()
        models_to_check = {
            settings.gemini_clause_model,
            settings.gemini_summary_model,
            settings.gemini_embedding_model,
        }
        for model_name in models_to_check:
            limiter = get_model_rate_limiter(model_name)
            if await limiter.is_daily_quota_exhausted_async():
                return 0

        waiting_jobs = await self.job_repo.find_waiting_quota_jobs()
        if not waiting_jobs:
            return 0

        pool = await _get_arq_pool()
        resumed = 0
        now = datetime.now(UTC).replace(tzinfo=None)
        try:
            for job in waiting_jobs:
                if job.document_id is None:
                    continue
                new_arq_id = f"doc_analysis:{job.id}:{int(time.time())}"
                job.status = "queued"
                job.stage = "queued"
                job.arq_job_id = new_arq_id
                job.error_message = None
                job.updated_at = now

                doc_res = await self.session.execute(
                    select(Document).where(Document.id == job.document_id)
                )
                doc = doc_res.scalar_one_or_none()
                if doc is not None:
                    doc.status = "uploaded"

                await self.session.commit()

                if pool is not None:
                    try:
                        await pool.enqueue_job(
                            "process_document_job",
                            str(job.document_id),
                            str(job.id),
                            _job_id=new_arq_id,
                        )
                    except Exception as exc:
                        logger.warning(
                            "waiting_quota_auto_resume_enqueue_failed",
                            job_id=str(job.id),
                            document_id=str(job.document_id),
                            error=str(exc),
                        )

                try:
                    from app.core.sse import broadcast_event

                    broadcast_event(
                        str(job.document_id),
                        "status",
                        {
                            "status": "queued",
                            "job_status": "queued",
                            "stage": "queued",
                            "total_clauses": job.total_clauses,
                            "analyzed_clauses": job.completed_clauses,
                        },
                    )
                except Exception:
                    pass

                resumed += 1
        finally:
            if pool is not None:
                try:
                    await pool.aclose()
                except Exception:
                    pass

        if resumed > 0:
            logger.info("waiting_quota_jobs_auto_resumed", count=resumed)
        return resumed


def format_user_failure_message(raw_error: str | None, status: str = "failed") -> str:
    """
    Map internal worker/LLM exception strings to plain-English explanations safe for end users.
    Never exposes tracebacks, file paths, SQL queries, or internal keys.
    """
    lower = (raw_error or "").lower()
    norm_status = (status or "").strip().lower().replace("_", " ")

    if norm_status == "interrupted" or "interrupted by server or worker restart" in lower:
        return (
            "Analysis was interrupted when the background worker restarted. "
            "Any completed clauses are saved — click Retry Analysis to continue."
        )
    if (
        "503" in lower
        or "unavailable" in lower
        or "high demand" in lower
        or "rate limits exhausted" in lower
    ):
        return (
            "The AI service is temporarily experiencing high demand and automatic retries were exhausted. "
            "Your completed clauses remain saved — please click Retry Analysis in a few moments."
        )
    if "monthly" in lower and "quota" in lower:
        return (
            "Your monthly clause analysis limit has been reached. "
            "Please delete unused documents or raise your quota before retrying."
        )
    if "call budget exceeded" in lower:
        return (
            "Analysis stopped automatically after reaching the per-document safety call limit "
            "to protect against excess quota usage. Saved clauses remain intact — please click Retry Analysis."
        )
    if "daily" in lower and ("quota" in lower or "429" in lower):
        return (
            "The daily AI service quota was reached before analysis could finish. "
            "Completed clauses remain saved — click Retry Analysis after quota resets."
        )
    if "429" in lower or "resource_exhausted" in lower or "rate limit" in lower:
        return (
            "The AI service hit a temporary request-rate limit. "
            "Completed clauses remain saved — please wait a minute and click Retry Analysis."
        )
    if "timeout" in lower or "timed out" in lower or "504" in lower:
        return (
            "Analysis took longer than the worker time limit for this document. "
            "Your completed clauses are saved — click Retry Analysis to finish the remaining clauses."
        )
    if any(
        term in lower
        for term in ("no clauses extracted", "scanned", "encrypt", "corrupt", "empty file")
    ):
        return (
            "We couldn't extract readable contract text from this file "
            "(it may be a scanned image, empty, or password-protected PDF). "
            "Please upload a text-based PDF or DOCX file."
        )
    return (
        "Analysis could not be completed cleanly due to an unexpected processing error. "
        "Any completed clauses remain safely saved — please click Retry Analysis."
    )
