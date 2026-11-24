"""
Authentication service.

Business logic for user registration, login, token refresh, and profile retrieval.
"""

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

    async def delete_account(self, user_id: UUID) -> None:
        """
        Delete a user account and all associated data (GDPR delete-my-data).
        Cleans up local upload files and cascades deletions in DB.
        """
        user = await self.user_repo.get_by_id(user_id)
        if user is None:
            raise AuthenticationError("User not found.")

        # Clean up user's upload directory
        import shutil

        from app.core.config import get_settings

        cfg = get_settings()
        user_dir = cfg.upload_path / str(user_id)
        if user_dir.exists():
            shutil.rmtree(user_dir, ignore_errors=True)

        # Explicitly delete user documents first to purge all cascade records
        from sqlalchemy import delete

        from app.models.document import Document
        await self.session.execute(delete(Document).where(Document.user_id == user_id))

        # Delete user record
        await self.user_repo.delete(user_id)
        await self.session.commit()
        logger.info("user_account_deleted", user_id=str(user_id))
