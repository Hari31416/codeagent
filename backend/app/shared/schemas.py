"""
Pydantic schemas for authentication and user management.
"""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

# ─────────────────────────────────────────────────────────────────────────────
# Authentication Schemas
# ─────────────────────────────────────────────────────────────────────────────


class LoginRequest(BaseModel):
    """Request model for user login."""

    email: EmailStr
    password: str = Field(..., min_length=6)


class TokenResponse(BaseModel):
    """Response model for authentication tokens."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshTokenRequest(BaseModel):
    """Request model for token refresh."""

    refresh_token: str


# ─────────────────────────────────────────────────────────────────────────────
# User Schemas
# ─────────────────────────────────────────────────────────────────────────────


class UserBase(BaseModel):
    """Base user schema with common fields."""

    email: EmailStr
    full_name: str | None = None


class UserCreate(UserBase):
    """Schema for creating a new user."""

    password: str = Field(..., min_length=6)
    role: Literal["admin", "user"] = "user"


class UserUpdate(BaseModel):
    """Schema for updating an existing user."""

    email: EmailStr | None = None
    full_name: str | None = None
    password: str | None = Field(None, min_length=6)
    role: Literal["admin", "user"] | None = None
    is_active: bool | None = None


class UserResponse(BaseModel):
    """Response model for user data."""

    user_id: UUID
    email: str
    full_name: str | None
    role: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        """Pydantic config for ORM mode."""

        from_attributes = True


class UserListResponse(BaseModel):
    """Response model for list of users."""

    success: bool = True
    data: list[UserResponse]
    total: int
