"""
Knowledge base schemas.

Pydantic models for knowledge base documents, clauses, and ingestion.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class KBDocumentCreate(BaseModel):
    """Request to create a knowledge base document."""
    title: str = Field(..., min_length=1, max_length=500)
    document_type: str
    jurisdiction: str | None = None
    version: str = "1.0"


class KBDocumentResponse(BaseModel):
    """Knowledge base document details."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    document_type: str
    source: str | None = None
    jurisdiction: str | None = None
    version: str
    status: str
    clause_count: int = 0
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime | None = None


class KBClauseResponse(BaseModel):
    """Knowledge base clause details."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    kb_document_id: UUID
    clause_number: str | None = None
    title: str | None = None
    content: str
    category: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class KBIngestionRequest(BaseModel):
    """Request to ingest content into the knowledge base."""
    title: str
    document_type: str
    jurisdiction: str | None = None
    version: str = "1.0"


class KBIngestionResponse(BaseModel):
    """Response after knowledge base ingestion."""
    document_id: UUID
    title: str
    clauses_extracted: int
    clauses_embedded: int
    status: str
    message: str
