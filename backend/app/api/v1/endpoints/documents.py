"""
Document management endpoints.

Handles document upload, listing, detail retrieval, and deletion.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_user_id, get_pagination
from app.core.database import async_session_factory
from app.dependencies import get_db_session
from app.schemas.analysis import (
    AnalysisStatusResponse,
    ClauseAnalysisResponse,
    DocumentAnalysisResponse,
)
from app.schemas.common import APIResponse, PaginatedResponse, PaginationParams
from app.schemas.document import (
    DocumentDetail,
    DocumentListItem,
    DocumentStatus,
    DocumentType,
    DocumentUploadResponse,
)
from app.services.analysis_service import AnalysisService
from app.services.document_service import DocumentService
from app.services.export_service import ExportService

router = APIRouter()


async def run_analysis_background(document_id: UUID):
    """Helper to run the analysis task with a fresh database session."""
    async with async_session_factory() as session:
        service = AnalysisService(session)
        await service._run_analysis_task(document_id)


@router.post(
    "",
    response_model=APIResponse[DocumentUploadResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Upload a legal document",
    description="Upload a document for parsing and risk analysis.",
)
@router.post(
    "/",
    response_model=APIResponse[DocumentUploadResponse],
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
)
@router.post(
    "/upload",
    response_model=APIResponse[DocumentUploadResponse],
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
)
async def upload_document(
    background_tasks: BackgroundTasks,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    file: UploadFile = File(...),
    document_type: str = Form(default="other"),
    jurisdiction: str | None = Form(default=None),
):
    """Upload and start analysis on a document."""
    service = DocumentService(session)
    document = await service.upload_document(
        user_id=user_id,
        file=file,
        document_type=document_type,
        jurisdiction=jurisdiction,
    )

    # Trigger background analysis
    background_tasks.add_task(run_analysis_background, document.id)

    return APIResponse(
        data=DocumentUploadResponse.model_validate(document),
        message="Document uploaded successfully. Analysis started.",
    )


@router.get(
    "",
    response_model=APIResponse[PaginatedResponse[DocumentListItem]],
    summary="List documents",
    description="Retrieve a paginated list of uploaded documents.",
)
@router.get(
    "/",
    response_model=APIResponse[PaginatedResponse[DocumentListItem]],
    include_in_schema=False,
)
async def list_documents(
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    pagination: Annotated[PaginationParams, Depends(get_pagination)],
    status_filter: DocumentStatus | None = Query(default=None, alias="status"),
    document_type: DocumentType | None = Query(default=None),
):
    """List all documents for the authenticated user."""
    service = DocumentService(session)
    items, total = await service.list_documents(
        user_id=user_id,
        offset=pagination.offset,
        limit=pagination.page_size,
        status_filter=status_filter,
        document_type=document_type,
    )
    paginated = PaginatedResponse.create(
        items=[DocumentListItem.model_validate(doc) for doc in items],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )
    return APIResponse(data=paginated)


@router.get(
    "/{document_id}",
    response_model=APIResponse[DocumentDetail],
    summary="Get document details",
    description="Retrieve full details for a specific document.",
)
async def get_document(
    document_id: UUID,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
):
    """Get detailed information about a specific document."""
    service = DocumentService(session)
    document = await service.get_document(document_id, user_id)
    return APIResponse(data=DocumentDetail.model_validate(document))


@router.delete(
    "/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a document",
    description="Delete a document and all associated analysis data.",
)
async def delete_document(
    document_id: UUID,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
):
    """Delete a document and its associated data."""
    service = DocumentService(session)
    await service.delete_document(document_id, user_id)


@router.get(
    "/{document_id}/status",
    response_model=APIResponse[AnalysisStatusResponse],
    summary="Get document processing job status",
    description="Check processing progress and stage for an uploaded document.",
)
async def get_document_status(
    document_id: UUID,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
):
    """Retrieve background job progress status."""
    service = DocumentService(session)
    document = await service.get_document(document_id, user_id)

    status_str = document.status.lower()
    progress_map = {
        "uploaded": (0.10, "Document uploaded, queued for processing"),
        "extracting": (0.30, "Extracting text and layout spans"),
        "segmenting": (0.50, "Segmenting into logical legal clauses"),
        "analyzing": (0.75, "Retrieving reference clauses and assessing risk"),
        "waiting for quota": (0.75, "Daily API quota reached. Job paused and will resume automatically after reset."),
        "completed": (1.00, "Analysis complete"),
        "failed": (1.00, "Document processing failed"),
    }
    progress, current_step = progress_map.get(status_str, (0.0, "Unknown state"))
    quota_msg = None
    if document.metadata_ and isinstance(document.metadata_, dict):
        quota_msg = document.metadata_.get("quota_notice")

    return APIResponse(
        data=AnalysisStatusResponse(
            document_id=document.id,
            status=document.status,
            progress=progress,
            current_step=current_step,
            message=quota_msg,
        )
    )


@router.get(
    "/{document_id}/clauses",
    response_model=APIResponse[list[ClauseAnalysisResponse]],
    summary="Get analyzed clauses for document",
    description="Retrieve all clauses with their plain-English simplifications and risk assessments.",
)
async def get_document_clauses(
    document_id: UUID,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
):
    """Get all clause analyses for a document."""
    doc_service = DocumentService(session)
    await doc_service.get_document(document_id, user_id)

    analysis_service = AnalysisService(session)
    analyses = await analysis_service.get_clause_analyses(document_id)
    return APIResponse(data=[ClauseAnalysisResponse.model_validate(a) for a in analyses])


@router.get(
    "/{document_id}/analysis",
    response_model=APIResponse[DocumentAnalysisResponse],
    summary="Get document risk analysis",
    description="Retrieve holistic document-level risk score and executive summary.",
)
async def get_document_risk_analysis(
    document_id: UUID,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
):
    """Get document-level analysis."""
    doc_service = DocumentService(session)
    await doc_service.get_document(document_id, user_id)

    analysis_service = AnalysisService(session)
    analysis = await analysis_service.get_document_analysis(document_id)
    return APIResponse(data=DocumentAnalysisResponse.model_validate(analysis))


@router.get(
    "/{document_id}/export/json",
    summary="Export document analysis as JSON",
    description="Download validated JSON report for this document.",
)
async def export_document_json(
    document_id: UUID,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
):
    """Export document analysis as JSON."""
    from fastapi.responses import JSONResponse
    service = ExportService(session)
    data = await service.export_json(document_id, user_id)
    filename = f"{data['document']['filename']}_risk_analysis.json"
    return JSONResponse(
        content=data,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get(
    "/{document_id}/export/markdown",
    summary="Export document analysis as Markdown",
    description="Download formatted Markdown report for this document.",
)
async def export_document_markdown(
    document_id: UUID,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
):
    """Export document analysis as Markdown."""
    from fastapi import Response
    service = ExportService(session)
    md_content = await service.export_markdown(document_id, user_id)
    doc = await service._get_authorized_document(document_id, user_id)
    filename = f"{doc.original_filename}_risk_analysis.md"
    return Response(
        content=md_content,
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
