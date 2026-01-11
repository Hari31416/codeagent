"""
Artifact management API endpoints.
"""

from datetime import timedelta
from typing import Any
from uuid import UUID

from app.config import settings
from app.core.deps import CurrentActiveUser
from app.core.storage import get_storage_service
from app.db.pool import get_system_db
from app.db.session_db import ArtifactRepository, ProjectRepository, SessionRepository
from app.services.workspace_service import WorkspaceService
from app.shared.logging import get_logger
from fastapi import APIRouter, HTTPException, Query

logger = get_logger(__name__)
router = APIRouter(prefix="/api/v1/artifacts", tags=["artifacts"])


def _safe_isoformat(value: Any) -> str:
    """Safely convert a datetime or string to ISO format string."""
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


artifact_repo = ArtifactRepository()
session_repo = SessionRepository()
project_repo = ProjectRepository()
storage_service = get_storage_service()
workspace_service = WorkspaceService()


@router.get("/{artifact_id}")
async def get_artifact(artifact_id: UUID, current_user: CurrentActiveUser):
    """Get artifact metadata by ID."""
    async with get_system_db() as conn:
        artifact = await artifact_repo.get_artifact(conn, artifact_id)

    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")

    # Verify ownership via session
    async with get_system_db() as conn:
        if artifact.get("session_id"):
            session = await session_repo.get_session(conn, artifact["session_id"])
            if session and session["user_id"] != current_user["user_id"]:
                raise HTTPException(status_code=403, detail="Access denied")
        elif artifact.get("project_id"):
            project = await project_repo.get_project(conn, artifact["project_id"])
            if project and project["user_id"] != current_user["user_id"]:
                raise HTTPException(status_code=403, detail="Access denied")

    return {
        "success": True,
        "data": {
            "artifact_id": str(artifact["artifact_id"]),
            "session_id": (
                str(artifact["session_id"]) if artifact.get("session_id") else None
            ),
            "file_name": artifact["file_name"],
            "file_type": artifact["file_type"],
            "mime_type": artifact["mime_type"],
            "size_bytes": artifact["size_bytes"],
            "created_at": _safe_isoformat(artifact["created_at"]),
            "presigned_url": f"{settings.api_base_url}/artifacts/{artifact['artifact_id']}/download",
        },
    }


@router.get("/{artifact_id}/url")
async def get_artifact_url(
    artifact_id: UUID,
    expires_hours: int = Query(1, ge=1, le=24),
):
    """
    Get a presigned URL for an artifact.

    URLs are temporary (default 1 hour) for security.
    """
    async with get_system_db() as conn:
        artifact = await artifact_repo.get_artifact(conn, artifact_id)

    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")

    url = storage_service.get_presigned_url(
        artifact["minio_object_key"],
        expires=timedelta(hours=expires_hours),
    )

    return {
        "success": True,
        "data": {
            "artifact_id": str(artifact_id),
            "url": url,
            "expires_in_seconds": expires_hours * 3600,
        },
    }


@router.get("/{artifact_id}/download")
async def download_artifact(artifact_id: UUID):
    """
    Stream artifact file directly from MinIO through the backend.

    This avoids presigned URL signature issues with proxies.
    """
    async with get_system_db() as conn:
        artifact = await artifact_repo.get_artifact(conn, artifact_id)

    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")

    try:
        # Download file from MinIO
        file_data = storage_service.download(artifact["minio_object_key"])

        from fastapi.responses import Response

        return Response(
            content=file_data,
            media_type=artifact["mime_type"],
            headers={
                "Content-Disposition": f'inline; filename="{artifact["file_name"]}"',
                "Content-Length": str(len(file_data)),
            },
        )
    except Exception as e:
        logger.error(
            "artifact_download_failed",
            artifact_id=str(artifact_id),
            error=str(e),
        )
        raise HTTPException(status_code=500, detail="Failed to download artifact")


@router.get("/sessions/{session_id}")
async def get_session_artifacts(session_id: UUID):
    """Get all artifacts for a session."""
    async with get_system_db() as conn:
        artifacts = await artifact_repo.get_artifacts_by_session(conn, session_id)

    return {
        "success": True,
        "data": [
            {
                "artifact_id": str(a["artifact_id"]),
                "file_name": a["file_name"],
                "file_type": a["file_type"],
                "mime_type": a["mime_type"],
                "size_bytes": a["size_bytes"],
                "created_at": _safe_isoformat(a["created_at"]),
                "presigned_url": f"{settings.api_base_url}/artifacts/{a['artifact_id']}/download",
            }
            for a in artifacts
        ],
        "total": len(artifacts),
    }


@router.get("/projects/{project_id}")
async def get_project_artifacts(project_id: UUID):
    """Get all project-level artifacts (shared across all sessions in project)."""
    async with get_system_db() as conn:
        artifacts = await artifact_repo.get_artifacts_by_project(conn, project_id)

    return {
        "success": True,
        "data": [
            {
                "artifact_id": str(a["artifact_id"]),
                "project_id": str(a["project_id"]) if a.get("project_id") else None,
                "file_name": a["file_name"],
                "file_type": a["file_type"],
                "mime_type": a["mime_type"],
                "size_bytes": a["size_bytes"],
                "created_at": _safe_isoformat(a["created_at"]),
                "presigned_url": f"{settings.api_base_url}/artifacts/{a['artifact_id']}/download",
            }
            for a in artifacts
        ],
        "total": len(artifacts),
    }


@router.delete("/{artifact_id}")
async def delete_artifact(artifact_id: UUID):
    """
    Delete an artifact.

    This will:
    1. Delete the file from MinIO
    2. Delete the artifact record from PostgreSQL
    """
    # Get artifact info
    async with get_system_db() as conn:
        artifact = await artifact_repo.get_artifact(conn, artifact_id)

        if not artifact:
            raise HTTPException(status_code=404, detail="Artifact not found")

        # Delete from MinIO
        try:
            storage_service.delete(artifact["minio_object_key"])
        except Exception as e:
            logger.error(
                "artifact_file_deletion_failed",
                artifact_id=str(artifact_id),
                error=str(e),
            )
            # Continue with database deletion even if MinIO fails

        # Delete from database
        deleted = await artifact_repo.delete_artifact(conn, artifact_id)

    if not deleted:
        raise HTTPException(
            status_code=500, detail="Failed to delete artifact from database"
        )

    return {
        "success": True,
        "message": "Artifact deleted successfully",
    }
