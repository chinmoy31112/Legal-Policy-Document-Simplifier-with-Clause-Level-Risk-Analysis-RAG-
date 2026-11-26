"""
Admin and Telemetry Endpoints for Gemini Call Ledger.

Provides visibility into today's outbound Gemini calls categorized by purpose
and status to match and cross-verify with Google AI Studio request metrics.
"""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Query

from app.ai.ledger import get_call_ledger
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.get("/today", summary="Get today's Gemini calls by purpose")
async def get_today_ledger_summary(
    date: str | None = Query(
        default=None,
        description="Target date in YYYY-MM-DD format (defaults to today UTC)",
    ),
) -> dict[str, Any]:
    """
    Returns today's aggregate outbound Gemini calls grouped by purpose
    (embed, classify, analyze, repair, retry, summary) and status (ok, 429 minute, 429 day, 503, invalid JSON).
    Directly corresponds to AI Studio's RPD usage.
    """
    ledger = get_call_ledger()
    return ledger.get_today_summary(target_date_str=date)


@router.get("/document/{document_id}", summary="Get call ledger summary for a specific document")
async def get_document_ledger_summary(document_id: UUID) -> dict[str, Any]:
    """
    Returns total Gemini calls, retries, repairs, latency, tokens,
    and budget for a specific document analysis job.
    """
    ledger = get_call_ledger()
    return ledger.get_document_summary(str(document_id))
