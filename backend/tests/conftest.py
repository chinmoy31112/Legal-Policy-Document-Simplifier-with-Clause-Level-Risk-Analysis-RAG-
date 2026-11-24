"""Test configuration and shared fixtures."""

import sys
from collections.abc import AsyncGenerator
from pathlib import Path

import pytest_asyncio
from httpx import ASGITransport, AsyncClient

# Ensure backend root is on sys.path
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.database import engine
from app.main import create_app

fastapi_app = create_app()


@pytest_asyncio.fixture
async def cleanup_database_pool():
    """Dispose connection pool after each test to prevent cross-event-loop connection reuse."""
    yield
    try:
        import asyncio
        if hasattr(engine, "pool") and (engine.pool.checkedin() + engine.pool.checkedout() > 0):
            await asyncio.wait_for(engine.dispose(), timeout=1.0)
    except Exception:
        pass


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """Create an async test client for the FastAPI app."""
    transport = ASGITransport(app=fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test", follow_redirects=True) as ac:
        yield ac
