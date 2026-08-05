"""
Clause schemas.

Pydantic models for extracted legal clauses.
"""

from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ClauseResponse(BaseModel):
    """Individual clause data."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    document_id: UUID
    clause_index: int
    clause_number: str | None = None
    title: str | None = None
    content: str
    category: str | None = None
    start_page: int | None = None
    end_page: int | None = None
    start_char: int | None = None
    end_char: int | None = None
    metadata: dict[str, Any] = Field(default_factory=dict, validation_alias="metadata_")
