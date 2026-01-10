"""
Session management API endpoints.
"""

from typing import Any
from uuid import UUID

from app.db.pool import get_system_db
from app.db.session_db import ArtifactRepository, MessageRepository, SessionRepository
from app.services.export_service import ExportService
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
export_service = ExportService()


class CreateSessionRequest(BaseModel):
    """Request model for creating a session."""

    user_id: UUID
    project_id: UUID
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
            project_id=request.project_id,
            name=request.name,
        )

    logger.info("session_created_via_api", session_id=str(session["session_id"]))

    return {
        "success": True,
        "data": {
            "session_id": str(session["session_id"]),
            "user_id": str(session["user_id"]),
            "project_id": str(session["project_id"]),
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
            "project_id": str(session["project_id"]),
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
        # Parse metadata JSON if it's a string
        metadata = msg.get("metadata") or {}
        if isinstance(metadata, str):
            import json

            try:
                metadata = json.loads(metadata)
            except Exception:
                metadata = {}

        enriched = {
            "message_id": str(msg["message_id"]),
            "role": msg["role"],
            "content": msg["content"],
            "code": msg["code"],
            "thoughts": msg["thoughts"],
            "is_error": msg["is_error"],
            "created_at": msg["created_at"].isoformat(),
            "metadata": metadata,
        }

        # Extract iterations from metadata if present
        # Extract iterations from metadata if present
        if metadata.get("iterations"):
            # Normalize iteration outputs to ensure frontend compatibility
            raw_iterations = metadata["iterations"]
            if isinstance(raw_iterations, list):
                normalized = []
                for iter_data in raw_iterations:
                    if isinstance(iter_data, dict):
                        # Create copy to avoid mutating original if it was cached/shared (unlikely here but safe)
                        n_iter = iter_data.copy()
                        # Ensure output is typed
                        n_iter["output"] = _normalize_iteration_output(
                            n_iter.get("output")
                        )
                        # Ensure final_result is typed (user-defined answer)
                        if (
                            "final_result" in n_iter
                            and n_iter["final_result"] is not None
                        ):
                            n_iter["final_result"] = _normalize_iteration_output(
                                n_iter.get("final_result")
                            )
                        normalized.append(n_iter)
                    else:
                        normalized.append(iter_data)
                enriched["iterations"] = normalized
            else:
                enriched["iterations"] = raw_iterations

        # Add artifact IDs if present
        if msg.get("artifact_ids"):
            enriched["artifact_ids"] = [str(aid) for aid in msg["artifact_ids"]]

        enriched_messages.append(enriched)

    return {"success": True, "data": enriched_messages, "total": len(enriched_messages)}


def _normalize_iteration_output(output: Any) -> dict[str, Any] | None:
    """
    Ensure iteration output is in TypedData format.
    Matches logic in AgentOrchestrator._serialize_to_typed_data but for retrieval.
    """
    if output is None:
        return None

    # Check if already in TypedData format
    if (
        isinstance(output, dict)
        and "kind" in output
        and "data" in output
        and isinstance(output.get("kind"), str)
    ):
        return output

    # If it's a list or dict (and not typed data), treat as JSON or Multi
    if isinstance(output, (dict, list)):
        # If it looks like a plotly figure (dict with data/layout)
        if isinstance(output, dict) and ("data" in output and "layout" in output):
            return {
                "kind": "plotly",
                "data": output,
                "metadata": {},
            }

        # Detect Table (List of Dicts) - Common fallback for DataFrames
        if isinstance(output, list) and output and isinstance(output[0], dict):
            # Check if it looks like a table (flat dicts)
            # Collect all keys to ensure we handle sparse data
            keys = set()
            is_flat = True
            for item in output:
                if not isinstance(item, dict):
                    is_flat = False
                    break
                keys.update(item.keys())

            if is_flat:
                headers = sorted(list(keys))
                rows = []
                for item in output:
                    # Use None for missing values to be cleaner, or empty string
                    row = [item.get(k, "") for k in headers]
                    rows.append(row)

                return {
                    "kind": "table",
                    "data": {"headers": headers, "rows": rows},
                    "metadata": {"count": len(rows), "inferred_from": "list_of_dicts"},
                }

        # Default to JSON for structural data
        return {
            "kind": "json",
            "data": output,
            "metadata": {},
        }

    # Default to TEXT for everything else
    return {
        "kind": "text",
        "data": str(output),
        "metadata": {"original_type": type(output).__name__},
    }


@router.get("/{session_id}/artifacts")
async def get_session_artifacts(session_id: UUID):
    """Get all artifacts for a session."""
    async with get_system_db() as conn:
        artifacts = await artifact_repo.get_artifacts_by_session(
            conn, session_id=session_id
        )

    # Generate presigned URLs for each artifact
    # This was the bug: previously it only returned metadata
    result = []
    for a in artifacts:
        try:
            url = await workspace_service.get_presigned_url(
                session_id=session_id,
                file_name=a["file_name"],
            )
            result.append(
                {
                    "artifact_id": str(a["artifact_id"]),
                    "file_name": a["file_name"],
                    "file_type": a["file_type"],
                    "mime_type": a["mime_type"],
                    "size_bytes": a["size_bytes"],
                    "created_at": a["created_at"].isoformat(),
                    "presigned_url": url,
                }
            )
        except Exception as e:
            logger.warning(
                "failed_to_generate_presigned_url",
                artifact_id=str(a["artifact_id"]),
                error=str(e),
            )
            # Add without URL if generation fails
            result.append(
                {
                    "artifact_id": str(a["artifact_id"]),
                    "file_name": a["file_name"],
                    "file_type": a["file_type"],
                    "mime_type": a["mime_type"],
                    "size_bytes": a["size_bytes"],
                    "created_at": a["created_at"].isoformat(),
                }
            )

    return {
        "success": True,
        "data": result,
        "total": len(result),
    }


@router.get("")
async def list_sessions(
    user_id: UUID = Query(..., description="User ID to filter sessions"),
    project_id: UUID | None = Query(
        None, description="Optional project ID to filter sessions"
    ),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """List sessions for a user, optionally filtered by project."""
    async with get_system_db() as conn:
        sessions = await session_repo.list_sessions_by_user(
            conn=conn,
            user_id=user_id,
            project_id=project_id,
            limit=limit,
            offset=offset,
        )

    return {
        "success": True,
        "data": [
            {
                "session_id": str(s["session_id"]),
                "project_id": str(s["project_id"]),
                "name": s["name"],
                "created_at": s["created_at"].isoformat(),
                "updated_at": s["updated_at"].isoformat(),
            }
            for s in sessions
        ],
        "total": len(sessions),
    }


@router.get("/{session_id}/export")
async def export_session(session_id: UUID):
    """
    Export a session as JSON metadata and markdown.

    Returns:
        - metadata: Full session metadata
        - markdown: Structured markdown with embedded artifacts
        - filename: Suggested filename for download
    """
    try:
        result = await export_service.export_session(session_id)
        return {
            "success": True,
            "data": {
                "metadata": result.metadata_json,
                "markdown": result.markdown_content,
                "filename": result.filename,
            },
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("export_session_failed", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
