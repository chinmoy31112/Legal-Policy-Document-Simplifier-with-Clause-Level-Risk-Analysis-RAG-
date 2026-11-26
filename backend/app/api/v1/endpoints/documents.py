"""
Document management endpoints.

Handles document upload, listing, detail retrieval, and deletion.
"""

import asyncio
import json
from typing import Annotated
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Response,
    UploadFile,
    status,
)
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.rate_limiter import get_model_rate_limiter
from app.api.v1.deps import get_current_user_id, get_pagination
from app.core.config import get_settings
from app.core.logging import get_logger
from app.dependencies import get_db_session
from app.repositories.job_repo import JobRepository
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
from app.services.job_service import JobService, format_user_failure_message

logger = get_logger(__name__)

router = APIRouter()

# Legacy/test in-process task map retained strictly for cooperative cancel hooks in tests
_active_analysis_tasks: dict[UUID, asyncio.Task] = {}


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
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    file: UploadFile = File(...),
    document_type: str = Form(default="other"),
    jurisdiction: str | None = Form(default=None),
):
    """Upload document and enqueue analysis job onto persistent ARQ worker queue."""
    service = DocumentService(session)
    document = await service.upload_document(
        user_id=user_id,
        file=file,
        document_type=document_type,
        jurisdiction=jurisdiction,
    )

    # Enqueue in persistent ARQ worker queue (never run analysis inside the API process)
    job_service = JobService(session)
    await job_service.enqueue_document_analysis(document_id=document.id, user_id=user_id)

    return APIResponse(
        data=DocumentUploadResponse.model_validate(document),
        message="Document uploaded successfully. Analysis queued for background worker.",
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
    """Cancel active jobs, delete document/clauses/results/caches, and report purged/kept items."""
    service = DocumentService(session)
    report = await service.delete_document(
        document_id,
        user_id,
        legacy_tasks_map=_active_analysis_tasks,
    )
    return Response(
        status_code=status.HTTP_204_NO_CONTENT,
        headers={
            "X-Purged-Summary": json.dumps(report["purged"]),
            "X-Kept-Summary": json.dumps(report["kept"]),
        },
    )


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

    job_repo = JobRepository(session)
    latest_job = await job_repo.get_latest_for_document(document.id)

    status_str = document.status.lower()
    progress_map = {
        "uploaded": (0.10, "Document uploaded, queued for processing"),
        "queued": (0.10, "Queued for background worker"),
        "extracting": (0.30, "Extracting text and layout spans"),
        "segmenting": (0.50, "Segmenting into logical legal clauses"),
        "analyzing": (0.75, "Retrieving reference clauses and assessing risk"),
        "waiting for quota": (
            0.75,
            "Daily API quota reached. Job paused and will resume automatically after reset.",
        ),
        "waiting_for_quota": (
            0.75,
            "Daily API quota reached. Job paused and will resume automatically after reset.",
        ),
        "cancelling": (0.90, "Stopping analysis..."),
        "cancelled": (1.00, "Analysis cancelled"),
        "interrupted": (0.50, "Analysis interrupted by restart; ready to retry"),
        "completed": (1.00, "Analysis complete"),
        "failed": (1.00, "Document processing failed"),
    }
    progress, current_step = progress_map.get(status_str, (0.0, "Unknown state"))
    status_message = None
    if document.metadata_ and isinstance(document.metadata_, dict):
        status_message = document.metadata_.get("quota_notice")

    job_status_str = (latest_job.status or "").lower() if latest_job else ""
    if status_str in ("failed", "interrupted") or job_status_str in ("failed", "interrupted"):
        effective_fail_status = (
            job_status_str if job_status_str in ("failed", "interrupted") else status_str
        )
        status_message = format_user_failure_message(
            latest_job.error_message if latest_job else None,
            status=effective_fail_status,
        )

    total_clauses = latest_job.total_clauses if latest_job else len(document.clauses or [])
    analyzed_clauses = (
        latest_job.completed_clauses if latest_job else len(document.analysis_results or [])
    )
    if status_str == "completed" and total_clauses > 0:
        analyzed_clauses = total_clauses

    return APIResponse(
        data=AnalysisStatusResponse(
            document_id=document.id,
            status=document.status,
            progress=progress,
            current_step=current_step,
            total_clauses=total_clauses,
            analyzed_clauses=analyzed_clauses,
            message=status_message,
            job_id=latest_job.id if latest_job else None,
            job_status=latest_job.status if latest_job else None,
            stage=latest_job.stage if latest_job else status_str,
        )
    )


@router.get(
    "/{document_id}/events",
    summary="Stream live analysis events via SSE",
    description="Listen to server-sent events for batch completions, clause updates, and provisional scores.",
)
@router.get("/{document_id}/stream", include_in_schema=False)
async def stream_document_events(
    document_id: UUID,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
):
    """Stream live Server-Sent Events (SSE) for document analysis progress."""
    service = DocumentService(session)
    await service.get_document(document_id, user_id)

    from app.core.sse import get_sse_broadcaster

    broadcaster = get_sse_broadcaster()
    return StreamingResponse(
        broadcaster.subscribe(str(document_id)),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post(
    "/{document_id}/resume",
    response_model=APIResponse[AnalysisStatusResponse],
    summary="Resume document analysis",
    description="Resume processing a document that paused due to daily quota exhaustion or transient interruption.",
)
async def resume_document_analysis(
    document_id: UUID,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
):
    """Resume analysis for a document in 'waiting for quota', 'failed', 'interrupted', or 'cancelled' status."""
    service = DocumentService(session)
    document = await service.get_document(document_id, user_id)

    if document.status not in ["waiting for quota", "failed", "interrupted", "cancelled"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Cannot resume document in '{document.status}' status. "
                "Only 'waiting for quota', 'failed', 'interrupted', or 'cancelled' can be resumed."
            ),
        )

    # Reset any rate limiter daily exhausted flag for the models
    settings = get_settings()
    get_model_rate_limiter(settings.gemini_clause_model).reset_daily_quota_exhausted()
    get_model_rate_limiter(settings.gemini_summary_model).reset_daily_quota_exhausted()

    # Update document status and enqueue job via persistent ARQ worker queue
    analysis_service = AnalysisService(session)
    await analysis_service.document_repo.update_status(document_id, "uploaded")
    await session.commit()

    job_service = JobService(session)
    job = await job_service.enqueue_document_analysis(document_id=document_id, user_id=user_id)

    return APIResponse(
        data=AnalysisStatusResponse(
            document_id=document.id,
            status="uploaded",
            progress=0.10,
            current_step="Queued to resume remaining clauses",
            message="Analysis queued in background worker.",
            job_id=job.id,
            job_status=job.status,
            stage=job.stage,
        ),
        message="Document analysis resumed.",
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


@router.get(
    "/{document_id}/export/pdf",
    summary="Export document analysis as PDF",
    description="Download formatted PDF risk analysis report for this document.",
)
async def export_document_pdf(
    document_id: UUID,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
):
    """Export document analysis as PDF."""
    from fastapi import Response

    service = ExportService(session)
    pdf_bytes = await service.export_pdf(document_id, user_id)
    doc = await service._get_authorized_document(document_id, user_id)
    filename = f"{doc.original_filename}_risk_analysis.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
