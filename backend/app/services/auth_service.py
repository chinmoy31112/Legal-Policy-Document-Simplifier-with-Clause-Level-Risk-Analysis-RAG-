"""
Authentication service.

Business logic for user registration, login, token refresh, and profile retrieval.
"""

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthenticationError, ValidationError
from app.core.logging import get_logger
from app.core.metrics import track_auth_failure
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.user import User
from app.repositories.user_repo import UserRepository
from app.schemas.auth import TokenResponse

logger = get_logger(__name__)


class AuthService:
    """Handles authentication business logic."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.user_repo = UserRepository(session)

    async def register(self, email: str, password: str, full_name: str) -> User:
        """
        Register a new user account.

        Raises:
            ValidationError: If the email is already taken.
        """
        if await self.user_repo.email_exists(email):
            raise ValidationError(f"Email '{email}' is already registered.")

        hashed = hash_password(password)
        user = await self.user_repo.create(
            email=email,
            hashed_password=hashed,
            full_name=full_name,
        )
        await self.session.commit()

        logger.info("user_registered", user_id=str(user.id), email=email)
        return user

    async def login(self, email: str, password: str) -> TokenResponse:
        """
        Authenticate a user and return JWT tokens.

        Raises:
            AuthenticationError: If credentials are invalid.
        """
        user = await self.user_repo.get_by_email(email)

        if user is None or not verify_password(password, user.hashed_password):
            track_auth_failure()
            raise AuthenticationError("Invalid email or password.")

        if not user.is_active:
            track_auth_failure()
            raise AuthenticationError("Account is deactivated.")

        access_token = create_access_token(subject=str(user.id))
        refresh_token = create_refresh_token(subject=str(user.id))

        logger.info("user_logged_in", user_id=str(user.id))
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
        )

    async def refresh(self, refresh_token_str: str) -> TokenResponse:
        """
        Refresh an expired access token using a valid refresh token.

        Raises:
            AuthenticationError: If the refresh token is invalid or expired.
        """
        try:
            payload = decode_token(refresh_token_str)
        except Exception:
            raise AuthenticationError("Invalid or expired refresh token.")

        if payload.get("type") != "refresh":
            raise AuthenticationError("Token is not a refresh token.")

        user_id = payload.get("sub")
        if user_id is None:
            raise AuthenticationError("Invalid token payload.")

        # Verify user still exists and is active
        user = await self.user_repo.get_by_id(UUID(user_id))
        if user is None or not user.is_active:
            raise AuthenticationError("User not found or deactivated.")

        access_token = create_access_token(subject=str(user.id))
        new_refresh_token = create_refresh_token(subject=str(user.id))

        return TokenResponse(
            access_token=access_token,
            refresh_token=new_refresh_token,
        )

    async def get_profile(self, user_id: UUID) -> User:
        """
        Get a user's profile by ID.

        Raises:
            AuthenticationError: If the user is not found.
        """
        user = await self.user_repo.get_by_id(user_id)
        if user is None:
            raise AuthenticationError("User not found.")
        return user

    async def delete_account(
        self,
        user_id: UUID,
        legacy_tasks_map: dict[UUID, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Cancel all user jobs first (DB + Redis + ARQ, waiting up to 5s), delete user account
        and all associated data (documents, clauses, results, jobs, local files, cached AI results),
        and report what is purged vs kept.
        """
        from sqlalchemy import delete, select

        from app.core.cancellation import purge_ai_caches
        from app.models.analysis import AnalysisResult, DocumentAnalysis
        from app.models.clause import Clause
        from app.models.document import Document
        from app.models.job import Job
        from app.services.job_service import JobService

        user = await self.user_repo.get_by_id(user_id)
        if user is None:
            raise AuthenticationError("User not found.")

        # 1. Cancel all queued/running jobs belonging to this user FIRST
        job_service = JobService(self.session)
        cancel_summary = await job_service.cancel_user_jobs(
            user_id=user_id,
            timeout_seconds=5.0,
            legacy_tasks_map=legacy_tasks_map,
        )

        # Capture document IDs and clause texts for AI cache invalidation prior to deletion
        doc_rows = await self.session.execute(
            select(Document.id).where(Document.user_id == user_id)
        )
        doc_ids = [row[0] for row in doc_rows.fetchall()]
        doc_id_strs = [str(did) for did in doc_ids]

        clause_texts: list[str] = []
        if doc_ids:
            cls_rows = await self.session.execute(
                select(Clause.content).where(Clause.document_id.in_(doc_ids))
            )
            clause_texts = [row[0] for row in cls_rows.fetchall() if row[0]]

        # 2. Clean up user's upload directory
        import shutil

        from app.core.config import get_settings

        cfg = get_settings()
        user_dir = cfg.upload_path / str(user_id)
        files_removed = user_dir.exists()
        if files_removed:
            shutil.rmtree(user_dir, ignore_errors=True)

        # 3. Explicitly purge results, clauses, jobs, documents, then user record
        results_count = 0
        doc_analysis_count = 0
        clauses_count = 0
        if doc_ids:
            r1 = await self.session.execute(
                delete(AnalysisResult).where(AnalysisResult.document_id.in_(doc_ids))
            )
            r2 = await self.session.execute(
                delete(DocumentAnalysis).where(DocumentAnalysis.document_id.in_(doc_ids))
            )
            r3 = await self.session.execute(delete(Clause).where(Clause.document_id.in_(doc_ids)))
            results_count = int(r1.rowcount or 0)
            doc_analysis_count = int(r2.rowcount or 0)
            clauses_count = int(r3.rowcount or 0)

        job_del = await self.session.execute(delete(Job).where(Job.user_id == user_id))
        doc_del = await self.session.execute(delete(Document).where(Document.user_id == user_id))

        await self.user_repo.delete(user_id)
        await self.session.commit()

        # 4. Purge cached AI results tied to this user or their documents
        cache_purged = await purge_ai_caches(
            document_ids=doc_id_strs,
            user_id=str(user_id),
            clause_texts=clause_texts,
        )

        report: dict[str, Any] = {
            "purged": {
                "user_id": str(user_id),
                "documents": int(doc_del.rowcount or 0),
                "clauses": clauses_count,
                "analysis_results": results_count,
                "document_analyses": doc_analysis_count,
                "jobs": int(job_del.rowcount or 0),
                "upload_directory_removed": files_removed,
                **cache_purged,
                "cancellation": cancel_summary,
            },
            "kept": {
                "audit_logs": "Anonymized (user_id set to NULL) and retained for compliance audit.",
                "call_ledger": "Aggregate API quota telemetry retained without user PII or document text.",
                "reference_clauses": "Global benchmark reference corpus unchanged.",
            },
        }
        logger.info(
            "user_account_deleted",
            user_id=str(user_id),
            purged=report["purged"],
            kept=report["kept"],
        )
        return report
