"""
Health and Readiness probes for Kubernetes / Docker / load-balancer monitoring.

Provides:
- Liveness (/api/v1/health and /health): Quick check that the HTTP process is responsive.
- Readiness (/api/v1/health/ready and /ready): Deep probe checking live PostgreSQL and Redis connectivity.
"""

import asyncio
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Response, status
from sqlalchemy import text

from app.core.config import get_settings
from app.core.database import async_session_factory
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()

router = APIRouter()


@router.get("", tags=["Health"])
@router.get("/", include_in_schema=False)
async def liveness_check() -> dict[str, Any]:
    """Liveness probe: verifies web server is alive."""
    return {
        "status": "healthy",
        "app": settings.app_name,
        "version": settings.app_version,
        "env": settings.app_env,
        "timestamp": datetime.now(UTC).isoformat(),
    }


@router.get("/ready", tags=["Health"])
async def readiness_check(response: Response) -> dict[str, Any]:
    """
    Readiness probe: verifies connectivity to PostgreSQL database and Redis job broker.
    Returns 503 if any core dependency fails or times out.
    """
    checks: dict[str, Any] = {
        "database": "unknown",
        "redis": "unknown",
        "status": "ready",
        "timestamp": datetime.now(UTC).isoformat(),
    }
    is_ready = True

    # 1. Probe PostgreSQL with a strict 2-second timeout
    try:
        async with asyncio.timeout(2.0):
            async with async_session_factory() as session:
                result = await session.execute(text("SELECT 1"))
                val = result.scalar()
                if val == 1:
                    checks["database"] = "connected"
                else:
                    checks["database"] = f"unexpected_result_{val}"
                    is_ready = False
    except Exception as exc:
        logger.warning("readiness_probe_db_unavailable", error=str(exc))
        checks["database"] = f"unavailable: {type(exc).__name__}"
        is_ready = False

    # 2. Probe Redis with a strict 1-second timeout
    try:
        import redis.asyncio as aioredis

        async with asyncio.timeout(1.0):
            r = aioredis.from_url(settings.redis_url, socket_connect_timeout=1)
            pong = await r.ping()
            await r.aclose()
            if pong:
                checks["redis"] = "connected"
            else:
                checks["redis"] = "no_pong"
                is_ready = False
    except Exception as exc:
        logger.warning("readiness_probe_redis_unavailable", error=str(exc))
        checks["redis"] = f"unavailable: {type(exc).__name__}"
        is_ready = False

    if not is_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        checks["status"] = "unhealthy"

    return checks
