"""
Knowledge base service.

Business logic for managing the reference knowledge base, including
ingestion (extraction and segmentation) of new reference documents.
"""

from uuid import UUID

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, ValidationError, FileUploadError
from app.core.logging import get_logger
from app.document_processing import extract_document, DocumentSegmenter
from app.models.knowledge_base import KBDocument, KBClause
from app.repositories.knowledge_base_repo import KBDocumentRepository, KBClauseRepository
from app.schemas.knowledge_base import KBIngestionResponse

logger = get_logger(__name__)


class KnowledgeBaseService:
    """Handles knowledge base document and clause management."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.kb_doc_repo = KBDocumentRepository(session)
        self.kb_clause_repo = KBClauseRepository(session)
        self.segmenter = DocumentSegmenter(min_clause_length=20)

    async def get_all_documents(self, offset: int = 0, limit: int = 20) -> tuple[list[KBDocument], int]:
        """List all KB documents."""
        items, total = await self.kb_doc_repo.get_all(offset=offset, limit=limit)
        return list(items), total

    async def get_document(self, document_id: UUID) -> KBDocument:
        """Get a KB document by ID."""
        document = await self.kb_doc_repo.get_by_id(document_id)
        if not document:
            raise NotFoundError("KBDocument", str(document_id))
        return document

    async def get_clauses_for_document(self, document_id: UUID) -> list[KBClause]:
        """Get all clauses for a specific KB document."""
        # Ensure document exists
        await self.get_document(document_id)
        clauses = await self.kb_clause_repo.get_by_document(document_id)
        return list(clauses)

    async def ingest_document(
        self,
        file: UploadFile,
        title: str,
        document_type: str,
        jurisdiction: str | None = None,
    ) -> KBIngestionResponse:
        """
        Upload and ingest a document into the knowledge base.

        Extracts text, segments into clauses, and stores them.
        Embeddings will be generated in Phase 4.
        """
        if not file.filename:
            raise FileUploadError("No filename provided.")

        # For KB ingestion, we can just save it to a temporary file
        # or read it into memory. For large files, saving to disk is better.
        import tempfile
        import os

        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{file.filename}") as temp_file:
                content = await file.read()
                temp_file.write(content)
                temp_path = temp_file.name

            # 1. Extract text
            extraction_result = extract_document(temp_path)
            if extraction_result.errors:
                logger.warning("kb_extraction_warnings", errors=extraction_result.errors)
                if not extraction_result.raw_text:
                    raise ValidationError(f"Could not extract text: {extraction_result.errors}")

            # 2. Segment into clauses
            segments = self.segmenter.segment(extraction_result)

            # 3. Create KB Document
            kb_doc = await self.kb_doc_repo.create(
                title=title,
                document_type=document_type,
                source=file.filename,
                jurisdiction=jurisdiction,
                content=extraction_result.raw_text,
                status="active"
            )

            # 4. Create KB Clauses
            kb_clauses = []
            for segment in segments:
                kb_clause = KBClause(
                    kb_document_id=kb_doc.id,
                    clause_number=segment.clause_number,
                    title=segment.title,
                    content=segment.content,
                    category=segment.category,
                )
                kb_clauses.append(kb_clause)
            
            await self.kb_clause_repo.bulk_create(kb_clauses)
            await self.session.commit()
            
            # TODO (Phase 4): Generate embeddings for these clauses
            # For now, clauses_embedded is 0

            return KBIngestionResponse(
                document_id=kb_doc.id,
                title=kb_doc.title,
                clauses_extracted=len(kb_clauses),
                clauses_embedded=0,
                status="success",
                message=f"Successfully ingested {len(kb_clauses)} clauses.",
            )
            
        finally:
            if 'temp_path' in locals() and os.path.exists(temp_path):
                try:
                    os.unlink(temp_path)
                except Exception as e:
                    logger.warning(f"Failed to delete temporary file {temp_path}: {e}")

    async def delete_document(self, document_id: UUID) -> None:
        """Delete a KB document and its clauses."""
        # Ensure document exists
        await self.get_document(document_id)
        
        # Deleting the document will cascade delete the clauses in Postgres
        await self.kb_doc_repo.delete(document_id)
        await self.session.commit()
        
        # TODO (Phase 4): Delete embeddings from ChromaDB
