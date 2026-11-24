"""
Export endpoints.

Handles exporting analysis results in JSON and Markdown formats.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_user_id
from app.dependencies import get_db_session
from app.services.export_service import ExportService

router = APIRouter()


@router.get(
    "/documents/{document_id}/json",
    summary="Export analysis as JSON",
    description="Download validated JSON risk analysis report.",
)
async def export_json(
    document_id: UUID,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
):
    """Export analysis results as JSON."""
    service = ExportService(session)
    data = await service.export_json(document_id, user_id)
    filename = f"{data['document']['filename']}_risk_analysis.json"
    return JSONResponse(
        content=data,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get(
    "/documents/{document_id}/markdown",
    summary="Export analysis as Markdown",
    description="Download formatted Markdown risk analysis report.",
)
async def export_markdown(
    document_id: UUID,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
):
    """Export analysis results as Markdown."""
    service = ExportService(session)
    md_content = await service.export_markdown(document_id, user_id)
    doc = await service._get_authorized_document(document_id, user_id)
    filename = f"{doc.original_filename}_risk_analysis.md"
    return Response(
        content=md_content,
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get(
    "/documents/{document_id}/pdf",
    summary="Export analysis as PDF (v1.1 Backlog)",
    description="PDF export is planned for v1.1 backlog.",
    status_code=status.HTTP_501_NOT_IMPLEMENTED,
)
async def export_pdf(
    document_id: UUID,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
):
    """PDF export endpoint (v1.1 Backlog)."""
    return JSONResponse(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        content={"detail": "PDF report export is scheduled for v1.1 backlog. Please use Markdown or JSON export in v1."},
    )


@router.get(
    "/documents/{document_id}/csv",
    summary="Export analysis as CSV (v1.1 Backlog)",
    description="CSV export is planned for v1.1 backlog.",
    status_code=status.HTTP_501_NOT_IMPLEMENTED,
)
async def export_csv(
    document_id: UUID,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
):
    """CSV export endpoint (v1.1 Backlog)."""
    return JSONResponse(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        content={"detail": "CSV export is scheduled for v1.1 backlog. Please use Markdown or JSON export in v1."},
    )
