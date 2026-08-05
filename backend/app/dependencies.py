"""
Application-level dependency injection.

Provides FastAPI dependencies for database sessions, services,
authentication, and AI components.
"""

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings, Settings
from app.core.database import async_session_factory


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield a database session, ensuring it is closed after use."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


def get_config() -> Settings:
    """Return the application settings singleton."""
    return get_settings()
