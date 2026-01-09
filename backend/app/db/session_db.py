"""
Database repositories for sessions, artifacts, and chat history.
Uses asyncpg for async PostgreSQL operations.
"""

from typing import Any
from uuid import UUID

from app.shared.logging import get_logger
from asyncpg import Connection

logger = get_logger(__name__)


class SessionRepository:
    """Repository for session CRUD operations."""

    async def create_session(
        self,
        conn: Connection,
        user_id: UUID,
        name: str | None = None,
    ) -> dict[str, Any]:
        """Create a new session with workspace prefix."""
        row = await conn.fetchrow(
            """
            INSERT INTO sessions (user_id, workspace_prefix, name)
            VALUES ($1, $2, $3)
            RETURNING session_id, user_id, workspace_prefix, name, created_at, updated_at, metadata
            """,
            user_id,
            "",  # Will be updated after getting session_id
            name or "Untitled Session",
        )

        session_id = row["session_id"]
        workspace_prefix = f"sessions/{session_id}/"

        # Update with correct workspace_prefix
        row = await conn.fetchrow(
            """
            UPDATE sessions
            SET workspace_prefix = $1
            WHERE session_id = $2
            RETURNING session_id, user_id, workspace_prefix, name, created_at, updated_at, metadata
            """,
            workspace_prefix,
            session_id,
        )

        logger.info(
            "session_created",
            session_id=str(session_id),
            user_id=str(user_id),
        )

        return dict(row)

    async def get_session(
        self,
        conn: Connection,
        session_id: UUID,
    ) -> dict[str, Any] | None:
        """Get session by ID."""
        row = await conn.fetchrow(
            """
            SELECT session_id, user_id, workspace_prefix, name, created_at, updated_at, metadata
            FROM sessions
            WHERE session_id = $1
            """,
            session_id,
        )
        return dict(row) if row else None

    async def update_session(
        self,
        conn: Connection,
        session_id: UUID,
        name: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        """Update session metadata."""
        updates = []
        params = [session_id]
        param_idx = 2

        if name is not None:
            updates.append(f"name = ${param_idx}")
            params.append(name)
            param_idx += 1

        if metadata is not None:
            import json

            updates.append(f"metadata = ${param_idx}")
            params.append(json.dumps(metadata))
            param_idx += 1

        if not updates:
            return await self.get_session(conn, session_id)

        updates.append("updated_at = NOW()")
        query = f"""
            UPDATE sessions
            SET {', '.join(updates)}
            WHERE session_id = $1
            RETURNING session_id, user_id, workspace_prefix, name, created_at, updated_at, metadata
        """

        row = await conn.fetchrow(query, *params)
        return dict(row) if row else None

    async def list_sessions_by_user(
        self,
        conn: Connection,
        user_id: UUID,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """List sessions for a user."""
        rows = await conn.fetch(
            """
            SELECT session_id, user_id, workspace_prefix, name, created_at, updated_at, metadata
            FROM sessions
            WHERE user_id = $1
            ORDER BY updated_at DESC
            LIMIT $2 OFFSET $3
            """,
            user_id,
            limit,
            offset,
        )
        return [dict(row) for row in rows]

    async def delete_session(
        self,
        conn: Connection,
        session_id: UUID,
    ) -> bool:
        """Delete a session (cascades to artifacts and messages)."""
        result = await conn.execute(
            "DELETE FROM sessions WHERE session_id = $1",
            session_id,
        )
        deleted = result.split()[-1] == "1"
        if deleted:
            logger.info("session_deleted", session_id=str(session_id))
        return deleted


class ArtifactRepository:
    """Repository for artifact CRUD operations."""

    async def create_artifact(
        self,
        conn: Connection,
        session_id: UUID,
        file_name: str,
        file_type: str,
        mime_type: str,
        size_bytes: int,
        minio_object_key: str,
        message_id: UUID | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Register a new artifact in the database."""
        import json

        row = await conn.fetchrow(
            """
            INSERT INTO artifacts (session_id, message_id, file_name, file_type, mime_type, size_bytes, minio_object_key, metadata)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            RETURNING artifact_id, session_id, message_id, file_name, file_type, mime_type, size_bytes, minio_object_key, created_at, metadata
            """,
            session_id,
            message_id,
            file_name,
            file_type,
            mime_type,
            size_bytes,
            minio_object_key,
            json.dumps(metadata or {}),
        )

        logger.info(
            "artifact_created",
            artifact_id=str(row["artifact_id"]),
            session_id=str(session_id),
            file_name=file_name,
        )

        return dict(row)

    async def get_artifact(
        self,
        conn: Connection,
        artifact_id: UUID,
    ) -> dict[str, Any] | None:
        """Get artifact by ID."""
        row = await conn.fetchrow(
            """
            SELECT artifact_id, session_id, message_id, file_name, file_type, mime_type, size_bytes, minio_object_key, created_at, metadata
            FROM artifacts
            WHERE artifact_id = $1
            """,
            artifact_id,
        )
        return dict(row) if row else None

    async def get_artifacts_by_session(
        self,
        conn: Connection,
        session_id: UUID,
    ) -> list[dict[str, Any]]:
        """Get all artifacts for a session."""
        rows = await conn.fetch(
            """
            SELECT artifact_id, session_id, message_id, file_name, file_type, mime_type, size_bytes, minio_object_key, created_at, metadata
            FROM artifacts
            WHERE session_id = $1
            ORDER BY created_at DESC
            """,
            session_id,
        )
        return [dict(row) for row in rows]

    async def get_artifacts_by_message(
        self,
        conn: Connection,
        message_id: UUID,
    ) -> list[dict[str, Any]]:
        """Get all artifacts associated with a specific message."""
        rows = await conn.fetch(
            """
            SELECT artifact_id, session_id, message_id, file_name, file_type, mime_type, size_bytes, minio_object_key, created_at, metadata
            FROM artifacts
            WHERE message_id = $1
            ORDER BY created_at ASC
            """,
            message_id,
        )
        return [dict(row) for row in rows]

    async def delete_artifact(
        self,
        conn: Connection,
        artifact_id: UUID,
    ) -> bool:
        """Delete an artifact record."""
        result = await conn.execute(
            "DELETE FROM artifacts WHERE artifact_id = $1",
            artifact_id,
        )
        deleted = result.split()[-1] == "1"
        if deleted:
            logger.info("artifact_deleted", artifact_id=str(artifact_id))
        return deleted


class MessageRepository:
    """Repository for chat message CRUD operations."""

    async def add_message(
        self,
        conn: Connection,
        session_id: UUID,
        role: str,
        content: str,
        code: str | None = None,
        thoughts: str | None = None,
        artifact_ids: list[UUID] | None = None,
        execution_logs: str | None = None,
        is_error: bool = False,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Add a message to the chat history."""
        import json

        row = await conn.fetchrow(
            """
            INSERT INTO messages (session_id, role, content, code, thoughts, artifact_ids, execution_logs, is_error, metadata)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            RETURNING message_id, session_id, role, content, code, thoughts, artifact_ids, execution_logs, is_error, created_at, metadata
            """,
            session_id,
            role,
            content,
            code,
            thoughts,
            artifact_ids or [],
            execution_logs,
            is_error,
            json.dumps(metadata or {}),
        )

        logger.debug("message_added", message_id=str(row["message_id"]), role=role)

        return dict(row)

    async def get_messages_by_session(
        self,
        conn: Connection,
        session_id: UUID,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """Get chat history for a session (for replay feature)."""
        rows = await conn.fetch(
            """
            SELECT message_id, session_id, role, content, code, thoughts, artifact_ids, execution_logs, is_error, created_at, metadata
            FROM messages
            WHERE session_id = $1
            ORDER BY created_at ASC
            LIMIT $2 OFFSET $3
            """,
            session_id,
            limit,
            offset,
        )
        return [dict(row) for row in rows]

    async def get_message(
        self,
        conn: Connection,
        message_id: UUID,
    ) -> dict[str, Any] | None:
        """Get a single message by ID."""
        row = await conn.fetchrow(
            """
            SELECT message_id, session_id, role, content, code, thoughts, artifact_ids, execution_logs, is_error, created_at, metadata
            FROM messages
            WHERE message_id = $1
            """,
            message_id,
        )
        return dict(row) if row else None

    async def delete_messages_by_session(
        self,
        conn: Connection,
        session_id: UUID,
    ) -> int:
        """Delete all messages for a session."""
        result = await conn.execute(
            "DELETE FROM messages WHERE session_id = $1",
            session_id,
        )
        count = int(result.split()[-1])
        logger.info("messages_deleted", session_id=str(session_id), count=count)
        return count
