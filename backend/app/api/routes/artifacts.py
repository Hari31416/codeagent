"""
Artifact management API endpoints.
"""

from datetime import timedelta
from uuid import UUID

from app.core.storage import get_storage_service
from app.db.pool import get_system_db
from app.db.session_db import ArtifactRepository
from app.services.workspace_service import WorkspaceService
from app.shared.logging import get_logger
from fastapi import APIRouter, HTTPException, Query

logger = get_logger(__name__)
router = APIRouter(prefix="/api/v1/artifacts", tags=["artifacts"])

artifact_repo = ArtifactRepository()
storage_service = get_storage_service()
workspace_service = WorkspaceService()


@router.get("/{artifact_id}")
async def get_artifact(artifact_id: UUID):
    """Get artifact metadata by ID."""
    async with get_system_db() as conn:
        artifact = await artifact_repo.get_artifact(conn, artifact_id)

    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")

    return {
        "success": True,
        "data": {
            "artifact_id": str(artifact["artifact_id"]),
            "session_id": str(artifact["session_id"]),
            "file_name": artifact["file_name"],
            "file_type": artifact["file_type"],
            "mime_type": artifact["mime_type"],
            "size_bytes": artifact["size_bytes"],
            "created_at": artifact["created_at"].isoformat(),
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
                "created_at": a["created_at"].isoformat(),
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
                "created_at": a["created_at"].isoformat(),
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
