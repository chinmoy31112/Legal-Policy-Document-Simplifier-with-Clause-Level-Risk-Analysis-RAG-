"""
Unit tests for Foundation components (Config, Logging, Health endpoints).
"""

import pytest
from httpx import AsyncClient

from app.core.config import Settings, get_settings
from app.core.logging import redact_document_text_processor


def test_settings_defaults():
    """Verify default configurations conform to ADRs and Phase 1 specifications."""
    settings = get_settings()
    assert settings.gemini_embedding_model == "gemini-embedding-2"
    assert settings.gemini_llm_model == "gemini-2.5-flash"
    assert settings.embedding_dimension == 768
    assert settings.vector_store_type in ("pgvector", "chroma", "memory")
    assert settings.enable_text_logging is False
    assert settings.max_file_size_mb == 50
    assert ".pdf" in settings.allowed_file_types


def test_settings_origin_parsing():
    """Verify CORS origins parser handles string lists and JSON strings."""
    s = Settings(allowed_origins="http://example.com, http://app.com")
    assert "http://example.com" in s.allowed_origins
    assert "http://app.com" in s.allowed_origins


def test_logging_redacts_sensitive_document_text():
    """Verify Rule 6: Never log document text is strictly enforced by the structlog processor."""
    event_dict = {
        "event": "clause_analyzed",
        "clause_id": "cls-001",
        "document_id": "doc-999",
        "clause_text": "Customer shall indemnify Vendor for all damages without cap.",
        "raw_text": "Confidential agreement terms here.",
        "untrusted_text": "Malicious injected instructions.",
        "password": "secret_password_123",
        "duration_ms": 42.5,
    }

    processed = redact_document_text_processor(None, "info", event_dict)

    # Sensitive fields must be redacted
    assert "Customer shall indemnify" not in str(processed["clause_text"])
    assert "[REDACTED" in processed["clause_text"]
    assert "Confidential agreement" not in str(processed["raw_text"])
    assert "[REDACTED" in processed["raw_text"]
    assert "secret_password_123" not in str(processed["password"])
    assert "[REDACTED" in processed["password"]

    # Non-sensitive operational metadata must be preserved
    assert processed["clause_id"] == "cls-001"
    assert processed["document_id"] == "doc-999"
    assert processed["duration_ms"] == 42.5


@pytest.mark.asyncio
async def test_health_endpoint_liveness(client: AsyncClient):
    """Verify root /health and /api/v1/health return 200 OK."""
    for path in ("/health", "/api/v1/health"):
        resp = await client.get(path)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert "version" in data
        assert "app" in data


@pytest.mark.asyncio
async def test_readiness_probe_structure(client: AsyncClient):
    """Verify readiness endpoint returns dependency health states."""
    resp = await client.get("/api/v1/health/ready")
    assert resp.status_code in (200, 503)
    data = resp.json()
    assert "database" in data
    assert "redis" in data
    assert "status" in data
