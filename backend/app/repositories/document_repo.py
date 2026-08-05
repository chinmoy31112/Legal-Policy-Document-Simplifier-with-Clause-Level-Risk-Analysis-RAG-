"""
Document repository — data access layer for Document model.
"""

from typing import Sequence
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document
from app.repositories.base import BaseRepository


class DocumentRepository(BaseRepository[Document]):
    """Repository for Document CRUD operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(Document, session)

    async def get_by_user(
        self,
        user_id: UUID,
        offset: int = 0,
        limit: int = 20,
        status_filter: str | None = None,
        document_type: str | None = None,
    ) -> tuple[Sequence[Document], int]:
        """Get paginated documents for a specific user with optional filters."""
        query = select(Document).where(Document.user_id == user_id)
        count_query = select(func.count()).select_from(Document).where(
            Document.user_id == user_id
        )

        if status_filter:
            query = query.where(Document.status == status_filter)
            count_query = count_query.where(Document.status == status_filter)

        if document_type:
            query = query.where(Document.document_type == document_type)
            count_query = count_query.where(Document.document_type == document_type)

        total_result = await self.session.execute(count_query)
        total = total_result.scalar() or 0

        query = query.offset(offset).limit(limit).order_by(
            Document.created_at.desc()
        )
        result = await self.session.execute(query)
        items = result.scalars().all()

        return items, total

    async def get_by_id_and_user(
        self, document_id: UUID, user_id: UUID
    ) -> Document | None:
        """Get a document by ID, scoped to a specific user."""
        query = select(Document).where(
            Document.id == document_id,
            Document.user_id == user_id,
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def update_status(self, document_id: UUID, status: str) -> Document | None:
        """Update a document's processing status."""
        return await self.update(document_id, status=status)
