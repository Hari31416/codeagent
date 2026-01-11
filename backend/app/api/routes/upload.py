"""
File upload API endpoints.

Handles file uploads to MinIO with atomic database registration.
"""

from uuid import UUID

from app.config import settings
from app.core.deps import CurrentActiveUser
from app.db.pool import get_system_db
from app.db.session_db import ArtifactRepository, ProjectRepository, SessionRepository
from app.services.workspace_service import WorkspaceService
from app.shared.logging import get_logger
from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse

logger = get_logger(__name__)
router = APIRouter(prefix="/api/v1", tags=["upload"])

workspace_service = WorkspaceService()
artifact_repo = ArtifactRepository()
session_repo = SessionRepository()
project_repo = ProjectRepository()


def get_file_type(filename: str) -> str:
    """Extract file type from filename."""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "unknown"
    return ext


def get_mime_type(file_type: str) -> str:
    """Get MIME type from file extension."""
    mime_map = {
        "csv": "text/csv",
        "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "xls": "application/vnd.ms-excel",
        "json": "application/json",
        "png": "image/png",
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "gif": "image/gif",
        "py": "text/x-python",
        "txt": "text/plain",
        "md": "text/markdown",
    }
    return mime_map.get(file_type, "application/octet-stream")


@router.post("/sessions/{session_id}/upload")
async def upload_file(
    session_id: UUID,
    current_user: CurrentActiveUser,
    file: UploadFile = File(...),
) -> JSONResponse:
    """
    Upload a file to a session's workspace.

    1. Saves file to MinIO under sessions/{session_id}/
    2. Creates artifact record in PostgreSQL
    3. Returns artifact_id and presigned URL
    """
    # Verify session ownership
    async with get_system_db() as conn:
        session = await session_repo.get_session(conn, session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        if session["user_id"] != current_user["user_id"]:
            raise HTTPException(status_code=403, detail="Access denied")

    try:
        # Read file content
        content = await file.read()
        file_name = file.filename or "untitled"
        file_type = get_file_type(file_name)
        mime_type = get_mime_type(file_type)

        # Upload to MinIO
        object_key = await workspace_service.upload_file(
            session_id=session_id,
            file_name=file_name,
            data=content,
            content_type=mime_type,
        )

        # Register in database
        async with get_system_db() as conn:
            artifact = await artifact_repo.create_artifact(
                conn=conn,
                session_id=session_id,
                file_name=file_name,
                file_type=file_type,
                mime_type=mime_type,
                size_bytes=len(content),
                minio_object_key=object_key,
            )

        # Generate standardized URL for immediate access
        presigned_url = (
            f"{settings.api_base_url}/artifacts/{artifact['artifact_id']}/download"
        )

        logger.info(
            "file_upload_complete",
            session_id=str(session_id),
            artifact_id=str(artifact["artifact_id"]),
            file_name=file_name,
            size_bytes=len(content),
        )

        return JSONResponse(
            content={
                "success": True,
                "data": {
                    "artifact_id": str(artifact["artifact_id"]),
                    "file_name": file_name,
                    "file_type": file_type,
                    "size_bytes": len(content),
                    "presigned_url": presigned_url,
                },
            },
            status_code=201,
        )

    except Exception as e:
        logger.error(
            "file_upload_failed",
            session_id=str(session_id),
            file_name=file.filename,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/projects/{project_id}/upload")
async def upload_project_file(
    project_id: UUID,
    current_user: CurrentActiveUser,
    file: UploadFile = File(...),
) -> JSONResponse:
    """
    Upload a file to a project's shared workspace.

    1. Saves file to MinIO under projects/{project_id}/
    2. Creates artifact record in PostgreSQL with project_id
    3. Returns artifact_id and presigned URL
    """
    # Verify project ownership
    async with get_system_db() as conn:
        project = await project_repo.get_project(conn, project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        if project["user_id"] != current_user["user_id"]:
            raise HTTPException(status_code=403, detail="Access denied")

    try:
        # Read file content
        content = await file.read()
        file_name = file.filename or "untitled"
        file_type = get_file_type(file_name)
        mime_type = get_mime_type(file_type)

        # Upload to MinIO
        object_key = await workspace_service.upload_project_file(
            project_id=project_id,
            file_name=file_name,
            data=content,
            content_type=mime_type,
        )

        # Register in database
        async with get_system_db() as conn:
            artifact = await artifact_repo.create_artifact(
                conn=conn,
                project_id=project_id,
                file_name=file_name,
                file_type=file_type,
                mime_type=mime_type,
                size_bytes=len(content),
                minio_object_key=object_key,
            )

        # Generate standardized URL for immediate access
        presigned_url = (
            f"{settings.api_base_url}/artifacts/{artifact['artifact_id']}/download"
        )

        logger.info(
            "project_file_upload_complete",
            project_id=str(project_id),
            artifact_id=str(artifact["artifact_id"]),
            file_name=file_name,
            size_bytes=len(content),
        )

        return JSONResponse(
            content={
                "success": True,
                "data": {
                    "artifact_id": str(artifact["artifact_id"]),
                    "file_name": file_name,
                    "file_type": file_type,
                    "size_bytes": len(content),
                    "presigned_url": presigned_url,
                },
            },
            status_code=201,
        )

    except Exception as e:
        logger.error(
            "project_file_upload_failed",
            project_id=str(project_id),
            file_name=file.filename,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail=str(e))
