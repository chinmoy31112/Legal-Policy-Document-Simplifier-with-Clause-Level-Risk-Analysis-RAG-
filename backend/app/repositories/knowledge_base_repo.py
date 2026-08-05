"""
Knowledge base repository — data access layer for KB models.
"""

from typing import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.knowledge_base import KBDocument, KBClause
from app.repositories.base import BaseRepository


class KBDocumentRepository(BaseRepository[KBDocument]):
    """Repository for KBDocument CRUD operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(KBDocument, session)

    async def get_with_clauses(self, kb_document_id: UUID) -> KBDocument | None:
        """Get a KB document with its associated clauses eagerly loaded."""
        query = (
            select(KBDocument)
            .where(KBDocument.id == kb_document_id)
            .options(selectinload(KBDocument.clauses))
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_by_title(self, title: str) -> KBDocument | None:
        """Find a KB document by its title."""
        query = select(KBDocument).where(KBDocument.title == title)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()


class KBClauseRepository(BaseRepository[KBClause]):
    """Repository for KBClause CRUD operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(KBClause, session)

    async def get_by_document(self, kb_document_id: UUID) -> Sequence[KBClause]:
        """Get all clauses for a specific KB document."""
        query = select(KBClause).where(KBClause.kb_document_id == kb_document_id)
        result = await self.session.execute(query)
        return result.scalars().all()

    async def bulk_create(self, clauses: list[KBClause]) -> None:
        """Create multiple KB clauses in a single operation."""
        self.session.add_all(clauses)
        await self.session.flush()
