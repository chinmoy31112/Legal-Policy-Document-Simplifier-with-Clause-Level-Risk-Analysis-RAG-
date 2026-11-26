"""Test configuration and shared fixtures."""

import asyncio
import os
import sys
from collections.abc import AsyncGenerator
from pathlib import Path

# Force offline test mode so test execution NEVER consumes user's live Google API quota
os.environ["APP_ENV"] = "test"
os.environ["GOOGLE_API_KEY"] = ""

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

# Ensure backend root is on sys.path
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import app.models  # noqa: F401
from app.core.database import Base, engine
from app.main import create_app

fastapi_app = create_app()

_tables_initialized = False


@pytest_asyncio.fixture(autouse=True)
async def ensure_tables_exist():
    """Ensure database schema and tables exist before tests run."""
    global _tables_initialized
    if not _tables_initialized:
        try:

            async def _init():
                async with engine.begin() as conn:
                    try:
                        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
                    except Exception:
                        pass
                    await conn.run_sync(Base.metadata.create_all)

            await asyncio.wait_for(_init(), timeout=1.0)
            _tables_initialized = True
        except Exception:
            pass
    yield


@pytest.fixture(autouse=True)
def cleanup_database_and_redis():
    """Dispose connection pool and clear redis test cache/rate-limits between tests."""
    try:
        import redis

        from app.core.config import get_settings

        r = redis.from_url(get_settings().redis_url, socket_connect_timeout=0.1, socket_timeout=0.1)
        r.ping()
        keys = (
            r.keys("embedcache:*")
            + r.keys("ratelimit:*")
            + r.keys("user_quota:*")
            + r.keys("job:cancel:*")
            + r.keys("job:ack:*")
            + r.keys("aicache:*")
            + r.keys("arq:*")
        )
        if keys:
            r.delete(*keys)
    except Exception:
        pass
    yield
    try:
        if hasattr(engine, "sync_engine"):
            engine.sync_engine.dispose()
    except Exception:
        pass
    try:
        import redis

        from app.core.config import get_settings

        r = redis.from_url(get_settings().redis_url, socket_connect_timeout=0.1, socket_timeout=0.1)
        r.ping()
        keys = (
            r.keys("embedcache:*")
            + r.keys("ratelimit:*")
            + r.keys("user_quota:*")
            + r.keys("job:cancel:*")
            + r.keys("job:ack:*")
            + r.keys("aicache:*")
            + r.keys("arq:*")
        )
        if keys:
            r.delete(*keys)
    except Exception:
        pass


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """Create an async test client for the FastAPI app."""
    transport = ASGITransport(app=fastapi_app)
    async with AsyncClient(
        transport=transport, base_url="http://test", follow_redirects=True
    ) as ac:
        yield ac
