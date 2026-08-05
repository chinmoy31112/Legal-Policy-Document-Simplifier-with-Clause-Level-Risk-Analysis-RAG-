"""
Authentication endpoints.

Handles user registration, login, token refresh, and profile retrieval.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.schemas.auth import (
    UserRegister,
    UserLogin,
    TokenResponse,
    TokenRefresh,
    UserResponse,
)
from app.schemas.common import APIResponse
from app.api.v1.deps import get_current_user_id

router = APIRouter()


@router.post(
    "/register",
    response_model=APIResponse[UserResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    description="Create a new user account with email, password, and full name.",
)
async def register(payload: UserRegister):
    """Register a new user account."""
    # Implementation in Phase 2
    pass


@router.post(
    "/login",
    response_model=APIResponse[TokenResponse],
    summary="User login",
    description="Authenticate with email and password. Returns access and refresh tokens.",
)
async def login(payload: UserLogin):
    """Authenticate user and return JWT tokens."""
    # Implementation in Phase 2
    pass


@router.post(
    "/refresh",
    response_model=APIResponse[TokenResponse],
    summary="Refresh access token",
    description="Exchange a valid refresh token for a new access token.",
)
async def refresh_token(payload: TokenRefresh):
    """Refresh an expired access token."""
    # Implementation in Phase 2
    pass


@router.get(
    "/me",
    response_model=APIResponse[UserResponse],
    summary="Get current user profile",
    description="Returns the authenticated user's profile information.",
)
async def get_profile(
    user_id: Annotated[UUID, Depends(get_current_user_id)],
):
    """Get the current authenticated user's profile."""
    # Implementation in Phase 2
    pass
