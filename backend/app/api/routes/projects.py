"""
Project management API endpoints.
"""

from uuid import UUID

from app.db.pool import get_system_db
from app.db.session_db import ProjectRepository, SessionRepository
from app.services.export_service import ExportService
from app.services.workspace_service import WorkspaceService
from app.shared.logging import get_logger
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

logger = get_logger(__name__)
router = APIRouter(prefix="/api/v1/projects", tags=["projects"])

project_repo = ProjectRepository()
session_repo = SessionRepository()
workspace_service = WorkspaceService()
export_service = ExportService()


class CreateProjectRequest(BaseModel):
    """Request model for creating a project."""

    user_id: UUID
    name: str
    description: str | None = None


class UpdateProjectRequest(BaseModel):
    """Request model for updating a project."""

    name: str | None = None
    description: str | None = None


@router.post("")
async def create_project(request: CreateProjectRequest):
    """
    Create a new project.

    Returns project_id and other project data.
    """
    try:
        async with get_system_db() as conn:
            project = await project_repo.create_project(
                conn,
                user_id=request.user_id,
                name=request.name,
                description=request.description,
            )
            return {"success": True, "data": project}
    except Exception as e:
        logger.error("create_project_failed", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{project_id}")
async def get_project(project_id: UUID):
    """Get project details by ID."""
    try:
        async with get_system_db() as conn:
            project = await project_repo.get_project(conn, project_id)
            if not project:
                raise HTTPException(status_code=404, detail="Project not found")
            return {"success": True, "data": project}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_project_failed", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{project_id}")
async def update_project(project_id: UUID, request: UpdateProjectRequest):
    """Update project metadata."""
    try:
        async with get_system_db() as conn:
            project = await project_repo.update_project(
                conn,
                project_id=project_id,
                name=request.name,
                description=request.description,
            )
            if not project:
                raise HTTPException(status_code=404, detail="Project not found")
            return {"success": True, "data": project}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("update_project_failed", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{project_id}")
async def delete_project(project_id: UUID):
    """
    Delete a project and all associated data.

    This will:
    1. Delete all sessions and their artifacts/messages
    2. Delete the project record from PostgreSQL
    """
    try:
        async with get_system_db() as conn:
            # 1. Delete all session workspaces
            sessions = await session_repo.list_sessions_by_project(
                conn,
                project_id=project_id,
                limit=1000,  # Cap at 1000 for safety, though projects likely satisfy this
            )
            for session in sessions:
                try:
                    await workspace_service.delete_workspace(session["session_id"])
                except Exception as e:
                    logger.warning(
                        "session_workspace_deletion_failed_during_project_delete",
                        session_id=str(session["session_id"]),
                        error=str(e),
                    )

            # 2. Delete project workspace
            try:
                await workspace_service.delete_project_workspace(project_id)
            except Exception as e:
                logger.warning(
                    "project_workspace_deletion_failed",
                    project_id=str(project_id),
                    error=str(e),
                )

            # 3. Delete from DB
            deleted = await project_repo.delete_project(conn, project_id)
            if not deleted:
                raise HTTPException(status_code=404, detail="Project not found")
            return {"success": True, "message": "Project deleted"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("delete_project_failed", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("")
async def list_projects(
    user_id: UUID = Query(..., description="User ID to filter projects"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """List projects for a user."""
    try:
        async with get_system_db() as conn:
            projects = await project_repo.list_projects_by_user(
                conn,
                user_id=user_id,
                limit=limit,
                offset=offset,
            )
            return {"success": True, "data": projects}
    except Exception as e:
        logger.error("list_projects_failed", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{project_id}/sessions")
async def list_project_sessions(
    project_id: UUID,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """List all sessions within a project."""
    try:
        async with get_system_db() as conn:
            # First verify project exists
            project = await project_repo.get_project(conn, project_id)
            if not project:
                raise HTTPException(status_code=404, detail="Project not found")

            sessions = await session_repo.list_sessions_by_project(
                conn,
                project_id=project_id,
                limit=limit,
                offset=offset,
            )
            return {"success": True, "data": sessions}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("list_project_sessions_failed", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{project_id}/export")
async def export_project(project_id: UUID):
    """
    Export all sessions in a project as JSON metadata and markdown.

    Returns:
        - metadata: Full project and session metadata
        - markdown: Combined markdown with embedded artifacts
        - filename: Suggested filename for download
        - session_count: Number of sessions exported
    """
    try:
        result = await export_service.export_project(project_id)
        return {
            "success": True,
            "data": {
                "metadata": result.metadata_json,
                "markdown": result.markdown_content,
                "filename": result.filename,
                "session_count": result.session_count,
            },
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("export_project_failed", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
