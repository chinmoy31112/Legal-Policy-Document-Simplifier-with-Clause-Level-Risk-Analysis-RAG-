"""
Job repository — data access layer for persistent analysis jobs.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document
from app.models.job import Job
from app.models.user import User
from app.repositories.base import BaseRepository


class JobRepository(BaseRepository[Job]):
    """Repository for Job CRUD, state transitions, cancellation, and orphan reaping."""

    def __init__(self, session: AsyncSession):
        super().__init__(Job, session)

    async def get_latest_for_document(self, document_id: UUID) -> Job | None:
        """Return the most recent Job record for a document."""
        query = (
            select(Job)
            .where(Job.document_id == document_id)
            .order_by(Job.created_at.desc())
            .limit(1)
        )
        res = await self.session.execute(query)
        return res.scalar_one_or_none()

    async def get_active_for_document(self, document_id: UUID) -> list[Job]:
        """Return queued/running/waiting_for_quota/cancelling jobs for a document."""
        query = select(Job).where(
            Job.document_id == document_id,
            Job.status.in_(["queued", "running", "waiting_for_quota", "cancelling"]),
        )
        res = await self.session.execute(query)
        return list(res.scalars().all())

    async def get_active_for_user(self, user_id: UUID) -> list[Job]:
        """Return all non-terminal jobs belonging to a user."""
        query = select(Job).where(
            Job.user_id == user_id,
            Job.status.in_(["queued", "running", "waiting_for_quota", "cancelling"]),
        )
        res = await self.session.execute(query)
        return list(res.scalars().all())

    async def mark_cancelling_for_document(self, document_id: UUID) -> list[Job]:
        """Atomically flag active jobs for a document as cancelling."""
        active = await self.get_active_for_document(document_id)
        if not active:
            return []
        await self.session.execute(
            update(Job)
            .where(
                Job.document_id == document_id,
                Job.status.in_(["queued", "running", "waiting_for_quota", "cancelling"]),
            )
            .values(
                cancel_requested=True,
                status="cancelling",
                updated_at=datetime.now(UTC).replace(tzinfo=None),
            )
        )
        return active

    async def mark_cancelling_for_user(self, user_id: UUID) -> list[Job]:
        """Atomically flag all active jobs belonging to a user as cancelling."""
        active = await self.get_active_for_user(user_id)
        if not active:
            return []
        await self.session.execute(
            update(Job)
            .where(
                Job.user_id == user_id,
                Job.status.in_(["queued", "running", "waiting_for_quota", "cancelling"]),
            )
            .values(
                cancel_requested=True,
                status="cancelling",
                updated_at=datetime.now(UTC).replace(tzinfo=None),
            )
        )
        return active

    async def mark_interrupted_on_startup(self) -> int:
        """
        Mark any jobs left in 'running' state after an unclean shutdown/restart as 'interrupted'.
        Jobs that had cancel_requested=True or 'cancelling' are finalized as 'cancelled'.
        """
        now = datetime.now(UTC).replace(tzinfo=None)
        res_cancel = await self.session.execute(
            update(Job)
            .where(
                Job.status.in_(["running", "cancelling"]),
                Job.cancel_requested.is_(True),
            )
            .values(
                status="cancelled",
                stage="cancelled",
                completed_at=now,
                updated_at=now,
            )
        )
        res_interrupt = await self.session.execute(
            update(Job)
            .where(Job.status == "running")
            .values(
                status="interrupted",
                stage="interrupted",
                error_message="Job interrupted by server or worker restart.",
                updated_at=now,
            )
        )
        # Sync any documents stuck in active processing stages back to interrupted/failed
        await self.session.execute(
            update(Document)
            .where(Document.status.in_(["extracting", "segmenting", "analyzing"]))
            .values(status="failed", updated_at=now)
        )
        return int((res_cancel.rowcount or 0) + (res_interrupt.rowcount or 0))

    async def find_orphan_jobs(self) -> list[Job]:
        """Find jobs whose referenced document or user no longer exists."""
        valid_docs = select(Document.id)
        valid_users = select(User.id)
        query = select(Job).where(
            (Job.document_id.is_(None))
            | (~Job.document_id.in_(valid_docs))
            | (Job.user_id.is_(None))
            | (~Job.user_id.in_(valid_users))
        )
        res = await self.session.execute(query)
        return list(res.scalars().all())

    async def find_waiting_quota_jobs(self) -> list[Job]:
        """Find non-cancelled waiting_for_quota jobs whose documents still exist."""
        valid_docs = select(Document.id)
        query = select(Job).where(
            Job.status == "waiting_for_quota",
            Job.cancel_requested.is_(False),
            Job.document_id.is_not(None),
            Job.document_id.in_(valid_docs),
        )
        res = await self.session.execute(query)
        return list(res.scalars().all())

    async def delete_for_document(self, document_id: UUID) -> int:
        """Delete all job rows for a document."""
        res = await self.session.execute(delete(Job).where(Job.document_id == document_id))
        return int(res.rowcount or 0)

    async def delete_for_user(self, user_id: UUID) -> int:
        """Delete all job rows for a user."""
        res = await self.session.execute(delete(Job).where(Job.user_id == user_id))
        return int(res.rowcount or 0)
