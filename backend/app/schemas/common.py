"""
Common schemas shared across the application.

Includes pagination, generic API responses, and reusable base schemas.
"""

from datetime import datetime
from typing import Any, Generic, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class PaginationParams(BaseModel):
    """Pagination query parameters."""
    page: int = Field(default=1, ge=1, description="Page number")
    page_size: int = Field(default=20, ge=1, le=100, description="Items per page")

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response wrapper."""
    items: list[T]
    total: int
    page: int
    page_size: int
    total_pages: int

    @classmethod
    def create(
        cls,
        items: list[T],
        total: int,
        page: int,
        page_size: int,
    ) -> "PaginatedResponse[T]":
        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=(total + page_size - 1) // page_size,
        )


class APIResponse(BaseModel, Generic[T]):
    """Standard API response envelope."""
    success: bool = True
    data: T | None = None
    message: str | None = None


class ErrorResponse(BaseModel):
    """Standard error response."""
    error: dict[str, Any] = Field(
        ...,
        examples=[{
            "type": "ValidationError",
            "message": "Invalid input.",
            "code": "VALIDATION_ERROR",
        }],
    )


class TimestampSchema(BaseModel):
    """Base schema with timestamp fields."""
    model_config = ConfigDict(from_attributes=True)
    created_at: datetime
    updated_at: datetime | None = None
