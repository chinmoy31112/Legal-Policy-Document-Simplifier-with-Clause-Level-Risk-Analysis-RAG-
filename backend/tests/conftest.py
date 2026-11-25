"""Test configuration and shared fixtures."""

import sys
from collections.abc import AsyncGenerator
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

# Ensure backend root is on sys.path
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.database import engine
from app.main import create_app

fastapi_app = create_app()


@pytest.fixture(autouse=True)
def cleanup_database_and_redis():
    """Dispose connection pool and clear redis test cache/rate-limits between tests."""
    try:
        import redis

        from app.core.config import get_settings
        r = redis.from_url(get_settings().redis_url, socket_connect_timeout=0.5)
        keys = r.keys("embedcache:*") + r.keys("ratelimit:*") + r.keys("user_quota:*")
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
        r = redis.from_url(get_settings().redis_url, socket_connect_timeout=0.5)
        keys = r.keys("embedcache:*") + r.keys("ratelimit:*") + r.keys("user_quota:*")
        if keys:
            r.delete(*keys)
    except Exception:
        pass


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """Create an async test client for the FastAPI app."""
    transport = ASGITransport(app=fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test", follow_redirects=True) as ac:
        yield ac
