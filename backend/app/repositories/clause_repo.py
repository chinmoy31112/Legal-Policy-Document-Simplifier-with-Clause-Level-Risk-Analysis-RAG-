"""
Clause repository — data access layer for Clause model.
"""

from typing import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.clause import Clause
from app.repositories.base import BaseRepository


class ClauseRepository(BaseRepository[Clause]):
    """Repository for Clause CRUD operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(Clause, session)

    async def get_by_document(self, document_id: UUID) -> Sequence[Clause]:
        """Get all clauses for a specific document, ordered by index."""
        query = (
            select(Clause)
            .where(Clause.document_id == document_id)
            .order_by(Clause.clause_index.asc())
            .options(selectinload(Clause.analysis_result))
        )
        result = await self.session.execute(query)
        return result.scalars().all()

    async def bulk_create(self, clauses: list[Clause]) -> None:
        """Create multiple clauses in a single operation."""
        self.session.add_all(clauses)
        await self.session.flush()
