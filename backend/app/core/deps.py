"""
FastAPI dependency injection for authentication.

Provides reusable dependencies for protecting API endpoints.
"""

from typing import Annotated, Any
from uuid import UUID

from app.core.auth import verify_token
from app.db.pool import get_system_db
from app.shared.logging import get_logger
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

logger = get_logger(__name__)

# HTTP Bearer token security scheme
bearer_scheme = HTTPBearer(auto_error=False)


async def get_user_by_id(user_id: UUID) -> dict[str, Any] | None:
    """
    Fetch a user from the database by ID.

    Args:
        user_id: The UUID of the user to fetch.

    Returns:
        User record as a dict or None if not found.
    """
    async with get_system_db() as conn:
        row = await conn.fetchrow(
            """
            SELECT user_id, email, full_name, role, is_active, created_at, updated_at
            FROM users
            WHERE user_id = $1
            """,
            user_id,
        )
        if row:
            return dict(row)
        return None


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> dict[str, Any]:
    """
    Dependency to get the current authenticated user.

    Extracts and validates the JWT token from the Authorization header,
    then fetches the corresponding user from the database.

    Args:
        credentials: The HTTP Bearer credentials.

    Returns:
        The authenticated user record.

    Raises:
        HTTPException: If authentication fails.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if credentials is None:
        logger.warning("auth_missing_credentials")
        raise credentials_exception

    token = credentials.credentials
    user_id_str = verify_token(token, token_type="access")

    if user_id_str is None:
        logger.warning("auth_invalid_token")
        raise credentials_exception

    try:
        user_id = UUID(user_id_str)
    except ValueError:
        logger.warning("auth_invalid_user_id", user_id=user_id_str)
        raise credentials_exception

    user = await get_user_by_id(user_id)
    if user is None:
        logger.warning("auth_user_not_found", user_id=str(user_id))
        raise credentials_exception

    return user


async def get_current_active_user(
    current_user: Annotated[dict[str, Any], Depends(get_current_user)],
) -> dict[str, Any]:
    """
    Dependency to get the current active user.

    Args:
        current_user: The authenticated user from get_current_user.

    Returns:
        The authenticated active user record.

    Raises:
        HTTPException: If the user is inactive.
    """
    if not current_user.get("is_active", False):
        logger.warning("auth_inactive_user", user_id=str(current_user["user_id"]))
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user",
        )
    return current_user


async def require_admin(
    current_user: Annotated[dict[str, Any], Depends(get_current_active_user)],
) -> dict[str, Any]:
    """
    Dependency to require admin role.

    Args:
        current_user: The authenticated active user.

    Returns:
        The authenticated admin user record.

    Raises:
        HTTPException: If the user is not an admin.
    """
    if current_user.get("role") != "admin":
        logger.warning(
            "auth_admin_required",
            user_id=str(current_user["user_id"]),
            role=current_user.get("role"),
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )
    return current_user


# Type aliases for cleaner dependency injection
CurrentUser = Annotated[dict[str, Any], Depends(get_current_user)]
CurrentActiveUser = Annotated[dict[str, Any], Depends(get_current_active_user)]
AdminUser = Annotated[dict[str, Any], Depends(require_admin)]
