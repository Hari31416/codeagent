"""
Cleanup tasks for old sessions and temporary data.

Run periodically (e.g., via cron or scheduled task).
"""

from datetime import datetime, timedelta, timezone

from app.core.cache import cache
from app.db.pool import get_system_db
from app.services.workspace_service import WorkspaceService
from app.shared.logging import get_logger

logger = get_logger(__name__)

workspace_service = WorkspaceService()


async def cleanup_old_sessions(days_old: int = 30):
    """
    Delete sessions and their workspaces older than specified days.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=days_old)

    async with get_system_db() as conn:
        # Get old sessions
        old_sessions = await conn.fetch(
            """
            SELECT session_id FROM sessions
            WHERE updated_at < $1
            """,
            cutoff,
        )

        for session in old_sessions:
            session_id = session["session_id"]
            try:
                # Delete workspace files from MinIO
                await workspace_service.delete_workspace(session_id)

                # Delete from database (cascade deletes artifacts and messages)
                await conn.execute(
                    "DELETE FROM sessions WHERE session_id = $1", session_id
                )

                logger.info("old_session_deleted", session_id=str(session_id))

            except Exception as e:
                logger.error(
                    "session_cleanup_failed",
                    session_id=str(session_id),
                    error=str(e),
                )


async def cleanup_redis_keys():
    """
    Clean up expired Redis keys that weren't auto-expired.
    """
    # Clear old console buffers
    deleted = await cache.clear_pattern("session:console:*")
    logger.info("redis_cleanup_complete", deleted_keys=deleted)
