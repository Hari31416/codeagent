"""
Session state service using Redis.

Uses the existing CacheService from app/core/cache.py
"""

from typing import Any
from uuid import UUID

from app.core.cache import cache  # Singleton CacheService instance
from app.shared.logging import get_logger

logger = get_logger(__name__)


class SessionState:
    """Represents the current state of a session."""

    def __init__(
        self,
        session_id: UUID,
        is_busy: bool = False,
        current_operation: str | None = None,
        last_code: str | None = None,
        last_output: str | None = None,
        console_buffer: list[str] | None = None,
    ):
        self.session_id = session_id
        self.is_busy = is_busy
        self.current_operation = current_operation
        self.last_code = last_code
        self.last_output = last_output
        self.console_buffer = console_buffer or []


class SessionStateService:
    """
    Manages transient session state in Redis.

    Tracks:
    - busy/idle status (to prevent race conditions)
    - console output buffer for real-time streaming
    - temporary computation results
    """

    BUSY_KEY_PREFIX = "session:busy:"
    CONSOLE_KEY_PREFIX = "session:console:"
    STATE_KEY_PREFIX = "session:state:"
    LOCK_TTL = 300  # 5 minutes
    CONSOLE_TTL = 3600  # 1 hour

    async def acquire_lock(self, session_id: UUID) -> bool:
        """
        Try to acquire a lock for a session (mark as busy).
        Returns True if lock acquired, False if session is already busy.

        Uses Redis SETNX for atomic operation.
        """
        key = f"{self.BUSY_KEY_PREFIX}{session_id}"
        client = await cache.get_client()
        # SETNX + EXPIRE atomically
        acquired = await client.set(key, "1", nx=True, ex=self.LOCK_TTL)
        if acquired:
            logger.debug("session_lock_acquired", session_id=str(session_id))
        else:
            logger.debug("session_already_busy", session_id=str(session_id))
        return bool(acquired)

    async def release_lock(self, session_id: UUID) -> None:
        """Release the busy lock for a session."""
        key = f"{self.BUSY_KEY_PREFIX}{session_id}"
        await cache.delete(key)
        logger.debug("session_lock_released", session_id=str(session_id))

    async def is_busy(self, session_id: UUID) -> bool:
        """Check if a session is currently busy."""
        key = f"{self.BUSY_KEY_PREFIX}{session_id}"
        return await cache.exists(key)

    async def append_console_output(
        self,
        session_id: UUID,
        output: str,
    ) -> None:
        """Append output to the console buffer for real-time streaming."""
        key = f"{self.CONSOLE_KEY_PREFIX}{session_id}"
        client = await cache.get_client()
        await client.rpush(key, output)
        await client.expire(key, self.CONSOLE_TTL)

    async def get_console_output(
        self,
        session_id: UUID,
        start: int = 0,
        end: int = -1,
    ) -> list[str]:
        """Get console output from the buffer."""
        key = f"{self.CONSOLE_KEY_PREFIX}{session_id}"
        client = await cache.get_client()
        outputs = await client.lrange(key, start, end)
        return outputs

    async def clear_console_output(self, session_id: UUID) -> None:
        """Clear the console output buffer."""
        key = f"{self.CONSOLE_KEY_PREFIX}{session_id}"
        await cache.delete(key)

    async def set_state(
        self,
        session_id: UUID,
        state: dict[str, Any],
        ttl: int = 3600,
    ) -> None:
        """Store session state as JSON."""
        key = f"{self.STATE_KEY_PREFIX}{session_id}"
        await cache.set_json(key, state, ttl_seconds=ttl)

    async def get_state(self, session_id: UUID) -> dict[str, Any] | None:
        """Retrieve session state."""
        key = f"{self.STATE_KEY_PREFIX}{session_id}"
        return await cache.get_json(key)
