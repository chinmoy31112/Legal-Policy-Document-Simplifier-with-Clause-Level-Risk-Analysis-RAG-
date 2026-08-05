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


from app.ai.embedding import EmbeddingService
from app.ai.retrieval import RetrievalService

class KnowledgeBaseService:
    """Handles knowledge base document and clause management."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.kb_doc_repo = KBDocumentRepository(session)
        self.kb_clause_repo = KBClauseRepository(session)
        self.segmenter = DocumentSegmenter(min_clause_length=20)
        self.embedding_service = EmbeddingService()
        self.retrieval_service = RetrievalService()

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

        Extracts text, segments into clauses, generates embeddings,
        and stores them in PostgreSQL and ChromaDB.
        """
        if not file.filename:
            raise FileUploadError("No filename provided.")

        import tempfile
        import os
        import uuid

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

            if not segments:
                raise ValidationError("Failed to extract any usable clauses from the document.")

            # 3. Create KB Document
            kb_doc = await self.kb_doc_repo.create(
                title=title,
                document_type=document_type,
                source=file.filename,
                jurisdiction=jurisdiction,
                content=extraction_result.raw_text,
                status="active"
            )

            # 4. Generate Embeddings
            texts_to_embed = [segment.content for segment in segments]
            embeddings = await self.embedding_service.generate_embeddings(texts_to_embed)
            
            if len(embeddings) != len(segments):
                raise AIServiceError(f"Embedding count mismatch. Expected {len(segments)}, got {len(embeddings)}.")

            # 5. Create DB Clauses and prepare for ChromaDB
            kb_clauses = []
            chroma_ids = []
            chroma_texts = []
            chroma_metadatas = []

            for i, segment in enumerate(segments):
                # Generate a stable UUID for the clause
                clause_id = uuid.uuid4()
                chroma_id = str(clause_id)
                
                kb_clause = KBClause(
                    id=clause_id,
                    kb_document_id=kb_doc.id,
                    clause_number=segment.clause_number,
                    title=segment.title,
                    content=segment.content,
                    category=segment.category,
                    chromadb_id=chroma_id
                )
                kb_clauses.append(kb_clause)
                
                # Prepare ChromaDB inputs
                chroma_ids.append(chroma_id)
                chroma_texts.append(segment.content)
                chroma_metadatas.append({
                    "kb_document_id": str(kb_doc.id),
                    "document_type": document_type,
                    "title": segment.title or "",
                    "category": segment.category or "",
                    "jurisdiction": jurisdiction or ""
                })
            
            # Save to Postgres
            await self.kb_clause_repo.bulk_create(kb_clauses)
            await self.session.commit()
            
            # Save to ChromaDB
            await self.retrieval_service.index_clauses(
                ids=chroma_ids,
                texts=chroma_texts,
                embeddings=embeddings,
                metadatas=chroma_metadatas
            )

            return KBIngestionResponse(
                document_id=kb_doc.id,
                title=kb_doc.title,
                clauses_extracted=len(kb_clauses),
                clauses_embedded=len(embeddings),
                status="success",
                message=f"Successfully ingested and embedded {len(kb_clauses)} clauses.",
            )
            
        finally:
            if 'temp_path' in locals() and os.path.exists(temp_path):
                try:
                    os.unlink(temp_path)
                except Exception as e:
                    logger.warning(f"Failed to delete temporary file {temp_path}: {e}")

    async def delete_document(self, document_id: UUID) -> None:
        """Delete a KB document and its clauses from both Postgres and ChromaDB."""
        # Ensure document exists
        await self.get_document(document_id)
        
        # Deleting the document will cascade delete the clauses in Postgres
        await self.kb_doc_repo.delete(document_id)
        await self.session.commit()
        
        # Delete embeddings from ChromaDB
        await self.retrieval_service.delete_document(str(document_id))
