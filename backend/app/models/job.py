"""
Job ORM model for persistent background document analysis tracking.

Tracks lifecycle state, stage, progress, and cancellation flags in PostgreSQL
so jobs survive API restarts and can be cleanly cancelled/reaped across workers.
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, TimestampMixin, UUIDMixin

JOB_STATES = (
    "queued",
    "running",
    "waiting_for_quota",
    "cancelling",
    "cancelled",
    "failed",
    "completed",
    "interrupted",
)


class Job(Base, UUIDMixin, TimestampMixin):
    """Persistent analysis job tied to a document and user."""

    __tablename__ = "jobs"

    # Intentionally stored without CASCADE FK so the periodic reaper can detect
    # and clean up any orphaned jobs if a document or user is deleted out-of-band.
    document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        index=True,
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        index=True,
    )
    arq_job_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="queued", index=True)
    stage: Mapped[str | None] = mapped_column(String(100), nullable=True, default="queued")
    total_clauses: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    completed_clauses: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cancel_requested: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, index=True
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(nullable=True)

    def __repr__(self) -> str:
        return (
            f"<Job(id={self.id}, document_id={self.document_id}, "
            f"status={self.status}, cancel_requested={self.cancel_requested})>"
        )
