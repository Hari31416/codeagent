"""
Datara Memory System

Memory architecture:
1. Short-term (Redis): Session-based conversation history with TTL
"""

import json
from datetime import datetime, timezone
from typing import Any

from app.core.cache import CacheService
from app.shared.logging import get_logger

logger = get_logger(__name__)


# =============================================================================
# Short-Term Memory (Redis)
# =============================================================================


class SessionMemory:
    """
    Short-term session memory using Redis.

    Stores:
    - Recent conversation messages
    - Active files in session
    - Active database connections in session

    TTL: Configurable (default: 1 hour)
    """

    def __init__(
        self,
        cache_service: CacheService | None = None,
        max_messages: int = 10,
        ttl_seconds: int = 3600,
    ):
        """
        Initialize session memory.

        Args:
            cache_service: Cache service instance (uses default if None)
            max_messages: Maximum messages to keep in history (FIFO)
            ttl_seconds: TTL for session data (default: 1 hour)
        """
        self.cache = cache_service or CacheService()
        self.max_messages = max_messages
        self.ttl_seconds = ttl_seconds

    async def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """
        Add a message to session history.

        Args:
            session_id: Unique session identifier
            role: Message role (user/assistant/system)
            content: Message content
            metadata: Optional metadata (artifacts, sources, etc.)
        """
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "metadata": metadata or {},
        }

        key = f"session:messages:{session_id}"

        # Get existing messages
        messages_json = await self.cache.get(key)
        messages = json.loads(messages_json) if messages_json else []

        # Append new message
        messages.append(message)

        # Keep only last N messages (FIFO)
        if len(messages) > self.max_messages:
            messages = messages[-self.max_messages :]

        # Store back with TTL
        await self.cache.set(
            key,
            json.dumps(messages),
            ttl_seconds=self.ttl_seconds,
        )

        logger.debug(
            "Message added to session",
            session_id=session_id,
            role=role,
            total_messages=len(messages),
        )

    async def get_session_context(
        self,
        session_id: str,
        include_system: bool = False,
        include_metadata: bool = True,
    ) -> list[dict[str, Any]]:
        """
        Get recent messages for LLM context.

        Args:
            session_id: Unique session identifier
            include_system: Include system messages in context
            include_metadata: Include formatted metadata in assistant messages

        Returns:
            List of messages in format: [{"role": "...", "content": "..."}]
        """
        key = f"session:messages:{session_id}"
        messages_json = await self.cache.get(key)

        if not messages_json:
            return []

        messages = json.loads(messages_json)

        # Filter out system messages if needed
        if not include_system:
            messages = [msg for msg in messages if msg["role"] != "system"]

        # Build LLM message format with optional metadata
        result = []
        for msg in messages:
            content = msg["content"]

            # For assistant messages, include metadata summary if available
            if include_metadata and msg["role"] == "assistant" and msg.get("metadata"):
                metadata = msg["metadata"]

                # Include code history summary if present
                if "code_history" in metadata and metadata["code_history"]:
                    code_summary_parts = [content, "\n\n[Previous execution details:]"]
                    for entry in metadata["code_history"]:
                        iteration = entry.get("iteration", "?")
                        code = entry.get("code", "")
                        success = entry.get("success", False)
                        output = entry.get("output", "")
                        error = entry.get("error", "")

                        code_summary_parts.append(f"\n--- Iteration {iteration} ---")
                        if code:
                            # Truncate long code for context window efficiency
                            code_preview = (
                                code[:500] + "..." if len(code) > 500 else code
                            )
                            code_summary_parts.append(
                                f"Code:\n```python\n{code_preview}\n```"
                            )
                        if success:
                            output_preview = (
                                str(output)[:300] if output else "No output"
                            )
                            code_summary_parts.append(f"Result: {output_preview}")
                        else:
                            error_preview = (
                                str(error)[:200] if error else "Unknown error"
                            )
                            code_summary_parts.append(f"Error: {error_preview}")

                    content = "\n".join(code_summary_parts)

            result.append({"role": msg["role"], "content": content})

        return result

    async def get_full_session_history(
        self,
        session_id: str,
    ) -> list[dict[str, Any]]:
        """
        Get full session history with metadata.

        Args:
            session_id: Unique session identifier

        Returns:
            List of messages with timestamps and metadata
        """
        key = f"session:messages:{session_id}"
        messages_json = await self.cache.get(key)

        if not messages_json:
            return []

        return json.loads(messages_json)

    async def set_active_files(
        self,
        session_id: str,
        file_ids: list[str],
    ) -> None:
        """
        Set active files for the session.

        Args:
            session_id: Unique session identifier
            file_ids: List of file IDs currently in use
        """
        key = f"session:files:{session_id}"
        await self.cache.set(
            key,
            json.dumps(file_ids),
            ttl_seconds=self.ttl_seconds,
        )

        logger.debug(
            "Active files updated",
            session_id=session_id,
            file_count=len(file_ids),
        )

    async def get_active_files(self, session_id: str) -> list[str]:
        """
        Get active files for the session.

        Args:
            session_id: Unique session identifier

        Returns:
            List of file IDs
        """
        key = f"session:files:{session_id}"
        files_json = await self.cache.get(key)

        return json.loads(files_json) if files_json else []

    async def set_active_connections(
        self,
        session_id: str,
        connection_ids: list[str],
    ) -> None:
        """
        Set active database connections for the session.

        Args:
            session_id: Unique session identifier
            connection_ids: List of connection IDs currently in use
        """
        key = f"session:connections:{session_id}"
        await self.cache.set(
            key,
            json.dumps(connection_ids),
            ttl_seconds=self.ttl_seconds,
        )

    async def get_active_connections(self, session_id: str) -> list[str]:
        """
        Get active database connections for the session.

        Args:
            session_id: Unique session identifier

        Returns:
            List of connection IDs
        """
        key = f"session:connections:{session_id}"
        connections_json = await self.cache.get(key)

        return json.loads(connections_json) if connections_json else []

    async def clear_session(self, session_id: str) -> None:
        """
        Clear all session data.

        Args:
            session_id: Unique session identifier
        """
        keys = [
            f"session:messages:{session_id}",
            f"session:files:{session_id}",
            f"session:connections:{session_id}",
        ]

        for key in keys:
            await self.cache.delete(key)

        logger.info("Session cleared", session_id=session_id)

    async def extend_session_ttl(self, session_id: str) -> None:
        """
        Extend TTL for all session data.

        Args:
            session_id: Unique session identifier
        """
        keys = [
            f"session:messages:{session_id}",
            f"session:files:{session_id}",
            f"session:connections:{session_id}",
        ]

        for key in keys:
            value = await self.cache.get(key)
            if value:
                await self.cache.set(key, value, ttl_seconds=self.ttl_seconds)
