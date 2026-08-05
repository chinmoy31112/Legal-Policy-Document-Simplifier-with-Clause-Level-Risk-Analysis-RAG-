"""
Document service.

Business logic for file upload, validation, storage, and document management.
"""

import os
import re
import uuid
from pathlib import Path
from uuid import UUID

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.exceptions import FileUploadError, NotFoundError, AuthorizationError
from app.core.logging import get_logger
from app.models.document import Document
from app.repositories.document_repo import DocumentRepository

logger = get_logger(__name__)
settings = get_settings()

# Allowed MIME types mapped to file extensions
MIME_TYPE_MAP: dict[str, str] = {
    "application/pdf": ".pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "text/plain": ".txt",
    "text/markdown": ".md",
    "application/json": ".json",
    "application/octet-stream": None,  # Fallback: check extension
}


def sanitize_filename(filename: str) -> str:
    """
    Sanitize a filename: remove dangerous characters, limit length.
    """
    # Remove path separators and null bytes
    name = filename.replace("/", "_").replace("\\", "_").replace("\x00", "")
    # Keep only safe characters
    name = re.sub(r"[^\w\s\-.]", "_", name)
    # Collapse multiple underscores/spaces
    name = re.sub(r"[\s_]+", "_", name).strip("_")
    # Limit length
    if len(name) > 200:
        base, ext = os.path.splitext(name)
        name = base[:200 - len(ext)] + ext
    return name or "unnamed_document"


def validate_file_extension(filename: str) -> str:
    """
    Validate that the file extension is allowed.

    Returns the validated extension.
    Raises FileUploadError if the extension is not allowed.
    """
    ext = os.path.splitext(filename)[1].lower()
    if ext not in settings.allowed_file_types:
        raise FileUploadError(
            f"File type '{ext}' is not supported. "
            f"Allowed types: {', '.join(settings.allowed_file_types)}"
        )
    return ext


class DocumentService:
    """Handles document upload, storage, and management."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.document_repo = DocumentRepository(session)

    async def upload_document(
        self,
        user_id: UUID,
        file: UploadFile,
        document_type: str = "other",
        jurisdiction: str | None = None,
    ) -> Document:
        """
        Upload and store a document file.

        Validates file type and size, saves to disk, creates DB record.

        Raises:
            FileUploadError: If file validation fails.
        """
        if not file.filename:
            raise FileUploadError("No filename provided.")

        # Validate file extension
        ext = validate_file_extension(file.filename)

        # Read file content
        content = await file.read()
        file_size = len(content)

        # Validate file size
        if file_size == 0:
            raise FileUploadError("Uploaded file is empty.")
        if file_size > settings.max_file_size_bytes:
            raise FileUploadError(
                f"File size ({file_size / 1024 / 1024:.1f} MB) exceeds "
                f"the maximum allowed size ({settings.max_file_size_mb} MB)."
            )

        # Sanitize and generate unique filename
        safe_name = sanitize_filename(file.filename)
        unique_filename = f"{uuid.uuid4().hex}_{safe_name}"

        # Create user-specific upload directory
        user_dir = settings.upload_path / str(user_id)
        user_dir.mkdir(parents=True, exist_ok=True)
        file_path = user_dir / unique_filename

        # Write file to disk
        try:
            file_path.write_bytes(content)
        except OSError as e:
            logger.error("file_write_error", error=str(e), path=str(file_path))
            raise FileUploadError(f"Failed to save file: {e}")

        # Create database record
        document = await self.document_repo.create(
            user_id=user_id,
            filename=unique_filename,
            original_filename=file.filename,
            file_path=str(file_path),
            file_type=ext.lstrip("."),
            file_size=file_size,
            document_type=document_type,
            jurisdiction=jurisdiction,
            status="uploaded",
        )
        await self.session.commit()

        logger.info(
            "document_uploaded",
            document_id=str(document.id),
            user_id=str(user_id),
            filename=file.filename,
            size=file_size,
        )
        return document

    async def list_documents(
        self,
        user_id: UUID,
        offset: int = 0,
        limit: int = 20,
        status_filter: str | None = None,
        document_type: str | None = None,
    ) -> tuple[list[Document], int]:
        """List documents for a user with optional filters."""
        items, total = await self.document_repo.get_by_user(
            user_id=user_id,
            offset=offset,
            limit=limit,
            status_filter=status_filter,
            document_type=document_type,
        )
        return list(items), total

    async def get_document(self, document_id: UUID, user_id: UUID) -> Document:
        """
        Get a document by ID, scoped to the requesting user.

        Raises:
            NotFoundError: If the document doesn't exist or doesn't belong to the user.
        """
        document = await self.document_repo.get_by_id_and_user(document_id, user_id)
        if document is None:
            raise NotFoundError("Document", str(document_id))
        return document

    async def delete_document(self, document_id: UUID, user_id: UUID) -> None:
        """
        Delete a document and its file from disk.

        Raises:
            NotFoundError: If the document doesn't exist or doesn't belong to the user.
        """
        document = await self.document_repo.get_by_id_and_user(document_id, user_id)
        if document is None:
            raise NotFoundError("Document", str(document_id))

        # Delete file from disk
        file_path = Path(document.file_path)
        if file_path.exists():
            try:
                file_path.unlink()
            except OSError as e:
                logger.warning("file_delete_error", error=str(e), path=str(file_path))

        # Delete from database
        await self.document_repo.delete(document_id)
        await self.session.commit()

        logger.info(
            "document_deleted",
            document_id=str(document_id),
            user_id=str(user_id),
        )
