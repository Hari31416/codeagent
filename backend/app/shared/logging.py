"""
CodingAgent Logging Module

Structured logging using structlog.
- JSON format in production
- Colorful console output in development
"""

import logging
import sys
from typing import Any

import structlog
from structlog.types import Processor

from app.config import settings


def configure_logging() -> None:
    """Configure structlog for the application."""

    # Shared processors for all environments
    shared_processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
    ]

    if settings.environment == "production":
        # JSON logging for production (easy to parse, ship to log aggregators)
        shared_processors.append(structlog.processors.format_exc_info)
        shared_processors.append(structlog.processors.JSONRenderer())
    else:
        # Pretty console logging for development
        # Only use colors if stdout is a TTY (not redirected to a file)
        use_colors = sys.stdout.isatty()

        # Use plain text exception formatting when not on TTY
        # to avoid ANSI codes in log files
        if use_colors:
            # Rich tracebacks for interactive terminal
            shared_processors.append(structlog.dev.ConsoleRenderer(colors=True))
        else:
            # Plain text for file output - no Rich tracebacks
            shared_processors.append(structlog.processors.format_exc_info)
            shared_processors.append(
                structlog.dev.ConsoleRenderer(
                    colors=False,
                    exception_formatter=structlog.dev.plain_traceback,
                )
            )

    _configure_stdlib_logging()

    structlog.configure(
        processors=shared_processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def _configure_stdlib_logging() -> None:
    """
    Configure standard library logging.

    Sets root logger conservatively and application loggers to user-configured level.
    """
    # Configure standard library logging - set root logger conservatively
    # to prevent third-party libraries from logging at debug level
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=logging.WARNING,
    )

    # Set application loggers to user-configured level
    app_level = getattr(logging, settings.log_level.upper())
    for app_logger_name in ["app", "codingagent"]:
        logging.getLogger(app_logger_name).setLevel(app_level)

    # Keep specific noisy loggers quiet
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """
    Get a logger instance.

    Args:
        name: Logger name (typically __name__ of the calling module)

    Returns:
        Configured structlog logger

    Example:
        >>> from app.shared.logging import get_logger
        >>> logger = get_logger(__name__)
        >>> logger.info("Processing file", file_id="abc123", size_bytes=1024)
    """
    return structlog.get_logger(name)


def bind_context(**kwargs: Any) -> None:
    """
    Bind context variables to all subsequent log messages.
    Useful for request-scoped context like request_id, user_id.

    Example:
        >>> bind_context(request_id="req-123", user_id="user-456")
        >>> logger.info("Processing request")  # Will include request_id and user_id
    """
    structlog.contextvars.bind_contextvars(**kwargs)


def clear_context() -> None:
    """Clear all bound context variables."""
    structlog.contextvars.clear_contextvars()


# Initialize logging on module import
configure_logging()

# Default logger instance
logger = get_logger("codingagent")
