"""
API v1 aggregate router.

Includes all versioned endpoint routers under /api/v1.
"""

from fastapi import APIRouter

from app.api.v1.endpoints import auth, documents, analysis, knowledge_base, export, search

api_v1_router = APIRouter()

api_v1_router.include_router(
    auth.router,
    prefix="/auth",
    tags=["Authentication"],
)

api_v1_router.include_router(
    documents.router,
    prefix="/documents",
    tags=["Documents"],
)

api_v1_router.include_router(
    analysis.router,
    prefix="/analysis",
    tags=["Analysis"],
)

api_v1_router.include_router(
    knowledge_base.router,
    prefix="/knowledge-base",
    tags=["Knowledge Base"],
)

api_v1_router.include_router(
    export.router,
    prefix="/export",
    tags=["Export"],
)

api_v1_router.include_router(
    search.router,
    prefix="/search",
    tags=["Search"],
)
