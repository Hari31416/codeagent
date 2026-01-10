"""
Database repositories for sessions, artifacts, and chat history.
Uses asyncpg for async PostgreSQL operations.
"""

from typing import Any
from uuid import UUID

from app.core.cache import cache
from app.shared.logging import get_logger
from asyncpg import Connection

logger = get_logger(__name__)


class ProjectRepository:
    """Repository for project CRUD operations."""

    async def ensure_user_exists(
        self,
        conn: Connection,
        user_id: UUID,
    ) -> None:
        """Ensure user exists in the database."""
        await conn.execute(
            """
            INSERT INTO users (user_id, email, full_name)
            VALUES ($1, $2, $3)
            ON CONFLICT (user_id) DO NOTHING
            """,
            user_id,
            f"{user_id}@anonymous.codeagent",
            "Anonymous User",
        )

    async def create_project(
        self,
        conn: Connection,
        user_id: UUID,
        name: str,
        description: str | None = None,
    ) -> dict[str, Any]:
        """Create a new project."""
        await self.ensure_user_exists(conn, user_id)

        row = await conn.fetchrow(
            """
            INSERT INTO projects (user_id, name, description)
            VALUES ($1, $2, $3)
            RETURNING project_id, user_id, name, description, created_at, updated_at, metadata
            """,
            user_id,
            name,
            description,
        )

        logger.info(
            "project_created",
            project_id=str(row["project_id"]),
            user_id=str(user_id),
        )

        return dict(row)

    async def get_project(
        self,
        conn: Connection,
        project_id: UUID,
    ) -> dict[str, Any] | None:
        """Get project by ID."""
        row = await conn.fetchrow(
            """
            SELECT project_id, user_id, name, description, created_at, updated_at, metadata
            FROM projects
            WHERE project_id = $1
            """,
            project_id,
        )
        return dict(row) if row else None

    async def update_project(
        self,
        conn: Connection,
        project_id: UUID,
        name: str | None = None,
        description: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        """Update project metadata."""
        import json

        updates = []
        params = [project_id]
        param_idx = 2

        if name is not None:
            updates.append(f"name = ${param_idx}")
            params.append(name)
            param_idx += 1

        if description is not None:
            updates.append(f"description = ${param_idx}")
            params.append(description)
            param_idx += 1

        if metadata is not None:
            updates.append(f"metadata = ${param_idx}")
            params.append(json.dumps(metadata))
            param_idx += 1

        if not updates:
            return await self.get_project(conn, project_id)

        updates.append("updated_at = NOW()")
        query = f"""
            UPDATE projects
            SET {", ".join(updates)}
            WHERE project_id = $1
            RETURNING project_id, user_id, name, description, created_at, updated_at, metadata
        """

        row = await conn.fetchrow(query, *params)
        return dict(row) if row else None

    async def list_projects_by_user(
        self,
        conn: Connection,
        user_id: UUID,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """List projects for a user."""
        await self.ensure_user_exists(conn, user_id)

        rows = await conn.fetch(
            """
            SELECT project_id, user_id, name, description, created_at, updated_at, metadata
            FROM projects
            WHERE user_id = $1
            ORDER BY updated_at DESC
            LIMIT $2 OFFSET $3
            """,
            user_id,
            limit,
            offset,
        )
        return [dict(row) for row in rows]

    async def delete_project(
        self,
        conn: Connection,
        project_id: UUID,
    ) -> bool:
        """Delete a project (cascades to sessions, artifacts, and messages)."""
        result = await conn.execute(
            "DELETE FROM projects WHERE project_id = $1",
            project_id,
        )
        deleted = result.split()[-1] == "1"
        if deleted:
            logger.info("project_deleted", project_id=str(project_id))
        return deleted


class SessionRepository:
    """Repository for session CRUD operations."""

    async def ensure_user_exists(
        self,
        conn: Connection,
        user_id: UUID,
    ) -> None:
        """Ensure user exists in the database."""
        await conn.execute(
            """
            INSERT INTO users (user_id, email, full_name)
            VALUES ($1, $2, $3)
            ON CONFLICT (user_id) DO NOTHING
            """,
            user_id,
            f"{user_id}@anonymous.codeagent",
            "Anonymous User",
        )

    async def create_session(
        self,
        conn: Connection,
        user_id: UUID,
        project_id: UUID,
        name: str | None = None,
    ) -> dict[str, Any]:
        """Create a new session with workspace prefix."""
        await self.ensure_user_exists(conn, user_id)

        row = await conn.fetchrow(
            """
            INSERT INTO sessions (user_id, project_id, workspace_prefix, name)
            VALUES ($1, $2, $3, $4)
            RETURNING session_id, user_id, project_id, workspace_prefix, name, created_at, updated_at, metadata
            """,
            user_id,
            project_id,
            "",  # Will be updated after getting session_id
            name or "Untitled Session",
        )

        session_id = row["session_id"]
        workspace_prefix = f"projects/{project_id}/sessions/{session_id}/"

        # Update with correct workspace_prefix
        row = await conn.fetchrow(
            """
            UPDATE sessions
            SET workspace_prefix = $1
            WHERE session_id = $2
            RETURNING session_id, user_id, project_id, workspace_prefix, name, created_at, updated_at, metadata
            """,
            workspace_prefix,
            session_id,
        )

        logger.info(
            "session_created",
            session_id=str(session_id),
            project_id=str(project_id),
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
            SELECT session_id, user_id, project_id, workspace_prefix, name, created_at, updated_at, metadata
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
            SET {", ".join(updates)}
            WHERE session_id = $1
            RETURNING session_id, user_id, project_id, workspace_prefix, name, created_at, updated_at, metadata
        """

        row = await conn.fetchrow(query, *params)
        return dict(row) if row else None

    async def list_sessions_by_user(
        self,
        conn: Connection,
        user_id: UUID,
        project_id: UUID | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """List sessions for a user, optionally filtered by project."""
        await self.ensure_user_exists(conn, user_id)

        if project_id:
            rows = await conn.fetch(
                """
                SELECT session_id, user_id, project_id, workspace_prefix, name, created_at, updated_at, metadata
                FROM sessions
                WHERE user_id = $1 AND project_id = $2
                ORDER BY updated_at DESC
                LIMIT $3 OFFSET $4
                """,
                user_id,
                project_id,
                limit,
                offset,
            )
        else:
            rows = await conn.fetch(
                """
                SELECT session_id, user_id, project_id, workspace_prefix, name, created_at, updated_at, metadata
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

    async def list_sessions_by_project(
        self,
        conn: Connection,
        project_id: UUID,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """List sessions for a specific project."""
        rows = await conn.fetch(
            """
            SELECT session_id, user_id, project_id, workspace_prefix, name, created_at, updated_at, metadata
            FROM sessions
            WHERE project_id = $1
            ORDER BY updated_at DESC
            LIMIT $2 OFFSET $3
            """,
            project_id,
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
        file_name: str,
        file_type: str,
        mime_type: str,
        size_bytes: int,
        minio_object_key: str,
        session_id: UUID | None = None,
        project_id: UUID | None = None,
        message_id: UUID | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Register a new artifact in the database."""
        import json

        # Validate that at least one of session_id or project_id is provided
        if session_id is None and project_id is None:
            raise ValueError("Either session_id or project_id must be provided")

        row = await conn.fetchrow(
            """
            INSERT INTO artifacts (session_id, project_id, message_id, file_name, file_type, mime_type, size_bytes, minio_object_key, metadata)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            RETURNING artifact_id, session_id, project_id, message_id, file_name, file_type, mime_type, size_bytes, minio_object_key, created_at, metadata
            """,
            session_id,
            project_id,
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
            session_id=str(session_id) if session_id else None,
            project_id=str(project_id) if project_id else None,
            file_name=file_name,
        )

        if session_id:
            await cache.delete_pattern(f"artifacts:session:{session_id}")
        if project_id:
            await cache.delete_pattern(f"artifacts:project:{project_id}")

        return dict(row)

    async def get_artifact(
        self,
        conn: Connection,
        artifact_id: UUID,
    ) -> dict[str, Any] | None:
        """Get artifact by ID."""
        row = await conn.fetchrow(
            """
            SELECT artifact_id, session_id, project_id, message_id, file_name, file_type, mime_type, size_bytes, minio_object_key, created_at, metadata
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
        cache_key = f"artifacts:session:{session_id}"
        cached_artifacts = await cache.get_json(cache_key)
        if cached_artifacts:
            logger.debug("artifacts_by_session_cache_hit", session_id=str(session_id))
            return cached_artifacts

        rows = await conn.fetch(
            """
            SELECT artifact_id, session_id, project_id, message_id, file_name, file_type, mime_type, size_bytes, minio_object_key, created_at, metadata
            FROM artifacts
            WHERE session_id = $1
            ORDER BY created_at DESC
            """,
            session_id,
        )
        artifacts = [dict(row) for row in rows]

        await cache.set_json(cache_key, artifacts, ttl_seconds=120)

        return artifacts

    async def get_artifacts_by_message(
        self,
        conn: Connection,
        message_id: UUID,
    ) -> list[dict[str, Any]]:
        """Get all artifacts associated with a specific message."""
        rows = await conn.fetch(
            """
            SELECT artifact_id, session_id, project_id, message_id, file_name, file_type, mime_type, size_bytes, minio_object_key, created_at, metadata
            FROM artifacts
            WHERE message_id = $1
            ORDER BY created_at ASC
            """,
            message_id,
        )
        return [dict(row) for row in rows]

    async def get_artifacts_by_project(
        self,
        conn: Connection,
        project_id: UUID,
    ) -> list[dict[str, Any]]:
        """Get all project-level artifacts (shared across all sessions in project)."""
        cache_key = f"artifacts:project:{project_id}"
        cached_artifacts = await cache.get_json(cache_key)
        if cached_artifacts:
            logger.debug("artifacts_by_project_cache_hit", project_id=str(project_id))
            return cached_artifacts

        rows = await conn.fetch(
            """
            SELECT artifact_id, session_id, project_id, message_id, file_name, file_type, mime_type, size_bytes, minio_object_key, created_at, metadata
            FROM artifacts
            WHERE project_id = $1 AND session_id IS NULL
            ORDER BY created_at DESC
            """,
            project_id,
        )
        artifacts = [dict(row) for row in rows]

        await cache.set_json(cache_key, artifacts, ttl_seconds=120)

        return artifacts

    async def get_project_and_session_artifacts(
        self,
        conn: Connection,
        project_id: UUID,
        session_id: UUID,
    ) -> list[dict[str, Any]]:
        """Get both project-level artifacts and session-specific artifacts."""
        rows = await conn.fetch(
            """
            SELECT artifact_id, session_id, project_id, message_id, file_name, file_type, mime_type, size_bytes, minio_object_key, created_at, metadata
            FROM artifacts
            WHERE (project_id = $1 AND session_id IS NULL) OR session_id = $2
            ORDER BY created_at DESC
            """,
            project_id,
            session_id,
        )
        return [dict(row) for row in rows]

    async def delete_artifact(
        self,
        conn: Connection,
        artifact_id: UUID,
    ) -> bool:
        """Delete an artifact record."""
        artifact = await self.get_artifact(conn, artifact_id)

        result = await conn.execute(
            "DELETE FROM artifacts WHERE artifact_id = $1",
            artifact_id,
        )
        deleted = result.split()[-1] == "1"
        if deleted:
            logger.info("artifact_deleted", artifact_id=str(artifact_id))

            if artifact:
                if artifact.get("session_id"):
                    await cache.delete_pattern(
                        f"artifacts:session:{artifact['session_id']}"
                    )
                if artifact.get("project_id"):
                    await cache.delete_pattern(
                        f"artifacts:project:{artifact['project_id']}"
                    )

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
        created_at: Any | None = None,
    ) -> dict[str, Any]:
        """Add a message to the chat history."""
        import json

        if created_at:
            row = await conn.fetchrow(
                """
                INSERT INTO messages (session_id, role, content, code, thoughts, artifact_ids, execution_logs, is_error, metadata, created_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
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
                created_at,
            )
        else:
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

        await cache.delete_pattern(f"history:{session_id}:*")

        return dict(row)

    async def get_messages_by_session(
        self,
        conn: Connection,
        session_id: UUID,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """Get chat history for a session (for replay feature)."""
        cache_key = f"history:{session_id}:{limit}:{offset}"
        cached_messages = await cache.get_json(cache_key)
        if cached_messages:
            logger.debug("session_history_cache_hit", session_id=str(session_id))
            return cached_messages

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
        messages = [dict(row) for row in rows]

        await cache.set_json(cache_key, messages, ttl_seconds=300)

        return messages

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
