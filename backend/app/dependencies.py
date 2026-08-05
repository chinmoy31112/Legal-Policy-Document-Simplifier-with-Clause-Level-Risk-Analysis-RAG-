"""
Application-level dependency injection.

Provides database session, service instances, and other shared dependencies
to FastAPI route handlers via Depends().
"""

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_factory


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Yield an async database session.

    The session is committed/rolled back and closed automatically.
    Use in route handlers via Depends(get_db_session).
    """
    async with async_session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
