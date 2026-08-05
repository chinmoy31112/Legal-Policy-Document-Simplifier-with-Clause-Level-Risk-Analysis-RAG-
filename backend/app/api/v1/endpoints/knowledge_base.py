"""
Knowledge base management endpoints.

Handles listing, uploading, and managing reference clause documents.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.knowledge_base import (
    KBClauseResponse,
    KBDocumentResponse,
    KBIngestionResponse,
)
from app.schemas.common import APIResponse, PaginatedResponse, PaginationParams
from app.api.v1.deps import get_current_user_id, get_pagination
from app.dependencies import get_db_session
from app.services.knowledge_base_service import KnowledgeBaseService

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
    session: Annotated[AsyncSession, Depends(get_db_session)],
):
    """List all knowledge base documents."""
    service = KnowledgeBaseService(session)
    items, total = await service.get_all_documents(
        offset=pagination.offset, limit=pagination.page_size
    )
    
    # Calculate clause count for response if it were loaded, but currently it's not.
    # To avoid N+1 queries, we could update the repo, but for now we return 0 or rely on a property.
    response_items = [KBDocumentResponse.model_validate(doc) for doc in items]
    
    paginated = PaginatedResponse.create(
        items=response_items,
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )
    return APIResponse(data=paginated)


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
    session: Annotated[AsyncSession, Depends(get_db_session)],
    file: UploadFile = File(...),
    title: str = Form(default="Reference Document"),
    document_type: str = Form(default="other"),
    jurisdiction: str | None = Form(default=None),
):
    """Upload and ingest a knowledge base document."""
    service = KnowledgeBaseService(session)
    result = await service.ingest_document(
        file=file,
        title=title,
        document_type=document_type,
        jurisdiction=jurisdiction,
    )
    return APIResponse(data=result, message="Knowledge base ingestion started.")


@router.get(
    "/{kb_document_id}",
    response_model=APIResponse[KBDocumentResponse],
    summary="Get knowledge base document",
    description="Retrieve details for a specific knowledge base document.",
)
async def get_kb_document(
    kb_document_id: UUID,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
):
    """Get knowledge base document details."""
    service = KnowledgeBaseService(session)
    document = await service.get_document(kb_document_id)
    return APIResponse(data=KBDocumentResponse.model_validate(document))


@router.get(
    "/{kb_document_id}/clauses",
    response_model=APIResponse[list[KBClauseResponse]],
    summary="Get knowledge base clauses",
    description="Retrieve all clauses for a knowledge base document.",
)
async def get_kb_clauses(
    kb_document_id: UUID,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
):
    """Get all clauses from a knowledge base document."""
    service = KnowledgeBaseService(session)
    clauses = await service.get_clauses_for_document(kb_document_id)
    return APIResponse(data=[KBClauseResponse.model_validate(c) for c in clauses])


@router.delete(
    "/{kb_document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete knowledge base document",
    description="Delete a knowledge base document and its clauses and embeddings.",
)
async def delete_kb_document(
    kb_document_id: UUID,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
):
    """Delete a knowledge base document."""
    service = KnowledgeBaseService(session)
    await service.delete_document(kb_document_id)
