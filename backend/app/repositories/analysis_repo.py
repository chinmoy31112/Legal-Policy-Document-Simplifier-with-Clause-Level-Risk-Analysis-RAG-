"""
Analysis repositories for data access to AnalysisResult and DocumentAnalysis models.
"""

from typing import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.analysis import AnalysisResult, DocumentAnalysis
from app.repositories.base import BaseRepository


class AnalysisResultRepository(BaseRepository[AnalysisResult]):
    """Repository for Clause-level AnalysisResult CRUD operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(AnalysisResult, session)

    async def get_by_document(self, document_id: UUID) -> Sequence[AnalysisResult]:
        """Get all clause analysis results for a document."""
        # Using a join with Clause to filter by document_id
        from app.models.clause import Clause
        
        query = (
            select(AnalysisResult)
            .options(selectinload(AnalysisResult.clause))
            .join(Clause, AnalysisResult.clause_id == Clause.id)
            .where(Clause.document_id == document_id)
            .order_by(Clause.clause_index.asc())
        )
        result = await self.session.execute(query)
        return result.scalars().all()

    async def bulk_create(self, results: list[AnalysisResult]) -> None:
        """Create multiple analysis results in a single operation."""
        self.session.add_all(results)
        await self.session.flush()


class DocumentAnalysisRepository(BaseRepository[DocumentAnalysis]):
    """Repository for DocumentAnalysis CRUD operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(DocumentAnalysis, session)

    async def get_by_document(self, document_id: UUID) -> DocumentAnalysis | None:
        """Get the overall document analysis for a document."""
        query = select(DocumentAnalysis).where(DocumentAnalysis.document_id == document_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
