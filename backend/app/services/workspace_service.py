"""
Workspace service - manages MinIO workspaces for sessions.

Uses the existing StorageService from app/core/storage.py
"""

from typing import BinaryIO
from uuid import UUID

from app.core.storage import get_storage_service
from app.shared.logging import get_logger

logger = get_logger(__name__)


class WorkspaceService:
    """
    Manages session workspaces in MinIO.

    Each session has a dedicated folder: sessions/{session_id}/
    """

    def __init__(self):
        self.storage = get_storage_service()

    def get_workspace_prefix(self, session_id: UUID) -> str:
        """Get the MinIO prefix for a session's workspace."""
        return f"sessions/{session_id}/"

    async def upload_file(
        self,
        session_id: UUID,
        file_name: str,
        data: bytes | BinaryIO,
        content_type: str = "application/octet-stream",
    ) -> str:
        """
        Upload a file to the session workspace.

        Returns:
            The MinIO object key
        """
        object_key = f"{self.get_workspace_prefix(session_id)}{file_name}"
        self.storage.upload(object_key, data, content_type)
        logger.info(
            "file_uploaded_to_workspace",
            session_id=str(session_id),
            file_name=file_name,
        )
        return object_key

    async def download_file(
        self,
        session_id: UUID,
        file_name: str,
    ) -> bytes:
        """Download a file from the session workspace."""
        object_key = f"{self.get_workspace_prefix(session_id)}{file_name}"
        return self.storage.download(object_key)

    async def get_presigned_url(
        self,
        session_id: UUID,
        file_name: str,
        expires_hours: int = 1,
    ) -> str:
        """Get a presigned URL for temporary file access."""
        from datetime import timedelta

        object_key = f"{self.get_workspace_prefix(session_id)}{file_name}"
        return self.storage.get_presigned_url(
            object_key, expires=timedelta(hours=expires_hours)
        )

    async def list_workspace_files(
        self,
        session_id: UUID,
    ) -> list[dict]:
        """List all files in a session's workspace."""
        prefix = self.get_workspace_prefix(session_id)
        return self.storage.list_objects(prefix=prefix, recursive=True)

    async def delete_workspace(
        self,
        session_id: UUID,
    ) -> int:
        """Delete all files in a session's workspace. Returns count deleted."""
        prefix = self.get_workspace_prefix(session_id)
        files = self.storage.list_objects(prefix=prefix, recursive=True)
        for file_info in files:
            self.storage.delete(file_info["name"])
        logger.info(
            "workspace_deleted",
            session_id=str(session_id),
            files_deleted=len(files),
        )
        return len(files)
