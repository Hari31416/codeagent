"""
Authentication API endpoints.

Handles user login, token refresh, and profile retrieval.
"""

from datetime import datetime, timezone
from typing import Any

from app.core.auth import (
    create_access_token,
    create_refresh_token,
    verify_password,
    verify_token,
)
from app.core.deps import CurrentActiveUser
from app.db.pool import get_system_db
from app.shared.logging import get_logger
from app.shared.schemas import LoginRequest, RefreshTokenRequest, TokenResponse
from fastapi import APIRouter, HTTPException, status

logger = get_logger(__name__)
router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


async def authenticate_user(email: str, password: str) -> dict[str, Any] | None:
    """
    Authenticate a user by email and password.

    Args:
        email: The user's email address.
        password: The plain text password.

    Returns:
        User record if authentication succeeds, None otherwise.
    """
    async with get_system_db() as conn:
        row = await conn.fetchrow(
            """
            SELECT user_id, email, password_hash, full_name, role, is_active
            FROM users
            WHERE email = $1
            """,
            email,
        )

    if row is None:
        logger.warning("auth_user_not_found", email=email)
        return None

    user = dict(row)

    if not verify_password(password, user["password_hash"]):
        logger.warning("auth_invalid_password", email=email)
        return None

    if not user["is_active"]:
        logger.warning("auth_inactive_user", email=email)
        return None

    return user


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest) -> TokenResponse:
    """
    Authenticate user and return access and refresh tokens.

    Args:
        request: Login credentials (email and password).

    Returns:
        Access and refresh tokens.

    Raises:
        HTTPException: If authentication fails.
    """
    user = await authenticate_user(request.email, request.password)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Update last_login timestamp
    async with get_system_db() as conn:
        await conn.execute(
            """
            UPDATE users SET last_login = $1 WHERE user_id = $2
            """,
            datetime.now(timezone.utc),
            user["user_id"],
        )

    # Create tokens with user role in claims
    access_token = create_access_token(
        subject=str(user["user_id"]),
        additional_claims={"role": user["role"]},
    )
    refresh_token = create_refresh_token(subject=str(user["user_id"]))

    logger.info("user_logged_in", user_id=str(user["user_id"]), email=user["email"])

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(request: RefreshTokenRequest) -> TokenResponse:
    """
    Exchange a refresh token for a new access token.

    Args:
        request: The refresh token.

    Returns:
        New access and refresh tokens.

    Raises:
        HTTPException: If the refresh token is invalid.
    """
    user_id_str = verify_token(request.refresh_token, token_type="refresh")

    if user_id_str is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Verify user still exists and is active
    from uuid import UUID

    try:
        user_id = UUID(user_id_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    async with get_system_db() as conn:
        row = await conn.fetchrow(
            """
            SELECT user_id, role, is_active
            FROM users
            WHERE user_id = $1
            """,
            user_id,
        )

    if row is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    user = dict(row)
    if not user["is_active"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is inactive",
        )

    # Create new tokens
    access_token = create_access_token(
        subject=str(user["user_id"]),
        additional_claims={"role": user["role"]},
    )
    new_refresh_token = create_refresh_token(subject=str(user["user_id"]))

    logger.info("token_refreshed", user_id=str(user["user_id"]))

    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
    )


@router.get("/me")
async def get_current_user_profile(current_user: CurrentActiveUser) -> dict:
    """
    Get the current authenticated user's profile.

    Args:
        current_user: The authenticated user from dependency.

    Returns:
        User profile data.
    """
    return {
        "success": True,
        "data": {
            "user_id": str(current_user["user_id"]),
            "email": current_user["email"],
            "full_name": current_user["full_name"],
            "role": current_user["role"],
            "is_active": current_user["is_active"],
            "created_at": (
                current_user["created_at"].isoformat()
                if current_user.get("created_at")
                else None
            ),
            "updated_at": (
                current_user["updated_at"].isoformat()
                if current_user.get("updated_at")
                else None
            ),
        },
    }


@router.post("/logout")
async def logout(current_user: CurrentActiveUser) -> dict:
    """
    Logout the current user.

    Note: With stateless JWT, this is primarily for client-side token clearing.
    For full token invalidation, implement a token blacklist.

    Args:
        current_user: The authenticated user.

    Returns:
        Success message.
    """
    logger.info("user_logged_out", user_id=str(current_user["user_id"]))
    return {"success": True, "message": "Successfully logged out"}
