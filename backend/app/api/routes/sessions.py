"""
Session management API endpoints.
"""

from uuid import UUID

from app.db.pool import get_system_db
from app.db.session_db import ArtifactRepository, MessageRepository, SessionRepository
from app.services.workspace_service import WorkspaceService
from app.shared.logging import get_logger
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

logger = get_logger(__name__)
router = APIRouter(prefix="/api/v1/sessions", tags=["sessions"])

session_repo = SessionRepository()
message_repo = MessageRepository()
artifact_repo = ArtifactRepository()
workspace_service = WorkspaceService()


class CreateSessionRequest(BaseModel):
    """Request model for creating a session."""

    user_id: UUID
    name: str | None = None


class UpdateSessionRequest(BaseModel):
    """Request model for updating a session."""

    name: str | None = None


@router.post("")
async def create_session(request: CreateSessionRequest):
    """
    Create a new session.

    Returns session_id and workspace_prefix.
    """
    async with get_system_db() as conn:
        session = await session_repo.create_session(
            conn=conn,
            user_id=request.user_id,
            name=request.name,
        )

    logger.info("session_created_via_api", session_id=str(session["session_id"]))

    return {
        "success": True,
        "data": {
            "session_id": str(session["session_id"]),
            "user_id": str(session["user_id"]),
            "workspace_prefix": session["workspace_prefix"],
            "name": session["name"],
            "created_at": session["created_at"].isoformat(),
        },
    }


@router.get("/{session_id}")
async def get_session(session_id: UUID):
    """Get session details by ID."""
    async with get_system_db() as conn:
        session = await session_repo.get_session(conn=conn, session_id=session_id)

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return {
        "success": True,
        "data": {
            "session_id": str(session["session_id"]),
            "user_id": str(session["user_id"]),
            "workspace_prefix": session["workspace_prefix"],
            "name": session["name"],
            "created_at": session["created_at"].isoformat(),
            "updated_at": session["updated_at"].isoformat(),
        },
    }


@router.patch("/{session_id}")
async def update_session(session_id: UUID, request: UpdateSessionRequest):
    """Update session metadata."""
    async with get_system_db() as conn:
        session = await session_repo.update_session(
            conn=conn,
            session_id=session_id,
            name=request.name,
        )

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return {
        "success": True,
        "data": {
            "session_id": str(session["session_id"]),
            "name": session["name"],
            "updated_at": session["updated_at"].isoformat(),
        },
    }


@router.delete("/{session_id}")
async def delete_session(session_id: UUID):
    """
    Delete a session and all associated data.

    This will:
    1. Delete workspace files from MinIO
    2. Delete session record from PostgreSQL (cascades to artifacts and messages)
    """
    # Delete workspace files
    try:
        deleted_count = await workspace_service.delete_workspace(session_id)
    except Exception as e:
        logger.error(
            "workspace_deletion_failed",
            session_id=str(session_id),
            error=str(e),
        )
        # Continue with database deletion even if MinIO fails

    # Delete from database
    async with get_system_db() as conn:
        deleted = await session_repo.delete_session(conn=conn, session_id=session_id)

    if not deleted:
        raise HTTPException(status_code=404, detail="Session not found")

    return {
        "success": True,
        "message": f"Session deleted. Removed {deleted_count} files from workspace.",
    }


@router.get("/{session_id}/history")
async def get_session_history(
    session_id: UUID,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """
    Get chat history for a session.

    Used for:
    - Resuming conversations
    - Replaying past sessions
    - Branching from a specific point
    """
    async with get_system_db() as conn:
        messages = await message_repo.get_messages_by_session(
            conn=conn,
            session_id=session_id,
            limit=limit,
            offset=offset,
        )

    # Enrich with artifact URLs if needed
    enriched_messages = []
    for msg in messages:
        enriched = {
            "message_id": str(msg["message_id"]),
            "role": msg["role"],
            "content": msg["content"],
            "code": msg["code"],
            "thoughts": msg["thoughts"],
            "is_error": msg["is_error"],
            "created_at": msg["created_at"].isoformat(),
        }

        # Add artifact IDs if present
        if msg.get("artifact_ids"):
            enriched["artifact_ids"] = [str(aid) for aid in msg["artifact_ids"]]

        enriched_messages.append(enriched)

    return {"success": True, "data": enriched_messages, "total": len(enriched_messages)}


@router.get("/{session_id}/artifacts")
async def get_session_artifacts(session_id: UUID):
    """Get all artifacts for a session."""
    async with get_system_db() as conn:
        artifacts = await artifact_repo.get_artifacts_by_session(
            conn, session_id=session_id
        )

    return {
        "success": True,
        "data": [
            {
                "artifact_id": str(a["artifact_id"]),
                "file_name": a["file_name"],
                "file_type": a["file_type"],
                "mime_type": a["mime_type"],
                "size_bytes": a["size_bytes"],
                "created_at": a["created_at"].isoformat(),
            }
            for a in artifacts
        ],
        "total": len(artifacts),
    }


@router.get("")
async def list_sessions(
    user_id: UUID = Query(..., description="User ID to filter sessions"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """List sessions for a user."""
    async with get_system_db() as conn:
        sessions = await session_repo.list_sessions_by_user(
            conn=conn,
            user_id=user_id,
            limit=limit,
            offset=offset,
        )

    return {
        "success": True,
        "data": [
            {
                "session_id": str(s["session_id"]),
                "name": s["name"],
                "created_at": s["created_at"].isoformat(),
                "updated_at": s["updated_at"].isoformat(),
            }
            for s in sessions
        ],
        "total": len(sessions),
    }
