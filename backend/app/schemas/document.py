"""
Document schemas.

Pydantic models for document upload, listing, and detail responses.
"""

from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class DocumentType(StrEnum):
    """Supported legal document types."""
    TERMS_AND_CONDITIONS = "terms_and_conditions"
    PRIVACY_POLICY = "privacy_policy"
    RENTAL_AGREEMENT = "rental_agreement"
    EMPLOYMENT_CONTRACT = "employment_contract"
    SERVICE_AGREEMENT = "service_agreement"
    LOAN_AGREEMENT = "loan_agreement"
    EULA = "eula"
    OTHER = "other"


class DocumentStatus(StrEnum):
    """Document processing status."""
    UPLOADED = "uploaded"
    EXTRACTING = "extracting"
    SEGMENTING = "segmenting"
    EMBEDDING = "embedding"
    ANALYZING = "analyzing"
    COMPLETED = "completed"
    FAILED = "failed"


class DocumentUploadResponse(BaseModel):
    """Response after a successful document upload."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    filename: str
    original_filename: str
    file_type: str
    file_size: int
    document_type: DocumentType
    status: DocumentStatus
    created_at: datetime


class DocumentListItem(BaseModel):
    """Condensed document info for list views."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    original_filename: str
    document_type: DocumentType
    status: DocumentStatus
    file_size: int
    is_scanned: bool = False
    clause_count: int = 0
    overall_risk_score: int | None = None
    created_at: datetime


class DocumentDetail(BaseModel):
    """Full document details including metadata."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    original_filename: str
    filename: str
    file_type: str
    file_size: int
    document_type: DocumentType
    status: DocumentStatus
    jurisdiction: str | None = None
    is_scanned: bool = False
    raw_text: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict, validation_alias="metadata_")
    created_at: datetime
    updated_at: datetime | None = None
