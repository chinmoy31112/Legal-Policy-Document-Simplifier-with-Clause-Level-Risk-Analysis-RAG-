"""
Application configuration using Pydantic Settings v2.

All configuration is loaded from environment variables with strict validation.
Zero secret leakage, explicit defaults, and model configurations adhering to Phase 0 ADRs.
"""

from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central application configuration with environment variable validation."""

    model_config = SettingsConfigDict(
        env_file=(".env", "backend/.env", "../backend/.env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ──────────────────────────────────────────────────────────
    app_name: str = "Legal Document Simplifier"
    app_version: str = "1.0.0"
    app_env: Literal["development", "staging", "production", "test"] = "development"
    debug: bool = False

    @field_validator("debug", mode="before")
    @classmethod
    def parse_debug(cls, v: Any) -> bool:
        if isinstance(v, str):
            v_lower = v.strip().lower()
            if v_lower in ("true", "1", "yes", "t", "on", "dev", "development"):
                return True
            return False
        return bool(v)

    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    log_format: Literal["json", "console"] = "json"

    # ── Server & Security ───────────────────────────────────────────────────
    host: str = "0.0.0.0"
    port: int = 8000
    allowed_origins: list[str] | str = Field(
        default=["http://localhost:3000", "http://127.0.0.1:3000"]
    )

    @field_validator("allowed_origins", mode="after")
    @classmethod
    def parse_origins(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str):
            v = v.strip()
            if v.startswith("[") and v.endswith("]"):
                import json

                try:
                    return json.loads(v)
                except Exception:
                    pass
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    # ── Database (PostgreSQL + pgvector) ────────────────────────────────────
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/legal_simplifier"
    database_echo: bool = False
    database_pool_size: int = 20
    database_max_overflow: int = 10

    # ── Redis & Background Jobs (ARQ) ───────────────────────────────────────
    redis_url: str = "redis://localhost:6379/0"
    job_timeout_seconds: int = 300
    job_max_retries: int = 3

    # ── Authentication ──────────────────────────────────────────────────────
    jwt_secret_key: str = "dev-insecure-secret-key-change-in-production-min-32-chars"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 7

    # ── Google Gemini AI Configuration ───────────────────────────────────────
    google_api_key: str = ""
    # Defaults per ADR 004: Models are configuration, not code.
    # Pinned model identifiers (no -latest aliases by default):
    gemini_embedding_model: str = "gemini-embedding-2"
    gemini_clause_model: str = "gemini-3.5-flash-lite"
    gemini_summary_model: str = "gemini-3.5-flash-lite"
    gemini_escalation_model: str | None = None
    gemini_enable_escalation: bool = False
    # GEMINI_LLM_MODEL is a deprecated backward-compatibility alias.
    # When unset, the separate gemini_clause_model and gemini_summary_model settings are used.
    gemini_llm_model: str | None = None
    gemini_analysis_batch_size: int = 4
    # Temperature, top_p, and top_k are omitted by default (3.5 Flash-Lite does not accept them):
    gemini_temperature: float | None = None
    gemini_top_p: float | None = None
    gemini_top_k: int | None = None
    gemini_max_output_tokens: int | None = None
    embedding_dimension: int = 768
    vector_store_type: Literal["pgvector", "chroma", "memory"] = "pgvector"

    def check_pinned_models(self) -> list[str]:
        """Check if any configured Gemini models are unpinned aliases, preview, or experimental."""
        warnings: list[str] = []
        for setting_name in ["gemini_clause_model", "gemini_summary_model", "gemini_embedding_model"]:
            val = getattr(self, setting_name, "")
            if not val:
                continue
            lower_val = val.lower()
            if "-latest" in lower_val or "preview" in lower_val or "exp" in lower_val or "experimental" in lower_val:
                warnings.append(
                    f"Setting '{setting_name}' is set to '{val}'. It is an alias, preview, or experimental. "
                    f"A pinned model (e.g. 'gemini-3.5-flash-lite') is strongly recommended."
                )
        return warnings

    # ── Upload & Storage ─────────────────────────────────────────────────────
    upload_dir: str = "./uploads"
    max_file_size_mb: int = 50
    allowed_file_types: list[str] | str = Field(default=[".pdf", ".docx", ".txt", ".md", ".json"])

    @field_validator("allowed_file_types", mode="after")
    @classmethod
    def parse_file_types(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str):
            return [ft.strip().lower() for ft in v.split(",") if ft.strip()]
        return v

    # ── Retrieval & RAG Parameters ──────────────────────────────────────────
    retrieval_top_k: int = 5
    retrieval_similarity_threshold: float = 0.20
    embedding_batch_size: int = 50
    rate_limit_delay: float = 4.0
    rate_limit_per_minute: int = 60

    # ── Per-Model Rate Limits and Daily Budgets ─────────────────────────────
    # Gemini 3.5 Flash-Lite: 15 RPM, ~250K TPM, 500 RPD -> Throttled below limits:
    gemini_flash_lite_rpm: int = 12
    gemini_flash_lite_tpm: int = 250_000
    gemini_flash_lite_rpd: int = 400

    # Gemini 3.8 Flash: 5 RPM, ~250K TPM, 20 RPD -> Throttled below limits:
    gemini_flash_rpm: int = 4
    gemini_flash_tpm: int = 250_000
    gemini_flash_rpd: int = 16

    # Gemini Embeddings: 100 RPM, 80K TPM, 1000 RPD -> Throttled below limits:
    gemini_embedding_rpm: int = 80
    gemini_embedding_tpm: int = 80_000
    gemini_embedding_rpd: int = 1000

    # LLM Legacy aliases
    gemini_llm_rpm: int = 12
    gemini_llm_tpm: int = 25_000

    # User quotas
    per_user_monthly_clause_quota: int = 500
    per_user_rpm_quota: int = 30

    def get_model_limits(self, model_name: str) -> dict[str, int]:
        """Return rate limits (rpm, tpm, rpd) for a given Gemini model name."""
        clean = model_name.replace("models/", "").lower()
        if "lite" in clean:
            return {
                "rpm": self.gemini_flash_lite_rpm,
                "tpm": self.gemini_flash_lite_tpm,
                "rpd": self.gemini_flash_lite_rpd,
            }
        elif "3.8" in clean or "flash" in clean or "3." in clean or "2.5" in clean:
            return {
                "rpm": self.gemini_flash_rpm,
                "tpm": self.gemini_flash_tpm,
                "rpd": self.gemini_flash_rpd,
            }
        elif "embed" in clean:
            return {
                "rpm": self.gemini_embedding_rpm,
                "tpm": self.gemini_embedding_tpm,
                "rpd": self.gemini_embedding_rpd,
            }
        return {"rpm": 12, "tpm": 250_000, "rpd": 400}

    # ── Privacy & Logging Policy (Rule 6: Never log document text) ───────────
    enable_text_logging: bool = False  # MUST remain False in all environments

    @property
    def max_file_size_bytes(self) -> int:
        return self.max_file_size_mb * 1024 * 1024

    @property
    def upload_path(self) -> Path:
        path = Path(self.upload_dir)
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings (singleton)."""
    return Settings()
