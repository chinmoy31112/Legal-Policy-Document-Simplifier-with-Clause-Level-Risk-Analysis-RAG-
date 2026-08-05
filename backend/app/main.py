"""
FastAPI application factory.

Creates and configures the FastAPI application with all middleware,
exception handlers, routers, and lifecycle events.
"""

import time
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.core.logging import setup_logging, get_logger
from app.core.exceptions import (
    AppException,
    DocumentProcessingError,
    AIServiceError,
    AuthenticationError,
    NotFoundError,
    ValidationError as AppValidationError,
)
from app.api.v1.router import api_v1_router

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifecycle manager: startup and shutdown events."""
    settings = get_settings()
    setup_logging(settings.log_level)
    logger.info(
        "application_starting",
        app_name=settings.app_name,
        version=settings.app_version,
        env=settings.app_env,
    )

    # Ensure required directories exist
    settings.upload_path
    settings.chroma_path

    yield

    logger.info("application_shutting_down")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=(
            "AI-powered legal document analyzer with clause-level risk assessment "
            "using Retrieval-Augmented Generation (RAG). Powered by Google Gemini."
        ),
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )

    # ── Middleware ────────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def add_process_time_header(request: Request, call_next):
        """Add X-Process-Time header to every response."""
        start = time.perf_counter()
        response = await call_next(request)
        elapsed = time.perf_counter() - start
        response.headers["X-Process-Time"] = f"{elapsed:.4f}"
        return response

    # ── Exception Handlers ───────────────────────────────────────────────
    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException):
        logger.warning(
            "app_exception",
            error_type=type(exc).__name__,
            detail=exc.detail,
            path=str(request.url),
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "type": type(exc).__name__,
                    "message": exc.detail,
                    "code": exc.error_code,
                }
            },
        )

    @app.exception_handler(AuthenticationError)
    async def auth_exception_handler(request: Request, exc: AuthenticationError):
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={
                "error": {
                    "type": "AuthenticationError",
                    "message": exc.detail,
                    "code": "AUTH_ERROR",
                }
            },
            headers={"WWW-Authenticate": "Bearer"},
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        logger.error(
            "unhandled_exception",
            error_type=type(exc).__name__,
            detail=str(exc),
            path=str(request.url),
            exc_info=True,
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": {
                    "type": "InternalServerError",
                    "message": "An unexpected error occurred. Please try again later.",
                    "code": "INTERNAL_ERROR",
                }
            },
        )

    # ── Routers ──────────────────────────────────────────────────────────
    app.include_router(api_v1_router, prefix="/api/v1")

    # ── Health Check ─────────────────────────────────────────────────────
    @app.get("/health", tags=["Health"])
    async def health_check():
        return {
            "status": "healthy",
            "app": settings.app_name,
            "version": settings.app_version,
            "env": settings.app_env,
        }

    return app


app = create_app()
