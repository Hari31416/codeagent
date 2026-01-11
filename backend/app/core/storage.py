"""
MinIO Storage Module

Provides object storage interface using MinIO (S3-compatible).
Handles file uploads, downloads, deletions, and presigned URL generation.
"""

from datetime import timedelta
from io import BytesIO
from typing import BinaryIO

import structlog
from minio import Minio
from minio.error import S3Error

from app.config import settings

logger = structlog.get_logger(__name__)


class StorageError(Exception):
    """Raised when storage operations fail."""

    pass


class StorageService:
    """MinIO object storage service with S3-compatible API."""

    def __init__(self):
        """Initialize MinIO client."""
        self.client = Minio(
            settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_secure,
        )
        self.bucket = settings.minio_bucket
        self._ensure_bucket_exists()

    def _ensure_bucket_exists(self) -> None:
        """Create bucket if it doesn't exist."""
        try:
            if not self.client.bucket_exists(self.bucket):
                self.client.make_bucket(self.bucket)
                logger.info("minio_bucket_created", bucket=self.bucket)
        except S3Error as e:
            logger.error(
                "minio_bucket_creation_failed", bucket=self.bucket, error=str(e)
            )
            raise StorageError(f"Failed to ensure bucket exists: {e}")

    def upload(
        self,
        object_name: str,
        data: bytes | BinaryIO,
        content_type: str = "application/octet-stream",
        metadata: dict[str, str] | None = None,
    ) -> str:
        """
        Upload a file to MinIO.

        Args:
            object_name: Key/path for the object in storage
            data: File data as bytes or file-like object
            content_type: MIME type of the file
            metadata: Optional metadata tags

        Returns:
            str: The object name/key

        Raises:
            StorageError: If upload fails
        """
        try:
            # Convert bytes to BytesIO if needed
            if isinstance(data, bytes):
                file_data = BytesIO(data)
                length = len(data)
            else:
                # For file-like objects, get size
                file_data = data
                file_data.seek(0, 2)  # Seek to end
                length = file_data.tell()
                file_data.seek(0)  # Reset to start

            self.client.put_object(
                bucket_name=self.bucket,
                object_name=object_name,
                data=file_data,
                length=length,
                content_type=content_type,
                metadata=metadata,
            )

            logger.info(
                "file_uploaded",
                object_name=object_name,
                size_bytes=length,
                content_type=content_type,
            )
            return object_name

        except S3Error as e:
            logger.error("upload_failed", object_name=object_name, error=str(e))
            raise StorageError(f"Failed to upload {object_name}: {e}")

    def download(self, object_name: str) -> bytes:
        """
        Download a file from MinIO.

        Args:
            object_name: Key/path of the object to download

        Returns:
            bytes: File content

        Raises:
            StorageError: If download fails
        """
        try:
            response = self.client.get_object(self.bucket, object_name)
            data = response.read()
            response.close()
            response.release_conn()

            logger.info(
                "file_downloaded", object_name=object_name, size_bytes=len(data)
            )
            return data

        except S3Error as e:
            logger.error("download_failed", object_name=object_name, error=str(e))
            raise StorageError(f"Failed to download {object_name}: {e}")

    def delete(self, object_name: str) -> None:
        """
        Delete a file from MinIO.

        Args:
            object_name: Key/path of the object to delete

        Raises:
            StorageError: If deletion fails
        """
        try:
            self.client.remove_object(self.bucket, object_name)
            logger.info("file_deleted", object_name=object_name)

        except S3Error as e:
            logger.error("deletion_failed", object_name=object_name, error=str(e))
            raise StorageError(f"Failed to delete {object_name}: {e}")

    def exists(self, object_name: str) -> bool:
        """
        Check if an object exists in MinIO.

        Args:
            object_name: Key/path of the object to check

        Returns:
            bool: True if object exists, False otherwise
        """
        try:
            self.client.stat_object(self.bucket, object_name)
            return True
        except S3Error:
            return False

    def get_presigned_url(
        self, object_name: str, expires: timedelta = timedelta(hours=1)
    ) -> str:
        """
        Generate a presigned URL for temporary file access.

        Args:
            object_name: Key/path of the object
            expires: URL expiration duration

        Returns:
            str: Presigned URL

        Raises:
            StorageError: If URL generation fails
        """
        try:
            url = self.client.presigned_get_object(
                bucket_name=self.bucket, object_name=object_name, expires=expires
            )

            # Replace internal endpoint with public endpoint if configured
            if settings.minio_public_endpoint:
                # Build the internal URL prefix to replace (protocol://host/bucket)
                protocol = "https" if settings.minio_secure else "http"
                internal_prefix = f"{protocol}://{settings.minio_endpoint}/{self.bucket}"
                # Replace with public endpoint + bucket
                url = url.replace(internal_prefix, f"{settings.minio_public_endpoint}/{self.bucket}", 1)

            logger.info(
                "presigned_url_generated",
                object_name=object_name,
                expires_seconds=expires.total_seconds(),
            )
            return url

        except S3Error as e:
            logger.error(
                "presigned_url_generation_failed", object_name=object_name, error=str(e)
            )
            raise StorageError(
                f"Failed to generate presigned URL for {object_name}: {e}"
            )

    def list_objects(self, prefix: str = "", recursive: bool = False) -> list[dict]:
        """
        List objects in the bucket with optional prefix filter.

        Args:
            prefix: Filter objects by prefix
            recursive: List recursively through subdirectories

        Returns:
            list[dict]: List of object metadata dictionaries
        """
        try:
            objects = self.client.list_objects(
                bucket_name=self.bucket, prefix=prefix, recursive=recursive
            )

            result = []
            for obj in objects:
                result.append(
                    {
                        "name": obj.object_name,
                        "size": obj.size,
                        "last_modified": obj.last_modified,
                        "etag": obj.etag,
                    }
                )

            logger.info("objects_listed", prefix=prefix, count=len(result))
            return result

        except S3Error as e:
            logger.error("list_objects_failed", prefix=prefix, error=str(e))
            raise StorageError(f"Failed to list objects with prefix '{prefix}': {e}")


# Singleton instance
_storage_service: StorageService | None = None


def get_storage_service() -> StorageService:
    """Get the singleton StorageService instance."""
    global _storage_service
    if _storage_service is None:
        import threading

        with threading.Lock():
            if _storage_service is None:
                _storage_service = StorageService()
    return _storage_service
