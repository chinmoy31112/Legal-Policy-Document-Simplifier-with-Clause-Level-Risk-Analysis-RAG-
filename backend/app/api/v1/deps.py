"""
API v1 route-level dependencies.

Authentication dependencies, pagination, and common query parameters.
"""

from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header, Query
from jose import JWTError

from app.core.security import decode_token
from app.core.exceptions import AuthenticationError
from app.schemas.common import PaginationParams


async def get_current_user_id(
    authorization: Annotated[str | None, Header()] = None,
) -> UUID:
    """
    Extract and validate user ID from the Authorization Bearer token.

    Raises:
        AuthenticationError: If the token is missing, invalid, or expired.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise AuthenticationError("Missing or invalid authorization header.")

    token = authorization.removeprefix("Bearer ").strip()

    try:
        payload = decode_token(token)
        user_id = payload.get("sub")
        token_type = payload.get("type")

        if user_id is None:
            raise AuthenticationError("Token payload missing subject.")
        if token_type != "access":
            raise AuthenticationError("Invalid token type.")

        return UUID(user_id)
    except (JWTError, ValueError) as e:
        raise AuthenticationError(f"Invalid token: {e}")


def get_pagination(
    page: Annotated[int, Query(ge=1, description="Page number")] = 1,
    page_size: Annotated[int, Query(ge=1, le=100, description="Items per page")] = 20,
) -> PaginationParams:
    """Extract and validate pagination query parameters."""
    return PaginationParams(page=page, page_size=page_size)
