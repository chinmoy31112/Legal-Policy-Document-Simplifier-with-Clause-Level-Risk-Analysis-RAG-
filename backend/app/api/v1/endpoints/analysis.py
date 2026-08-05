"""
Analysis endpoints.

Handles triggering analysis, retrieving results, and streaming progress.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import StreamingResponse

from app.schemas.analysis import (
    AnalysisStatusResponse,
    ClauseAnalysisResponse,
    DocumentAnalysisResponse,
)
from app.schemas.common import APIResponse
from app.api.v1.deps import get_current_user_id

router = APIRouter()


@router.post(
    "/documents/{document_id}/analyze",
    response_model=APIResponse[AnalysisStatusResponse],
    status_code=status.HTTP_202_ACCEPTED,
    summary="Start document analysis",
    description=(
        "Trigger the full RAG analysis pipeline for a document. "
        "The analysis runs asynchronously. Use the status endpoint or SSE stream "
        "to monitor progress."
    ),
)
async def start_analysis(
    document_id: UUID,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
):
    """Start the RAG analysis pipeline for a document."""
    # Implementation in Phase 5
    pass


@router.get(
    "/documents/{document_id}/status",
    response_model=APIResponse[AnalysisStatusResponse],
    summary="Get analysis status",
    description="Check the current progress of document analysis.",
)
async def get_analysis_status(
    document_id: UUID,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
):
    """Get the current analysis status for a document."""
    # Implementation in Phase 5
    pass


@router.get(
    "/documents/{document_id}/stream",
    summary="Stream analysis progress",
    description="Server-Sent Events stream for real-time analysis progress updates.",
)
async def stream_analysis_progress(
    document_id: UUID,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
):
    """Stream analysis progress via Server-Sent Events."""
    # Implementation in Phase 5
    pass


@router.get(
    "/documents/{document_id}/results",
    response_model=APIResponse[DocumentAnalysisResponse],
    summary="Get document-level analysis",
    description="Retrieve the aggregate analysis results for an entire document.",
)
async def get_document_analysis(
    document_id: UUID,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
):
    """Get document-level aggregate analysis results."""
    # Implementation in Phase 5
    pass


@router.get(
    "/documents/{document_id}/clauses",
    response_model=APIResponse[list[ClauseAnalysisResponse]],
    summary="Get clause-level analysis",
    description="Retrieve analysis results for all clauses in a document.",
)
async def get_clause_analyses(
    document_id: UUID,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    risk_category: str | None = Query(default=None, description="Filter by risk category"),
    min_risk_score: int | None = Query(default=None, ge=0, le=100),
):
    """Get clause-level analysis results with optional filtering."""
    # Implementation in Phase 5
    pass


@router.get(
    "/clauses/{clause_id}",
    response_model=APIResponse[ClauseAnalysisResponse],
    summary="Get single clause analysis",
    description="Retrieve the detailed analysis for a specific clause.",
)
async def get_clause_analysis(
    clause_id: UUID,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
):
    """Get analysis results for a single clause."""
    # Implementation in Phase 5
    pass
