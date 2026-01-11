"""
User management API endpoints.

Provides CRUD operations for users. Most endpoints require admin privileges.
"""

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from app.core.auth import get_password_hash
from app.core.deps import AdminUser
from app.db.pool import get_system_db
from app.shared.logging import get_logger
from app.shared.schemas import UserCreate, UserUpdate
from fastapi import APIRouter, HTTPException, Query, status

logger = get_logger(__name__)
router = APIRouter(prefix="/api/v1/users", tags=["users"])


def _format_user_response(user: dict[str, Any]) -> dict[str, Any]:
    """Format user record for API response."""
    return {
        "user_id": str(user["user_id"]),
        "email": user["email"],
        "full_name": user["full_name"],
        "role": user["role"],
        "is_active": user["is_active"],
        "created_at": (
            user["created_at"].isoformat() if user.get("created_at") else None
        ),
        "updated_at": (
            user["updated_at"].isoformat() if user.get("updated_at") else None
        ),
    }


@router.get("")
async def list_users(
    admin_user: AdminUser,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> dict:
    """
    List all users. Requires admin privileges.

    Args:
        admin_user: The authenticated admin user.
        limit: Maximum number of users to return.
        offset: Number of users to skip.

    Returns:
        List of users with total count.
    """
    async with get_system_db() as conn:
        rows = await conn.fetch(
            """
            SELECT user_id, email, full_name, role, is_active, created_at, updated_at
            FROM users
            ORDER BY created_at DESC
            LIMIT $1 OFFSET $2
            """,
            limit,
            offset,
        )

        count_row = await conn.fetchrow("SELECT COUNT(*) as total FROM users")
        total = count_row["total"] if count_row else 0

    users = [_format_user_response(dict(row)) for row in rows]

    return {
        "success": True,
        "data": users,
        "total": total,
    }


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_user(request: UserCreate, admin_user: AdminUser) -> dict:
    """
    Create a new user. Requires admin privileges.

    Args:
        request: User creation data.
        admin_user: The authenticated admin user.

    Returns:
        Created user data.

    Raises:
        HTTPException: If email already exists.
    """
    async with get_system_db() as conn:
        # Check if email already exists
        existing = await conn.fetchrow(
            "SELECT user_id FROM users WHERE email = $1",
            request.email,
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )

        # Create user
        password_hash = get_password_hash(request.password)
        now = datetime.now(timezone.utc)

        row = await conn.fetchrow(
            """
            INSERT INTO users (email, password_hash, full_name, role, is_active, created_at, updated_at)
            VALUES ($1, $2, $3, $4, TRUE, $5, $5)
            RETURNING user_id, email, full_name, role, is_active, created_at, updated_at
            """,
            request.email,
            password_hash,
            request.full_name,
            request.role,
            now,
        )

    user = dict(row)
    logger.info(
        "user_created",
        user_id=str(user["user_id"]),
        email=user["email"],
        created_by=str(admin_user["user_id"]),
    )

    return {
        "success": True,
        "data": _format_user_response(user),
    }


@router.get("/{user_id}")
async def get_user(user_id: UUID, admin_user: AdminUser) -> dict:
    """
    Get a user by ID. Requires admin privileges.

    Args:
        user_id: The UUID of the user to fetch.
        admin_user: The authenticated admin user.

    Returns:
        User data.

    Raises:
        HTTPException: If user not found.
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

    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return {
        "success": True,
        "data": _format_user_response(dict(row)),
    }


@router.patch("/{user_id}")
async def update_user(
    user_id: UUID,
    request: UserUpdate,
    admin_user: AdminUser,
) -> dict:
    """
    Update a user. Requires admin privileges.

    Args:
        user_id: The UUID of the user to update.
        request: User update data.
        admin_user: The authenticated admin user.

    Returns:
        Updated user data.

    Raises:
        HTTPException: If user not found or email conflict.
    """
    async with get_system_db() as conn:
        # Check if user exists
        existing = await conn.fetchrow(
            "SELECT user_id FROM users WHERE user_id = $1",
            user_id,
        )
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        # Check email uniqueness if updating email
        if request.email:
            email_check = await conn.fetchrow(
                "SELECT user_id FROM users WHERE email = $1 AND user_id != $2",
                request.email,
                user_id,
            )
            if email_check:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already registered",
                )

        # Build update query dynamically
        updates = []
        params = []
        param_idx = 1

        if request.email is not None:
            updates.append(f"email = ${param_idx}")
            params.append(request.email)
            param_idx += 1

        if request.full_name is not None:
            updates.append(f"full_name = ${param_idx}")
            params.append(request.full_name)
            param_idx += 1

        if request.password is not None:
            updates.append(f"password_hash = ${param_idx}")
            params.append(get_password_hash(request.password))
            param_idx += 1

        if request.role is not None:
            updates.append(f"role = ${param_idx}")
            params.append(request.role)
            param_idx += 1

        if request.is_active is not None:
            updates.append(f"is_active = ${param_idx}")
            params.append(request.is_active)
            param_idx += 1

        if not updates:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No fields to update",
            )

        # Add updated_at
        updates.append(f"updated_at = ${param_idx}")
        params.append(datetime.now(timezone.utc))
        param_idx += 1

        # Add user_id for WHERE clause
        params.append(user_id)

        query = f"""
            UPDATE users
            SET {', '.join(updates)}
            WHERE user_id = ${param_idx}
            RETURNING user_id, email, full_name, role, is_active, created_at, updated_at
        """

        row = await conn.fetchrow(query, *params)

    user = dict(row)
    logger.info(
        "user_updated",
        user_id=str(user["user_id"]),
        updated_by=str(admin_user["user_id"]),
    )

    return {
        "success": True,
        "data": _format_user_response(user),
    }


@router.delete("/{user_id}")
async def delete_user(user_id: UUID, admin_user: AdminUser) -> dict:
    """
    Delete a user. Requires admin privileges.

    Admins cannot delete themselves.

    Args:
        user_id: The UUID of the user to delete.
        admin_user: The authenticated admin user.

    Returns:
        Success message.

    Raises:
        HTTPException: If user not found or trying to delete self.
    """
    if user_id == admin_user["user_id"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account",
        )

    async with get_system_db() as conn:
        result = await conn.execute(
            "DELETE FROM users WHERE user_id = $1",
            user_id,
        )

    if result == "DELETE 0":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    logger.info(
        "user_deleted",
        user_id=str(user_id),
        deleted_by=str(admin_user["user_id"]),
    )

    return {
        "success": True,
        "message": "User deleted successfully",
    }
