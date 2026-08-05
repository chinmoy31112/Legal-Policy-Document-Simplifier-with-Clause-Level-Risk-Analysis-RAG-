"""
Base repository with generic async CRUD operations.

Provides a reusable base class for all data access repositories.
"""

from typing import Any, Generic, Sequence, Type, TypeVar
from uuid import UUID

from sqlalchemy import func, select, delete as sa_delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import Base

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    """Generic async CRUD repository."""

    def __init__(self, model: Type[ModelT], session: AsyncSession):
        self.model = model
        self.session = session

    async def get_by_id(self, id: UUID) -> ModelT | None:
        """Get a record by primary key."""
        return await self.session.get(self.model, id)

    async def get_all(
        self,
        offset: int = 0,
        limit: int = 20,
        **filters: Any,
    ) -> tuple[Sequence[ModelT], int]:
        """
        Get paginated records with optional filters.

        Returns:
            Tuple of (items, total_count).
        """
        query = select(self.model)
        count_query = select(func.count()).select_from(self.model)

        for key, value in filters.items():
            if value is not None and hasattr(self.model, key):
                query = query.where(getattr(self.model, key) == value)
                count_query = count_query.where(getattr(self.model, key) == value)

        # Get total count
        total_result = await self.session.execute(count_query)
        total = total_result.scalar() or 0

        # Get paginated items
        query = query.offset(offset).limit(limit).order_by(
            self.model.created_at.desc()
        )
        result = await self.session.execute(query)
        items = result.scalars().all()

        return items, total

    async def create(self, **kwargs: Any) -> ModelT:
        """Create a new record."""
        instance = self.model(**kwargs)
        self.session.add(instance)
        await self.session.flush()
        await self.session.refresh(instance)
        return instance

    async def update(self, id: UUID, **kwargs: Any) -> ModelT | None:
        """Update an existing record by ID."""
        instance = await self.get_by_id(id)
        if instance is None:
            return None
        for key, value in kwargs.items():
            if hasattr(instance, key):
                setattr(instance, key, value)
        await self.session.flush()
        await self.session.refresh(instance)
        return instance

    async def delete(self, id: UUID) -> bool:
        """Delete a record by ID."""
        instance = await self.get_by_id(id)
        if instance is None:
            return False
        await self.session.delete(instance)
        await self.session.flush()
        return True
