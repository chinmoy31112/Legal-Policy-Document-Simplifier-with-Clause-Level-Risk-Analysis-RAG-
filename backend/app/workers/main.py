"""
ARQ Background Worker entrypoint for async job processing.

Phase 1 baseline worker configuration. Handles lifecycle and connects to Redis.
Domain task implementations are wired in their respective owner phases.
"""

from typing import Any

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


async def process_document_job(ctx: dict[str, Any], document_id: str) -> dict[str, Any]:
    """ARQ background job executing document processing pipeline."""
    from uuid import UUID

    from app.core.database import async_session_factory
    from app.services.analysis_service import AnalysisService

    doc_uuid = UUID(document_id)
    logger.info("arq_process_document_started", document_id=document_id)
    async with async_session_factory() as session:
        service = AnalysisService(session)
        await service._run_analysis_task(doc_uuid)
    logger.info("arq_process_document_completed", document_id=document_id)
    return {"document_id": document_id, "status": "completed"}


async def startup(ctx: dict[str, Any]) -> None:
    """Worker startup hook."""
    logger.info("worker_starting", redis_url=settings.redis_url)


async def shutdown(ctx: dict[str, Any]) -> None:
    """Worker shutdown hook."""
    logger.info("worker_shutting_down")


class WorkerSettings(WorkerSettingsBase):
    """ARQ Worker configuration settings."""

    functions = [ping_task, process_document_job]  # type: ignore[assignment]
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
