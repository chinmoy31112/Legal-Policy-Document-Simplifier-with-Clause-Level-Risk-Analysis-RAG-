"""
Search endpoints.

Handles full-text and semantic search across documents and clauses.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.schemas.common import APIResponse
from app.api.v1.deps import get_current_user_id

router = APIRouter()


@router.get(
    "/",
    summary="Search documents and clauses",
    description=(
        "Search across clause titles, content, risk categories, "
        "and document names. Supports full-text filtering."
    ),
)
async def search(
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    q: str = Query(..., min_length=1, max_length=500, description="Search query"),
    scope: str = Query(
        default="all",
        description="Search scope: all, clauses, documents",
    ),
    risk_category: str | None = Query(default=None, description="Filter by risk category"),
    document_type: str | None = Query(default=None, description="Filter by document type"),
):
    """Search across documents and clauses."""
    # Implementation in Phase 6
    pass
