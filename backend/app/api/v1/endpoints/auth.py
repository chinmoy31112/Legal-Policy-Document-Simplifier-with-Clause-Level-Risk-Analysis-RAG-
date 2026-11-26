"""
Authentication endpoints.

Handles user registration, login, token refresh, and profile retrieval.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_user_id
from app.dependencies import get_db_session
from app.schemas.auth import (
    TokenRefresh,
    TokenResponse,
    UserLogin,
    UserRegister,
    UserResponse,
)
from app.schemas.common import APIResponse
from app.services.auth_service import AuthService

router = APIRouter()


@router.post(
    "/register",
    response_model=APIResponse[UserResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    description="Create a new user account with email, password, and full name.",
)
async def register(
    payload: UserRegister,
    session: Annotated[AsyncSession, Depends(get_db_session)],
):
    """Register a new user account."""
    service = AuthService(session)
    user = await service.register(
        email=payload.email,
        password=payload.password,
        full_name=payload.full_name,
    )
    return APIResponse(
        data=UserResponse.model_validate(user),
        message="Registration successful.",
    )


@router.post(
    "/login",
    response_model=APIResponse[TokenResponse],
    summary="User login",
    description="Authenticate with email and password. Returns access and refresh tokens.",
)
async def login(
    payload: UserLogin,
    session: Annotated[AsyncSession, Depends(get_db_session)],
):
    """Authenticate user and return JWT tokens."""
    service = AuthService(session)
    tokens = await service.login(email=payload.email, password=payload.password)
    return APIResponse(data=tokens, message="Login successful.")


@router.post(
    "/refresh",
    response_model=APIResponse[TokenResponse],
    summary="Refresh access token",
    description="Exchange a valid refresh token for a new access token.",
)
async def refresh_token(
    payload: TokenRefresh,
    session: Annotated[AsyncSession, Depends(get_db_session)],
):
    """Refresh an expired access token."""
    service = AuthService(session)
    tokens = await service.refresh(refresh_token_str=payload.refresh_token)
    return APIResponse(data=tokens, message="Token refreshed.")


@router.get(
    "/me",
    response_model=APIResponse[UserResponse],
    summary="Get current user profile",
    description="Returns the authenticated user's profile information.",
)
async def get_profile(
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
):
    """Get the current authenticated user's profile."""
    service = AuthService(session)
    user = await service.get_profile(user_id)
    return APIResponse(data=UserResponse.model_validate(user))


@router.delete(
    "/me",
    summary="Delete user account (Delete-My-Data)",
    description="Cancel active jobs, permanently delete user account and all uploaded documents, clauses, and analyses, and report kept metadata.",
)
async def delete_account(
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
):
    """Cancel user's jobs, delete user account and all data, and report kept records."""
    from app.api.v1.endpoints.documents import _active_analysis_tasks

    service = AuthService(session)
    report = await service.delete_account(user_id, legacy_tasks_map=_active_analysis_tasks)
    return APIResponse(
        data=report,
        message="User account and all associated data have been permanently deleted.",
    )


@router.post(
    "/delete-account",
    summary="Delete user account alias",
    description="Permanently delete the authenticated user account.",
)
async def delete_account_alias(
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
):
    """Alias for delete user account."""
    from app.api.v1.endpoints.documents import _active_analysis_tasks

    service = AuthService(session)
    report = await service.delete_account(user_id, legacy_tasks_map=_active_analysis_tasks)
    return APIResponse(
        data=report,
        message="User account and all associated data have been permanently deleted.",
    )
