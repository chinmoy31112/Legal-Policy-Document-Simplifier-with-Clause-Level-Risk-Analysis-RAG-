"""
Document management endpoints.

Handles document upload, listing, detail retrieval, and deletion.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.document import (
    DocumentDetail,
    DocumentListItem,
    DocumentStatus,
    DocumentType,
    DocumentUploadResponse,
)
from app.schemas.common import APIResponse, PaginatedResponse, PaginationParams
from app.api.v1.deps import get_current_user_id, get_pagination
from app.core.database import async_session_factory
from app.dependencies import get_db_session
from app.services.document_service import DocumentService
from app.services.analysis_service import AnalysisService

router = APIRouter()


async def run_analysis_background(document_id: UUID):
    """Helper to run the analysis task with a fresh database session."""
    async with async_session_factory() as session:
        service = AnalysisService(session)
        await service._run_analysis_task(document_id)


@router.post(
    "/upload",
    response_model=APIResponse[DocumentUploadResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Upload a legal document",
    description="Upload a document for parsing and risk analysis.",
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
        message="Document uploaded successfully. Analysis started."
    )


@router.get(
    "/",
    response_model=APIResponse[PaginatedResponse[DocumentListItem]],
    summary="List documents",
    description="Retrieve a paginated list of uploaded documents.",
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
