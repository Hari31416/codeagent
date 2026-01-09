"""
CodingAgent Error Handling

Custom exception classes and FastAPI exception handlers.
All exceptions follow a consistent structure for API responses.
"""

from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.shared.logging import get_logger
from app.shared.models import ErrorResponse

logger = get_logger(__name__)


# =============================================================================
# Base Exception
# =============================================================================


class CodingAgentError(Exception):
    """
    Base exception for all CodingAgent application errors.

    All custom exceptions should inherit from this class.
    """

    status_code: int = 500
    error_code: str = "INTERNAL_ERROR"

    def __init__(
        self,
        message: str = "An unexpected error occurred",
        error_code: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        self.message = message
        if error_code:
            self.error_code = error_code
        self.details = details
        super().__init__(self.message)


# =============================================================================
# Authentication & Authorization Errors
# =============================================================================


class AuthenticationError(CodingAgentError):
    """Raised when authentication fails (401)."""

    status_code = 401
    error_code = "AUTH_FAILED"

    def __init__(
        self,
        message: str = "Authentication failed",
        error_code: str = "AUTH_FAILED",
        details: dict[str, Any] | None = None,
    ):
        super().__init__(message, error_code, details)


class InvalidTokenError(AuthenticationError):
    """Raised when JWT token is invalid or expired."""

    error_code = "AUTH_INVALID_TOKEN"

    def __init__(self, message: str = "Invalid or expired token"):
        super().__init__(message, self.error_code)


class InvalidCredentialsError(AuthenticationError):
    """Raised when login credentials are incorrect."""

    error_code = "AUTH_INVALID_CREDENTIALS"

    def __init__(self, message: str = "Invalid email or password"):
        super().__init__(message, self.error_code)


class AuthorizationError(CodingAgentError):
    """Raised when user lacks permission for an action (403)."""

    status_code = 403
    error_code = "FORBIDDEN"

    def __init__(
        self,
        message: str = "You do not have permission to perform this action",
        error_code: str = "FORBIDDEN",
        details: dict[str, Any] | None = None,
    ):
        super().__init__(message, error_code, details)


class InsufficientRoleError(AuthorizationError):
    """Raised when user role is insufficient for the action."""

    error_code = "INSUFFICIENT_ROLE"

    def __init__(self, required_role: str):
        super().__init__(
            message=f"This action requires {required_role} role",
            error_code=self.error_code,
            details={"required_role": required_role},
        )


# =============================================================================
# Resource Errors
# =============================================================================


class NotFoundError(CodingAgentError):
    """Raised when a requested resource is not found (404)."""

    status_code = 404
    error_code = "NOT_FOUND"

    def __init__(
        self,
        resource: str = "Resource",
        resource_id: str | None = None,
    ):
        message = f"{resource} not found"
        details = None
        if resource_id:
            message = f"{resource} with ID '{resource_id}' not found"
            details = {"resource": resource, "resource_id": resource_id}
        super().__init__(message, self.error_code, details)


class ConflictError(CodingAgentError):
    """Raised when there's a conflict with existing data (409)."""

    status_code = 409
    error_code = "CONFLICT"

    def __init__(
        self,
        message: str = "Resource already exists",
        error_code: str = "CONFLICT",
        details: dict[str, Any] | None = None,
    ):
        super().__init__(message, error_code, details)


class DuplicateEmailError(ConflictError):
    """Raised when attempting to create user with existing email."""

    error_code = "DUPLICATE_EMAIL"

    def __init__(self, email: str):
        super().__init__(
            message=f"User with email '{email}' already exists",
            error_code=self.error_code,
            details={"email": email},
        )


# =============================================================================
# Validation & Input Errors
# =============================================================================


class ValidationError(CodingAgentError):
    """Raised when input validation fails (422)."""

    status_code = 422
    error_code = "VALIDATION_ERROR"

    def __init__(
        self,
        message: str = "Validation failed",
        details: dict[str, Any] | None = None,
    ):
        super().__init__(message, self.error_code, details)


class QuotaExceededError(CodingAgentError):
    """Raised when user exceeds their quota (429)."""

    status_code = 429
    error_code = "QUOTA_EXCEEDED"

    def __init__(
        self,
        resource: str,
        limit: int,
        current: int,
    ):
        super().__init__(
            message=f"{resource} quota exceeded: {current}/{limit}",
            error_code=self.error_code,
            details={"resource": resource, "limit": limit, "current": current},
        )


class RateLimitError(CodingAgentError):
    """Raised when rate limit is exceeded (429)."""

    status_code = 429
    error_code = "RATE_LIMITED"

    def __init__(
        self,
        message: str = "Too many requests. Please try again later.",
        retry_after: int | None = None,
    ):
        details = {"retry_after": retry_after} if retry_after else None
        super().__init__(message, self.error_code, details)


# =============================================================================
# External Service Errors
# =============================================================================


class ExternalServiceError(CodingAgentError):
    """Raised when an external service fails (502)."""

    status_code = 502
    error_code = "EXTERNAL_SERVICE_ERROR"

    def __init__(
        self,
        service: str,
        message: str | None = None,
    ):
        msg = message or f"External service '{service}' is unavailable"
        super().__init__(msg, self.error_code, {"service": service})


class DatabaseError(CodingAgentError):
    """Raised when database operation fails (500)."""

    status_code = 500
    error_code = "DATABASE_ERROR"

    def __init__(
        self,
        message: str = "Database operation failed",
        details: dict[str, Any] | None = None,
    ):
        super().__init__(message, self.error_code, details)


class CacheError(CodingAgentError):
    """Raised when cache operation fails (non-critical, logged as warning)."""

    status_code = 500
    error_code = "CACHE_ERROR"

    def __init__(
        self,
        message: str = "Cache operation failed",
        details: dict[str, Any] | None = None,
    ):
        super().__init__(message, self.error_code, details)


# =============================================================================
# Exception Handlers
# =============================================================================


async def codingagent_exception_handler(request: Request, exc: CodingAgentError) -> JSONResponse:
    """Handle all CodingAgentError exceptions."""
    request_id = getattr(request.state, "request_id", None)

    logger.warning(
        "Application error",
        error_code=exc.error_code,
        message=exc.message,
        status_code=exc.status_code,
        path=request.url.path,
    )

    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error=exc.message,
            error_code=exc.error_code,
            details=(
                [{"message": str(v), "field": k} for k, v in exc.details.items()]
                if exc.details
                else None
            ),
            request_id=request_id,
        ).model_dump(),
    )


async def http_exception_handler(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    """Handle standard HTTP exceptions."""
    request_id = getattr(request.state, "request_id", None)

    logger.warning(
        "HTTP error",
        status_code=exc.status_code,
        detail=exc.detail,
        path=request.url.path,
    )

    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error=str(exc.detail),
            error_code=f"HTTP_{exc.status_code}",
            request_id=request_id,
        ).model_dump(),
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Handle Pydantic validation errors."""
    request_id = getattr(request.state, "request_id", None)

    errors = exc.errors()
    details = []
    for error in errors:
        field = ".".join(str(loc) for loc in error["loc"][1:])  # Skip 'body'
        details.append({"field": field, "message": error["msg"]})

    logger.warning(
        "Validation error",
        errors=errors,
        path=request.url.path,
    )

    return JSONResponse(
        status_code=422,
        content=ErrorResponse(
            error="Validation failed",
            error_code="VALIDATION_ERROR",
            details=details,
            request_id=request_id,
        ).model_dump(),
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected exceptions."""
    request_id = getattr(request.state, "request_id", None)

    logger.exception(
        "Unexpected error",
        error=str(exc),
        error_type=type(exc).__name__,
        path=request.url.path,
    )

    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="An unexpected error occurred",
            error_code="INTERNAL_ERROR",
            request_id=request_id,
        ).model_dump(),
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Register all exception handlers with the FastAPI app."""
    app.add_exception_handler(CodingAgentError, codingagent_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)
