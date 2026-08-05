"""
Knowledge base management endpoints.

Handles listing, uploading, and managing reference clause documents.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, UploadFile, status

from app.schemas.knowledge_base import (
    KBClauseResponse,
    KBDocumentResponse,
    KBIngestionRequest,
    KBIngestionResponse,
)
from app.schemas.common import APIResponse, PaginatedResponse, PaginationParams
from app.api.v1.deps import get_current_user_id, get_pagination

router = APIRouter()


@router.get(
    "/",
    response_model=APIResponse[PaginatedResponse[KBDocumentResponse]],
    summary="List knowledge base documents",
    description="Retrieve a paginated list of knowledge base documents.",
)
async def list_kb_documents(
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    pagination: Annotated[PaginationParams, Depends(get_pagination)],
):
    """List all knowledge base documents."""
    # Implementation in Phase 3
    pass


@router.post(
    "/upload",
    response_model=APIResponse[KBIngestionResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Upload to knowledge base",
    description=(
        "Upload a reference document for the knowledge base. "
        "The document will be extracted, segmented, and embedded."
    ),
)
async def upload_kb_document(
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    file: UploadFile = File(...),
    title: str = "Reference Document",
    document_type: str = "other",
    jurisdiction: str | None = None,
):
    """Upload and ingest a knowledge base document."""
    # Implementation in Phase 3
    pass


@router.get(
    "/{kb_document_id}",
    response_model=APIResponse[KBDocumentResponse],
    summary="Get knowledge base document",
    description="Retrieve details for a specific knowledge base document.",
)
async def get_kb_document(
    kb_document_id: UUID,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
):
    """Get knowledge base document details."""
    # Implementation in Phase 3
    pass


@router.get(
    "/{kb_document_id}/clauses",
    response_model=APIResponse[list[KBClauseResponse]],
    summary="Get knowledge base clauses",
    description="Retrieve all clauses for a knowledge base document.",
)
async def get_kb_clauses(
    kb_document_id: UUID,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
):
    """Get all clauses from a knowledge base document."""
    # Implementation in Phase 3
    pass


@router.delete(
    "/{kb_document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete knowledge base document",
    description="Delete a knowledge base document and its clauses and embeddings.",
)
async def delete_kb_document(
    kb_document_id: UUID,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
):
    """Delete a knowledge base document."""
    # Implementation in Phase 3
    pass
