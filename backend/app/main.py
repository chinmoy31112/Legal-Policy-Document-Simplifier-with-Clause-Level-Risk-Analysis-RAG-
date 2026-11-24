"""
FastAPI application factory.

Creates and configures the FastAPI application with all middleware,
exception handlers, routers, and lifecycle events.
"""

import time
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

import app.models  # noqa: F401 — Register all ORM models
from app.api.v1.endpoints.health import readiness_check as probe_readiness
from app.api.v1.router import api_v1_router
from app.core.config import get_settings
from app.core.exceptions import (
    AppException,
    AuthenticationError,
)
from app.core.logging import get_logger, setup_logging
from app.core.metrics import registry, track_request

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifecycle manager: startup and shutdown events."""
    settings = get_settings()
    setup_logging(settings.log_level, settings.log_format)
    logger.info(
        "application_starting",
        app_name=settings.app_name,
        version=settings.app_version,
        env=settings.app_env,
    )

    # Ensure required directories exist
    settings.upload_path

    # Check for unpinned model aliases or experimental tags
    for warn_msg in settings.check_pinned_models():
        logger.warning("gemini_model_non_pinned_warning", warning=warn_msg)

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

    # ── Middleware ───────────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def request_timing_and_security_headers(request: Request, call_next):
        """Track request timing, collect telemetry metrics, and attach strict security headers."""
        start = time.perf_counter()
        response = await call_next(request)
        elapsed = time.perf_counter() - start

        # Process time & security headers
        response.headers["X-Process-Time"] = f"{elapsed:.4f}"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), camera=(), microphone=()"
        response.headers["Content-Security-Policy"] = "default-src 'self'; frame-ancestors 'none';"

        # Observability metrics collection
        track_request(request.method, request.url.path, response.status_code, elapsed)
        return response

    # ── Exception Handlers ───────────────────────────────────────────────────
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
                "detail": exc.detail,
                "error": {
                    "type": type(exc).__name__,
                    "message": exc.detail,
                    "code": exc.error_code,
                },
            },
        )

    @app.exception_handler(AuthenticationError)
    async def auth_exception_handler(request: Request, exc: AuthenticationError):
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={
                "detail": exc.detail,
                "error": {
                    "type": "AuthenticationError",
                    "message": exc.detail,
                    "code": "AUTH_ERROR",
                },
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

    # ── API v1 Routers ───────────────────────────────────────────────────────
    app.include_router(api_v1_router, prefix="/api/v1")

    # ── Root Health, Observability & Readiness Probes ────────────────────────
    @app.get("/health", tags=["Health"])
    @app.get("/health/live", tags=["Health"])
    async def root_health_check():
        return {
            "status": "healthy",
            "app": settings.app_name,
            "version": settings.app_version,
            "env": settings.app_env,
        }

    @app.get("/ready", tags=["Health"])
    @app.get("/health/ready", tags=["Health"])
    async def root_readiness_check(response: Response):
        return await probe_readiness(response)

    @app.get("/metrics", tags=["Observability"])
    async def prometheus_metrics():
        """Prometheus metrics exposition endpoint."""
        content = registry.generate_exposition()
        return Response(content=content, media_type="text/plain; version=0.0.4; charset=utf-8")

    return app


app = create_app()  # type: ignore[assignment]
