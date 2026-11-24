"""
Structured logging configuration using structlog.

Enforces Rule 6 ("Privacy: Never log document text"):
Automatically detects and redacts any text, raw_text, clause_text, or document payloads
from log records, logging only operational metadata, IDs, execution metrics, and error codes.
"""

import logging
import sys
from collections.abc import MutableMapping
from typing import Any

import structlog

# Sensitive keys that must NEVER be printed to logs under Rule 6
SENSITIVE_TEXT_KEYS = {
    "text",
    "raw_text",
    "clause_text",
    "document_text",
    "content",
    "full_text",
    "untrusted_text",
    "password",
    "hashed_password",
    "jwt_secret_key",
    "google_api_key",
}


def redact_document_text_processor(
    logger: Any, method_name: str, event_dict: MutableMapping[str, Any]
) -> MutableMapping[str, Any]:
    """
    Structlog processor that redacts any document or clause text to prevent PII/confidential leaks.
    Replaces full text with metadata summary (length, hash prefix).
    """
    for key in list(event_dict.keys()):
        lower_key = key.lower()
        if lower_key in SENSITIVE_TEXT_KEYS or "text" in lower_key or "password" in lower_key:
            val = event_dict[key]
            if isinstance(val, str):
                event_dict[key] = f"[REDACTED len={len(val)}]"
            elif isinstance(val, (bytes, bytearray)):
                event_dict[key] = f"[REDACTED_BYTES len={len(val)}]"
            elif val is not None:
                event_dict[key] = "[REDACTED]"
    return event_dict


def setup_logging(log_level: str = "INFO", log_format: str = "json") -> None:
    """
    Configure structured logging for the application.

    Args:
        log_level: Minimum log level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        log_format: 'json' for production/cloud logging or 'console' for local dev.
    """
    shared_processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        redact_document_text_processor,  # Enforce Zero-Text Logging Policy
        structlog.processors.UnicodeDecoder(),
    ]

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    formatter_processors: list[Any]
    if log_format == "console":
        formatter_processors = [
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            structlog.dev.ConsoleRenderer(colors=True),
        ]
    else:
        formatter_processors = [
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            structlog.processors.JSONRenderer(),
        ]

    formatter = structlog.stdlib.ProcessorFormatter(
        processors=formatter_processors,  # type: ignore[arg-type]
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    # Silence noisy third-party loggers
    for noisy in ("uvicorn.access", "asyncpg", "httpcore", "httpx"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Return a configured structured logger instance."""
    return structlog.get_logger(name)
