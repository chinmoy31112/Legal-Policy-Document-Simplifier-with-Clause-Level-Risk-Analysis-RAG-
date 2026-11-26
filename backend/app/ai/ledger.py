"""
Centralized Gemini Outbound Call Ledger and Budget Controller.

Adheres to:
- Part A.1: Record every outbound Gemini request (time, job_id, document_id, user_id,
            purpose, attempt_number, status, latency, tokens, model_name).
- Part A.2: Post-job summary logging (calls per purpose, retries, repairs,
            limiter wait time, total time).
- Part A.3: Daily budget tracking, routing 100% of outbound Gemini calls through
            ledger and limiter.
- Part A.4: Per-document call budget (default 1.5 x expected calls) with fast fail on exceed.
- Part A.5: CLI tool and admin endpoint for daily comparison with AI Studio.
"""

import argparse
import math
import threading
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any, Generator, Literal

from pydantic import BaseModel, Field

from app.core.exceptions import AIServiceError
from app.core.logging import get_logger

logger = get_logger(__name__)

CallPurpose = Literal[
    "embed",
    "classify",
    "analyze",
    "repair",
    "retry",
    "summary",
    "unknown",
]

CallStatus = Literal[
    "ok",
    "429 minute",
    "429 day",
    "503",
    "invalid JSON",
    "error",
]

# ContextVar for propagating tracing context across async tasks
_call_context_var: ContextVar[dict[str, Any]] = ContextVar(
    "_call_context_var",
    default={
        "job_id": None,
        "document_id": None,
        "user_id": None,
        "purpose": "unknown",
        "attempt_number": 1,
    },
)


def get_call_context() -> dict[str, Any]:
    """Retrieve the current call context dictionary."""
    return dict(_call_context_var.get())


def set_call_context(
    job_id: str | None = None,
    document_id: str | None = None,
    user_id: str | None = None,
    purpose: CallPurpose | str | None = None,
    attempt_number: int | None = None,
) -> None:
    """Update current task call context."""
    ctx = dict(_call_context_var.get())
    if job_id is not None:
        ctx["job_id"] = str(job_id)
    if document_id is not None:
        ctx["document_id"] = str(document_id)
    if user_id is not None:
        ctx["user_id"] = str(user_id)
    if purpose is not None:
        ctx["purpose"] = str(purpose)
    if attempt_number is not None:
        ctx["attempt_number"] = attempt_number
    _call_context_var.set(ctx)


def clear_call_context() -> None:
    """Reset call context to blank."""
    _call_context_var.set(
        {
            "job_id": None,
            "document_id": None,
            "user_id": None,
            "purpose": "unknown",
            "attempt_number": 1,
        }
    )


@contextmanager
def call_purpose(purpose: CallPurpose | str) -> Generator[None, None, None]:
    """Context manager to scope a block of code to a specific call purpose."""
    ctx = dict(_call_context_var.get())
    old_purpose = ctx.get("purpose", "unknown")
    ctx["purpose"] = str(purpose)
    _call_context_var.set(ctx)
    try:
        yield
    finally:
        ctx_revert = dict(_call_context_var.get())
        ctx_revert["purpose"] = old_purpose
        _call_context_var.set(ctx_revert)


class CallBudgetExceededError(AIServiceError):
    """Raised when a document exceeds its allotted Gemini call budget."""

    def __init__(self, document_id: str, current_calls: int, budget: int):
        self.document_id = document_id
        self.current_calls = current_calls
        self.budget = budget
        super().__init__(
            f"Call budget exceeded for document '{document_id}': "
            f"{current_calls} calls dispatched exceeding budget of {budget}. "
            "Analysis stopped to prevent infinite loops or quota drain."
        )


class CallRecord(BaseModel):
    """Detailed record of a single outbound Gemini API call."""

    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    job_id: str | None = None
    document_id: str | None = None
    user_id: str | None = None
    purpose: str = "unknown"
    attempt_number: int = 1
    status: str = "ok"
    latency: float = 0.0  # seconds
    tokens: int = 0
    model_name: str = ""


class CallLedger:
    """
    Centralized, thread-safe call ledger recording every outbound Gemini API request.
    Maintains daily statistics, per-document budgets, and post-job telemetry.
    """

    def __init__(self) -> None:
        self._records: list[CallRecord] = []
        self._document_budgets: dict[str, int] = {}
        self._document_calls: dict[str, list[CallRecord]] = {}
        self._lock = threading.Lock()

    def reset(self) -> None:
        """Clear all records and budgets (primarily for testing)."""
        with self._lock:
            self._records.clear()
            self._document_budgets.clear()
            self._document_calls.clear()

    def get_records(self) -> list[CallRecord]:
        """Return a snapshot list of recorded outbound calls."""
        with self._lock:
            return list(self._records)

    @staticmethod
    def calculate_expected_calls(
        clause_count: int,
        batch_size: int = 4,
        embed_batch_size: int = 100,
    ) -> int:
        """
        Calculate expected Gemini calls for a document:
        1 classification + ceil(clauses/embed_batch_size) + ceil(clauses/batch_size) + 1 summary
        """
        if clause_count <= 0:
            return 2  # 1 classification + 1 summary
        classify_calls = 1
        embed_calls = max(1, math.ceil(clause_count / max(1, embed_batch_size)))
        batch_calls = max(1, math.ceil(clause_count / max(1, batch_size)))
        summary_calls = 1
        return classify_calls + embed_calls + batch_calls + summary_calls

    @staticmethod
    def calculate_document_budget(
        clause_count: int,
        multiplier: float = 1.5,
        batch_size: int = 4,
        embed_batch_size: int = 100,
    ) -> int:
        """
        Calculate maximum allowed calls for a document (default 1.5x expected calls).
        Enforces a minimum floor of 4 calls.
        """
        expected = CallLedger.calculate_expected_calls(
            clause_count, batch_size=batch_size, embed_batch_size=embed_batch_size
        )
        return max(4, math.ceil(expected * multiplier))

    def set_document_budget(self, document_id: str, budget: int) -> None:
        """Register the call budget for a specific document."""
        with self._lock:
            self._document_budgets[str(document_id)] = budget

    def get_document_budget(self, document_id: str) -> int | None:
        """Retrieve the configured call budget for a document."""
        with self._lock:
            return self._document_budgets.get(str(document_id))

    def check_budget(self, document_id: str) -> None:
        """
        Verify that document has not exceeded its call budget.
        Raises CallBudgetExceededError if exceeded.
        """
        doc_id_str = str(document_id)
        with self._lock:
            budget = self._document_budgets.get(doc_id_str)
            if budget is not None:
                current_count = len(self._document_calls.get(doc_id_str, []))
                if current_count >= budget:
                    raise CallBudgetExceededError(
                        document_id=doc_id_str,
                        current_calls=current_count,
                        budget=budget,
                    )

    def record_call(
        self,
        purpose: str | None = None,
        status: str = "ok",
        latency: float = 0.0,
        tokens: int = 0,
        model_name: str = "",
        attempt_number: int | None = None,
        job_id: str | None = None,
        document_id: str | None = None,
        user_id: str | None = None,
    ) -> CallRecord:
        """
        Record a completed or attempted outbound Gemini API call.
        Extracts contextual metadata from contextvars when not passed explicitly.
        """
        ctx = get_call_context()

        resolved_job_id = job_id or ctx.get("job_id")
        resolved_doc_id = document_id or ctx.get("document_id")
        resolved_user_id = user_id or ctx.get("user_id")
        resolved_purpose = purpose or ctx.get("purpose") or "unknown"
        resolved_attempt = attempt_number or ctx.get("attempt_number") or 1

        # Check budget before logging new call if document_id is present
        if resolved_doc_id:
            doc_id_str = str(resolved_doc_id)
            with self._lock:
                budget = self._document_budgets.get(doc_id_str)
                current_count = len(self._document_calls.get(doc_id_str, []))
                if budget is not None and current_count >= budget:
                    raise CallBudgetExceededError(
                        document_id=doc_id_str,
                        current_calls=current_count,
                        budget=budget,
                    )

        record = CallRecord(
            timestamp=datetime.now(UTC),
            job_id=str(resolved_job_id) if resolved_job_id else None,
            document_id=str(resolved_doc_id) if resolved_doc_id else None,
            user_id=str(resolved_user_id) if resolved_user_id else None,
            purpose=str(resolved_purpose),
            attempt_number=resolved_attempt,
            status=status,
            latency=round(latency, 4),
            tokens=tokens,
            model_name=model_name,
        )

        with self._lock:
            self._records.append(record)
            if record.document_id:
                if record.document_id not in self._document_calls:
                    self._document_calls[record.document_id] = []
                self._document_calls[record.document_id].append(record)

        logger.debug(
            "gemini_call_recorded",
            purpose=record.purpose,
            status=record.status,
            attempt=record.attempt_number,
            latency=record.latency,
            tokens=record.tokens,
            document_id=record.document_id,
        )
        return record

    def get_document_calls_count(self, document_id: str) -> int:
        """Get total number of calls recorded for a document."""
        with self._lock:
            return len(self._document_calls.get(str(document_id), []))

    def get_document_summary(self, document_id: str) -> dict[str, Any]:
        """Produce post-job telemetry summary for a specific document."""
        doc_id_str = str(document_id)
        with self._lock:
            records = list(self._document_calls.get(doc_id_str, []))
            budget = self._document_budgets.get(doc_id_str)

        calls_by_purpose: dict[str, int] = {}
        calls_by_status: dict[str, int] = {}
        retries = 0
        repairs = 0
        total_tokens = 0
        total_latency = 0.0

        for r in records:
            calls_by_purpose[r.purpose] = calls_by_purpose.get(r.purpose, 0) + 1
            calls_by_status[r.status] = calls_by_status.get(r.status, 0) + 1
            if (
                r.purpose == "retry"
                or r.status.startswith("429")
                or r.status == "503"
                or r.attempt_number > 1
            ):
                retries += 1
            if r.purpose == "repair" or r.status == "invalid JSON":
                repairs += 1
            total_tokens += r.tokens
            total_latency += r.latency

        return {
            "document_id": doc_id_str,
            "total_calls": len(records),
            "budget": budget,
            "calls_by_purpose": calls_by_purpose,
            "calls_by_status": calls_by_status,
            "retries": retries,
            "repairs": repairs,
            "total_tokens": total_tokens,
            "total_latency_seconds": round(total_latency, 3),
        }

    def log_job_summary(
        self,
        document_id: str,
        total_time: float,
        limiter_wait_time: float,
    ) -> dict[str, Any]:
        """
        Log calls per purpose, retries, repairs, time waiting on the limiter,
        and total time after a job completes (Part A.2).
        """
        summary = self.get_document_summary(document_id)
        summary["total_time_seconds"] = round(total_time, 3)
        summary["limiter_wait_time_seconds"] = round(limiter_wait_time, 3)

        logger.info(
            "analysis_job_call_ledger_summary",
            document_id=str(document_id),
            total_calls=summary["total_calls"],
            budget=summary["budget"],
            calls_by_purpose=summary["calls_by_purpose"],
            retries=summary["retries"],
            repairs=summary["repairs"],
            limiter_wait_time_seconds=summary["limiter_wait_time_seconds"],
            total_time_seconds=summary["total_time_seconds"],
            status_breakdown=summary["calls_by_status"],
            total_tokens=summary["total_tokens"],
        )
        return summary

    def get_today_summary(self, target_date_str: str | None = None) -> dict[str, Any]:
        """
        Retrieve aggregated calls for today UTC (or target date)
        grouped by purpose and status for direct comparison with AI Studio.
        """
        date_str = target_date_str or datetime.now(UTC).strftime("%Y-%m-%d")

        with self._lock:
            all_records = list(self._records)

        day_records = [r for r in all_records if r.timestamp.strftime("%Y-%m-%d") == date_str]

        calls_by_purpose: dict[str, int] = {
            "embed": 0,
            "classify": 0,
            "analyze": 0,
            "repair": 0,
            "retry": 0,
            "summary": 0,
            "unknown": 0,
        }
        calls_by_status: dict[str, int] = {}
        total_tokens = 0
        total_retries = 0
        total_repairs = 0
        total_latency = 0.0

        for r in day_records:
            p = r.purpose if r.purpose in calls_by_purpose else "unknown"
            calls_by_purpose[p] += 1
            calls_by_status[r.status] = calls_by_status.get(r.status, 0) + 1
            if (
                r.purpose == "retry"
                or r.status.startswith("429")
                or r.status == "503"
                or r.attempt_number > 1
            ):
                total_retries += 1
            if r.purpose == "repair" or r.status == "invalid JSON":
                total_repairs += 1
            total_tokens += r.tokens
            total_latency += r.latency

        avg_latency = round(total_latency / len(day_records), 3) if day_records else 0.0

        return {
            "date": date_str,
            "total_calls": len(day_records),
            "calls_by_purpose": calls_by_purpose,
            "calls_by_status": calls_by_status,
            "total_tokens": total_tokens,
            "total_retries": total_retries,
            "total_repairs": total_repairs,
            "average_latency_seconds": avg_latency,
            "recent_calls": [r.model_dump(mode="json") for r in day_records[-50:]],
        }

    def get_today_calls_by_purpose(self, target_date_str: str | None = None) -> dict[str, int]:
        """Convenience method returning {purpose: count} for today UTC."""
        summary = self.get_today_summary(target_date_str)
        return summary["calls_by_purpose"]

    def format_today_table(self, target_date_str: str | None = None) -> str:
        """
        Format today's call ledger metrics into an ASCII table
        ready for CLI display and comparison with Google AI Studio.
        """
        summary = self.get_today_summary(target_date_str)
        date_str = summary["date"]
        total = summary["total_calls"]
        purposes = summary["calls_by_purpose"]
        statuses = summary["calls_by_status"]

        lines = [
            f"=== GEMINI CALL LEDGER [{date_str} UTC] ===",
            f"Total Outbound Requests: {total} (RPD equivalent in AI Studio)",
            f"Total Tokens Consumed:   {summary['total_tokens']:,}",
            f"Total Retries (429/503): {summary['total_retries']}",
            f"Total Schema Repairs:    {summary['total_repairs']}",
            f"Average Latency:         {summary['average_latency_seconds']}s",
            "",
            "--- Calls by Purpose ---",
            f"{'Purpose':<15} | {'Count':<8} | {'Share (%)':<10}",
            "-" * 38,
        ]

        for p, count in purposes.items():
            pct = f"{(count / total * 100):.1f}%" if total > 0 else "0.0%"
            lines.append(f"{p:<15} | {count:<8} | {pct:<10}")

        lines.extend(
            [
                "-" * 38,
                "",
                "--- Calls by Status ---",
                f"{'Status':<18} | {'Count':<8}",
                "-" * 30,
            ]
        )
        for s, count in statuses.items():
            lines.append(f"{s:<18} | {count:<8}")
        lines.append("-" * 30)
        lines.append(
            "Note: In Google AI Studio, check Requests Per Day (RPD) to cross-verify Total Outbound Requests."
        )

        return "\n".join(lines)


# Global singleton instance
_call_ledger_instance: CallLedger | None = None
_instance_lock = threading.Lock()


def get_call_ledger() -> CallLedger:
    """Obtain or initialize the global CallLedger singleton."""
    global _call_ledger_instance
    if _call_ledger_instance is None:
        with _instance_lock:
            if _call_ledger_instance is None:
                _call_ledger_instance = CallLedger()
    return _call_ledger_instance


# CLI entry point
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Query Gemini Outbound Call Ledger")
    parser.add_argument("--today", action="store_true", help="Display today's calls by purpose")
    parser.add_argument("--date", type=str, default=None, help="Specific date YYYY-MM-DD")
    parser.add_argument("--doc", type=str, default=None, help="Document ID for specific summary")
    parser.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args()
    ledger = get_call_ledger()

    if args.doc:
        doc_summary = ledger.get_document_summary(args.doc)
        if args.json:
            import json

            print(json.dumps(doc_summary, indent=2))
        else:
            print(f"=== Document Summary [{args.doc}] ===")
            print(f"Total Calls: {doc_summary['total_calls']} / Budget: {doc_summary['budget']}")
            print(f"Calls by Purpose: {doc_summary['calls_by_purpose']}")
            print(f"Retries: {doc_summary['retries']}, Repairs: {doc_summary['repairs']}")
            print(
                f"Latency: {doc_summary['total_latency_seconds']}s, Tokens: {doc_summary['total_tokens']}"
            )
    else:
        if args.json:
            import json

            print(json.dumps(ledger.get_today_summary(args.date), indent=2))
        else:
            print(ledger.format_today_table(args.date))
