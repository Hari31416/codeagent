"""
Authentication utilities for JWT token management and password hashing.

Uses passlib for password hashing with bcrypt and python-jose for JWT tokens.
"""

from datetime import datetime, timedelta, timezone
from typing import Any

from app.config import settings
from app.shared.logging import get_logger
from jose import JWTError, jwt
from passlib.context import CryptContext

logger = get_logger(__name__)

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain password against a hash.

    Args:
        plain_password: The plain text password to verify.
        hashed_password: The hashed password to compare against.

    Returns:
        True if the password matches, False otherwise.
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    Hash a password using bcrypt.

    Args:
        password: The plain text password to hash.

    Returns:
        The hashed password.
    """
    return pwd_context.hash(password)


def create_access_token(
    subject: str,
    expires_delta: timedelta | None = None,
    additional_claims: dict[str, Any] | None = None,
) -> str:
    """
    Create a JWT access token.

    Args:
        subject: The subject of the token (typically user_id).
        expires_delta: Optional custom expiration time.
        additional_claims: Optional additional claims to include in the token.

    Returns:
        The encoded JWT token string.
    """
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.jwt_access_token_expire_minutes
        )

    to_encode = {
        "sub": str(subject),
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "access",
    }

    if additional_claims:
        to_encode.update(additional_claims)

    encoded_jwt = jwt.encode(
        to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm
    )
    return encoded_jwt


def create_refresh_token(
    subject: str,
    expires_delta: timedelta | None = None,
) -> str:
    """
    Create a JWT refresh token.

    Args:
        subject: The subject of the token (typically user_id).
        expires_delta: Optional custom expiration time.

    Returns:
        The encoded JWT refresh token string.
    """
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            days=settings.jwt_refresh_token_expire_days
        )

    to_encode = {
        "sub": str(subject),
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "refresh",
    }

    encoded_jwt = jwt.encode(
        to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm
    )
    return encoded_jwt


def decode_token(token: str) -> dict[str, Any] | None:
    """
    Decode and validate a JWT token.

    Args:
        token: The JWT token to decode.

    Returns:
        The decoded token payload or None if invalid.
    """
    try:
        payload = jwt.decode(
            token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
        )
        return payload
    except JWTError as e:
        logger.warning("jwt_decode_failed", error=str(e))
        return None


def verify_token(token: str, token_type: str = "access") -> str | None:
    """
    Verify a JWT token and return the subject (user_id).

    Args:
        token: The JWT token to verify.
        token_type: The expected token type ("access" or "refresh").

    Returns:
        The subject (user_id) if valid, None otherwise.
    """
    payload = decode_token(token)
    if payload is None:
        return None

    # Check token type
    if payload.get("type") != token_type:
        logger.warning(
            "jwt_type_mismatch",
            expected=token_type,
            got=payload.get("type"),
        )
        return None

    subject = payload.get("sub")
    if subject is None:
        logger.warning("jwt_missing_subject")
        return None

    return subject
