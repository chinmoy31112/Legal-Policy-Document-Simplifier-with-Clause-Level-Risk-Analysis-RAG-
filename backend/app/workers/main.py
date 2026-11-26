"""
ARQ Background Worker entrypoint for async job processing.

Phase 1 baseline worker configuration. Handles lifecycle and connects to Redis.
Domain task implementations are wired in their respective owner phases.
"""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from arq import cron
from arq.connections import RedisSettings
from arq.typing import WorkerSettingsBase
from arq.worker import run_worker as arq_run_worker

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()


async def ping_task(ctx: dict[str, Any], word: str = "pong") -> str:
    """Baseline test task for worker verification."""
    logger.info("worker_task_executed", task="ping_task", word=word)
    return f"echo: {word}"


async def process_document_job(
    ctx: dict[str, Any],
    document_id: str,
    job_id_str: str | None = None,
) -> dict[str, Any]:
    """ARQ background job executing document processing pipeline with cooperative cancellation."""
    import asyncio

    from app.core.cancellation import acknowledge_cancelled, is_cancelled
    from app.core.database import async_session_factory
    from app.services.analysis_service import AnalysisService
    from app.services.job_service import (
        register_active_worker_task,
        unregister_active_worker_task,
    )

    doc_uuid = UUID(document_id)
    job_uuid = UUID(job_id_str) if job_id_str else None
    current_task = asyncio.current_task()
    if current_task:
        register_active_worker_task(doc_uuid, current_task)

    logger.info("arq_process_document_started", document_id=document_id, job_id=job_id_str)
    try:
        if await is_cancelled(document_id=doc_uuid, job_id=job_uuid):
            logger.info(
                "arq_job_cancelled_before_start", document_id=document_id, job_id=job_id_str
            )
            await acknowledge_cancelled(document_id=doc_uuid, job_id=job_uuid)
            return {"document_id": document_id, "job_id": job_id_str, "status": "cancelled"}

        async with async_session_factory() as session:
            service = AnalysisService(session)
            await service._run_analysis_task(doc_uuid, job_id=job_uuid)

        logger.info("arq_process_document_completed", document_id=document_id, job_id=job_id_str)
        return {"document_id": document_id, "job_id": job_id_str, "status": "completed"}
    except asyncio.CancelledError:
        logger.info("arq_process_document_cancelled", document_id=document_id, job_id=job_id_str)
        await acknowledge_cancelled(document_id=doc_uuid, job_id=job_uuid)
        raise
    finally:
        unregister_active_worker_task(doc_uuid)


async def reap_orphan_jobs_task(ctx: dict[str, Any]) -> dict[str, int]:
    """Periodic worker task reaping jobs whose document or user no longer exists."""
    from app.core.database import async_session_factory
    from app.services.job_service import JobService

    async with async_session_factory() as session:
        service = JobService(session)
        return await service.reap_orphan_jobs()


async def resume_waiting_quota_jobs_task(ctx: dict[str, Any]) -> int:
    """Periodic worker task restarting `waiting_for_quota` jobs after daily reset."""
    from app.core.database import async_session_factory
    from app.services.job_service import JobService

    async with async_session_factory() as session:
        service = JobService(session)
        return await service.resume_waiting_for_quota_jobs()


async def startup(ctx: dict[str, Any]) -> None:
    """Worker startup hook: mark jobs left 'running' as interrupted and reap orphans."""
    from app.core.database import async_session_factory
    from app.services.job_service import JobService

    logger.info(
        "worker_starting", redis_url=settings.redis_url, started_at=datetime.now(UTC).isoformat()
    )
    try:
        async with async_session_factory() as session:
            job_service = JobService(session)
            interrupted_count = await job_service.mark_interrupted_on_startup()
            reap_res = await job_service.reap_orphan_jobs()
            logger.info(
                "worker_startup_recovery_complete",
                interrupted_jobs=interrupted_count,
                reaped=reap_res,
            )
    except Exception as exc:
        logger.warning("worker_startup_recovery_skipped", error=str(exc))


async def shutdown(ctx: dict[str, Any]) -> None:
    """Worker shutdown hook."""
    logger.info("worker_shutting_down")


class WorkerSettings(WorkerSettingsBase):
    """ARQ Worker configuration settings."""

    functions = [
        ping_task,
        process_document_job,
        reap_orphan_jobs_task,
        resume_waiting_quota_jobs_task,
    ]  # type: ignore[assignment]
    cron_jobs = [
        cron(reap_orphan_jobs_task, second={0, 15, 30, 45}),
        cron(resume_waiting_quota_jobs_task, second={10, 40}),
    ]  # type: ignore[assignment]
    on_startup = startup  # type: ignore[assignment]
    on_shutdown = shutdown  # type: ignore[assignment]
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
    max_jobs = 10
    job_timeout = settings.job_timeout_seconds


def main() -> None:
    """Run ARQ worker."""
    arq_run_worker(WorkerSettings)


if __name__ == "__main__":
    main()
