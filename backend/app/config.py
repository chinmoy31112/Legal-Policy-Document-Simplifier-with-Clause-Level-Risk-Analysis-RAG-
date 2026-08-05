"""
Application configuration using Pydantic Settings.

All configuration is loaded from environment variables with sensible defaults.
Supports .env files for local development.
"""

from pathlib import Path
from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator


class Settings(BaseSettings):
    """Central application configuration."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ──────────────────────────────────────────────────────
    app_name: str = "Legal Document Simplifier"
    app_version: str = "1.0.0"
    app_env: Literal["development", "staging", "production"] = "development"
    debug: bool = True
    log_level: str = "INFO"

    # ── Server ───────────────────────────────────────────────────────────
    host: str = "0.0.0.0"
    port: int = 8000
    allowed_origins: list[str] = Field(
        default=["http://localhost:3000", "http://127.0.0.1:3000"]
    )

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def parse_origins(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v

    # ── Database ─────────────────────────────────────────────────────────
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/legal_simplifier"
    database_echo: bool = False
    database_pool_size: int = 20
    database_max_overflow: int = 10

    # ── Authentication ───────────────────────────────────────────────────
    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 7

    # ── Google AI ────────────────────────────────────────────────────────
    google_api_key: str = ""
    gemini_embedding_model: str = "gemini-embedding-2"
    gemini_llm_model: str = "gemini-2.5-flash"
    gemini_temperature: float = 0.1
    gemini_max_output_tokens: int = 8192

    # ── ChromaDB ─────────────────────────────────────────────────────────
    chroma_persist_dir: str = "./chroma_data"
    chroma_collection_name: str = "legal_clauses"

    # ── File Upload ──────────────────────────────────────────────────────
    upload_dir: str = "./uploads"
    max_file_size_mb: int = 50
    allowed_file_types: list[str] = Field(
        default=[".pdf", ".docx", ".txt", ".md", ".json"]
    )

    @field_validator("allowed_file_types", mode="before")
    @classmethod
    def parse_file_types(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str):
            return [ft.strip() for ft in v.split(",")]
        return v

    # ── RAG ──────────────────────────────────────────────────────────────
    retrieval_top_k: int = 5
    embedding_batch_size: int = 50

    # ── Rate Limiting ────────────────────────────────────────────────────
    rate_limit_per_minute: int = 60

    # ── Derived Properties ───────────────────────────────────────────────
    @property
    def max_file_size_bytes(self) -> int:
        return self.max_file_size_mb * 1024 * 1024

    @property
    def upload_path(self) -> Path:
        path = Path(self.upload_dir)
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def chroma_path(self) -> Path:
        path = Path(self.chroma_persist_dir)
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings (singleton)."""
    return Settings()
