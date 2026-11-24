"""
Analysis API endpoints.

Retrieve clause-level risk analyses and overall document summaries.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_user_id
from app.dependencies import get_db_session
from app.schemas.analysis import ClauseAnalysisResponse, DocumentAnalysisResponse
from app.schemas.common import APIResponse
from app.services.analysis_service import AnalysisService
from app.services.document_service import DocumentService

router = APIRouter()


@router.get(
    "/{document_id}/summary",
    response_model=APIResponse[DocumentAnalysisResponse],
    summary="Get document analysis summary",
    description="Retrieve the overall risk analysis and summary for a document.",
)
async def get_document_summary(
    document_id: UUID,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
):
    """Get the overall document analysis summary."""
    doc_service = DocumentService(session)
    await doc_service.get_document(document_id, user_id)

    service = AnalysisService(session)
    analysis = await service.get_document_analysis(document_id)
    return APIResponse(data=DocumentAnalysisResponse.model_validate(analysis))


@router.get(
    "/{document_id}/clauses",
    response_model=APIResponse[list[ClauseAnalysisResponse]],
    summary="Get clause analyses",
    description="Retrieve the risk analysis results for all clauses in a document.",
)
async def get_clause_analyses(
    document_id: UUID,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
):
    """Get all clause analyses for a document."""
    doc_service = DocumentService(session)
    await doc_service.get_document(document_id, user_id)

    service = AnalysisService(session)
    analyses = await service.get_clause_analyses(document_id)
    return APIResponse(data=[ClauseAnalysisResponse.model_validate(a) for a in analyses])
