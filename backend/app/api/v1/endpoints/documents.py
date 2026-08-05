"""
Document management endpoints.

Handles document upload, listing, detail retrieval, and deletion.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status

from app.schemas.document import (
    DocumentDetail,
    DocumentListItem,
    DocumentStatus,
    DocumentType,
    DocumentUploadResponse,
)
from app.schemas.common import APIResponse, PaginatedResponse, PaginationParams
from app.api.v1.deps import get_current_user_id, get_pagination

router = APIRouter()


@router.post(
    "/upload",
    response_model=APIResponse[DocumentUploadResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Upload a legal document",
    description=(
        "Upload a PDF, DOCX, or TXT file for analysis. "
        "The document will be queued for text extraction and clause segmentation."
    ),
)
async def upload_document(
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    file: UploadFile = File(..., description="Legal document file (PDF, DOCX, TXT)"),
    document_type: DocumentType = Form(
        default=DocumentType.OTHER,
        description="Type of legal document",
    ),
    jurisdiction: str | None = Form(default=None, description="Legal jurisdiction"),
):
    """Upload a legal document for analysis."""
    # Implementation in Phase 2
    pass


@router.get(
    "/",
    response_model=APIResponse[PaginatedResponse[DocumentListItem]],
    summary="List documents",
    description="Retrieve a paginated list of uploaded documents.",
)
async def list_documents(
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    pagination: Annotated[PaginationParams, Depends(get_pagination)],
    status_filter: DocumentStatus | None = Query(default=None, alias="status"),
    document_type: DocumentType | None = Query(default=None),
):
    """List all documents for the authenticated user."""
    # Implementation in Phase 2
    pass


@router.get(
    "/{document_id}",
    response_model=APIResponse[DocumentDetail],
    summary="Get document details",
    description="Retrieve full details for a specific document.",
)
async def get_document(
    document_id: UUID,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
):
    """Get detailed information about a specific document."""
    # Implementation in Phase 2
    pass


@router.delete(
    "/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a document",
    description="Delete a document and all associated analysis data.",
)
async def delete_document(
    document_id: UUID,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
):
    """Delete a document and its associated data."""
    # Implementation in Phase 2
    pass
