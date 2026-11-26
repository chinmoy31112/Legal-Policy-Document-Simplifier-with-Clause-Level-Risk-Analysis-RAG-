"""
Document service.

Business logic for file upload, validation, storage, and document management.
"""

import os
import re
import uuid
from pathlib import Path
from typing import Any
from uuid import UUID

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.exceptions import FileUploadError, NotFoundError, ValidationError
from app.core.logging import get_logger
from app.models.document import Document
from app.repositories.document_repo import DocumentRepository

logger = get_logger(__name__)
settings = get_settings()

# Allowed MIME types mapped to file extensions
MIME_TYPE_MAP: dict[str, str | None] = {
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
        name = base[: 200 - len(ext)] + ext
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


from app.document_processing import DocumentSegmenter
from app.repositories.clause_repo import ClauseRepository


class DocumentService:
    """Handles document upload, storage, and management."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.document_repo = DocumentRepository(session)
        self.clause_repo = ClauseRepository(session)
        self.segmenter = DocumentSegmenter(min_clause_length=50)

    async def upload_document(
        self,
        user_id: UUID,
        file: UploadFile,
        document_type: str = "other",
        jurisdiction: str | None = None,
    ) -> Document:
        """
        Upload and store a document file.

        Validates file type and size, saves to disk, creates DB record,
        extracts text, and segments into clauses.

        Raises:
            FileUploadError: If file validation fails.
        """
        import time

        t_upload_0 = time.perf_counter()
        if not file.filename:
            raise FileUploadError("No filename provided.")

        # Validate file extension
        ext = validate_file_extension(file.filename)

        # Read file content
        content = await file.read()
        file_size = len(content)

        # Validate file size
        if file_size == 0:
            raise ValidationError("Uploaded file is empty.")
        if file_size > settings.max_file_size_bytes:
            raise FileUploadError(
                f"File size ({file_size / 1024 / 1024:.1f} MB) exceeds "
                f"the maximum allowed size ({settings.max_file_size_mb} MB)."
            )

        # PDF magic bytes & scan inspection
        if ext == ".pdf":
            if not content.startswith(b"%PDF-"):
                raise ValidationError("Invalid PDF format: file lacks %PDF header signature.")
            try:
                import fitz

                from app.document_processing.extractor import is_scanned_pdf

                doc = fitz.open(stream=content, filetype="pdf")
                if doc.needs_pass or doc.is_encrypted:
                    doc.close()
                    raise ValidationError(
                        "Password-protected or encrypted PDF files are not supported."
                    )
                if doc.page_count == 0:
                    doc.close()
                    raise ValidationError("Uploaded PDF contains zero pages.")
                if is_scanned_pdf(doc):
                    doc.close()
                    raise ValidationError(
                        "Scanned PDFs are not supported in v1. Please upload a machine-readable, text-based PDF or document."
                    )
                doc.close()
            except ValidationError:
                raise
            except Exception as e:
                logger.warning("pdf_inspection_failed", error=str(e))
                raise ValidationError(f"Invalid or corrupt PDF file: {e}")

        # Sanitize and generate unique filename
        safe_name = sanitize_filename(file.filename)
        unique_filename = f"{uuid.uuid4().hex}_{safe_name}"

        # Create user-specific upload directory
        user_dir = settings.upload_path / str(user_id)
        user_dir.mkdir(parents=True, exist_ok=True)
        file_path = (user_dir / unique_filename).resolve()

        # Write file to disk
        try:
            file_path.write_bytes(content)
        except OSError as e:
            logger.error("file_write_error", error=str(e), path=str(file_path))
            raise FileUploadError(f"Failed to save file: {e}")

        # Create database record
        upload_duration = round(time.perf_counter() - t_upload_0, 4)
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
            raw_text=None,
            is_scanned=False,
            metadata={"upload_duration_seconds": upload_duration},
        )

        await self.session.commit()

        logger.info(
            "document_uploaded",
            document_id=str(document.id),
            user_id=str(user_id),
            filename=file.filename,
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

    async def delete_document(
        self,
        document_id: UUID,
        user_id: UUID,
        legacy_tasks_map: dict[UUID, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Cancel any running/queued jobs for a document (DB + Redis + ARQ, waiting up to 5s),
        delete files and DB records (results, clauses, jobs, document), purge tied AI caches,
        and return a report of what was purged and what is kept.

        Raises:
            NotFoundError: If the document doesn't exist or doesn't belong to the user.
        """
        from sqlalchemy import delete, select

        from app.core.cancellation import purge_ai_caches
        from app.models.analysis import AnalysisResult, DocumentAnalysis
        from app.models.clause import Clause
        from app.models.job import Job
        from app.services.job_service import JobService

        document = await self.document_repo.get_by_id_and_user(document_id, user_id)
        if document is None:
            raise NotFoundError("Document", str(document_id))

        # Capture clause texts for AI cache invalidation before deleting rows
        clause_res = await self.session.execute(
            select(Clause.content).where(Clause.document_id == document_id)
        )
        clause_texts = [row[0] for row in clause_res.fetchall() if row[0]]

        # 1. Cancel running/queued jobs and wait up to 5s for confirmation
        job_service = JobService(self.session)
        cancel_summary = await job_service.cancel_document_jobs(
            document_id=document_id,
            timeout_seconds=5.0,
            legacy_tasks_map=legacy_tasks_map,
        )

        # 2. Delete file from disk
        file_deleted = False
        file_path = Path(document.file_path)
        if not file_path.exists():
            cfg = get_settings()
            alt = cfg.upload_path / str(user_id) / document.filename
            if alt.exists():
                file_path = alt
        if file_path.exists():
            try:
                file_path.unlink()
                file_deleted = True
            except OSError as e:
                logger.warning("file_delete_error", error=str(e), path=str(file_path))

        # 3. Explicitly purge results, clauses, jobs, and document from database
        res_del = await self.session.execute(
            delete(AnalysisResult).where(AnalysisResult.document_id == document_id)
        )
        da_del = await self.session.execute(
            delete(DocumentAnalysis).where(DocumentAnalysis.document_id == document_id)
        )
        cls_del = await self.session.execute(
            delete(Clause).where(Clause.document_id == document_id)
        )
        job_del = await self.session.execute(delete(Job).where(Job.document_id == document_id))
        await self.document_repo.delete(document_id)
        await self.session.commit()

        # 4. Purge cached AI results tied to this document
        cache_purged = await purge_ai_caches(
            document_ids=[str(document_id)],
            clause_texts=clause_texts,
        )

        report: dict[str, Any] = {
            "purged": {
                "document_id": str(document_id),
                "analysis_results": int(res_del.rowcount or 0),
                "document_analyses": int(da_del.rowcount or 0),
                "clauses": int(cls_del.rowcount or 0),
                "jobs": int(job_del.rowcount or 0),
                "files": 1 if file_deleted else 0,
                **cache_purged,
                "cancellation": cancel_summary,
            },
            "kept": {
                "audit_logs": "Retained for audit compliance (no document text).",
                "call_ledger": "API quota telemetry entries retained without document content.",
                "reference_clauses": "Global precedent corpus unchanged.",
            },
        }

        logger.info(
            "document_deleted",
            document_id=str(document_id),
            user_id=str(user_id),
            purged=report["purged"],
            kept=report["kept"],
        )
        return report
