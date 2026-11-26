"""
Knowledge Base Service coordinating multi-format document ingestion and retrieval.

Phase 3 Deliverables:
- Ingestion from PDF, DOCX, TXT, JSON, Markdown (extract -> segment -> embed -> store).
- Idempotency enforced by normalized SHA-256 text hash.
- Vector store integration behind interface with full metadata.
- Clean CRUD, stats, and query methods.
"""

import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.embedding import GeminiEmbedder
from app.ai.interfaces import Embedder, VectorStore
from app.ai.retrieval import RetrievalResponse, RetrievalService
from app.ai.vector_store import get_vector_store
from app.core.config import get_settings
from app.core.exceptions import FileUploadError, NotFoundError, ValidationError
from app.core.logging import get_logger
from app.document_processing import segment_document
from app.document_processing.formats import extract_document
from app.models.knowledge_base import KBClause, KBDocument
from app.repositories.knowledge_base_repo import KBClauseRepository, KBDocumentRepository
from app.schemas.knowledge_base import KBIngestionResponse

logger = get_logger(__name__)


class KnowledgeBaseService:
    """
    Manages knowledge base reference documents and clauses across formats.
    Coordinates extraction, segmentation, hash-based idempotency, embedding, and vector storage.
    """

    def __init__(
        self,
        session: AsyncSession | None = None,
        embedder: Embedder | None = None,
        vector_store: VectorStore | None = None,
    ):
        self.session = session
        self.settings = get_settings()
        self.embedder = embedder or GeminiEmbedder()
        self.vector_store = vector_store or get_vector_store()
        self.retrieval_service = RetrievalService(
            embedder=self.embedder,
            vector_store=self.vector_store,
        )

        self.kb_doc_repo: KBDocumentRepository | None = None
        self.kb_clause_repo: KBClauseRepository | None = None

        if session is not None:
            self.kb_doc_repo = KBDocumentRepository(session)
            self.kb_clause_repo = KBClauseRepository(session)

        # Set of known clause hashes for in-memory idempotency check
        self._indexed_hashes: set[str] = set()

    def _hash_text(self, text: str) -> str:
        """Compute normalized SHA-256 hash for clause text."""
        normalized = " ".join(text.split())
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    async def index_reference_clauses_file(
        self,
        json_path: str | Path,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """
        Index curated reference clauses from a JSON file (e.g. reference_clauses.json).
        Enforces idempotency by text hash.
        """
        path = Path(json_path)
        if not path.exists():
            raise FileNotFoundError(f"Reference clauses file not found: {path}")

        raw_data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw_data, list):
            raise ValidationError(
                f"Expected a JSON list of reference clauses, got {type(raw_data)}"
            )

        return await self.index_reference_clauses(raw_data, source=path.name, dry_run=dry_run)

    async def index_reference_clauses(
        self,
        clauses: list[dict[str, Any]],
        source: str = "curated_reference",
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """
        Index a list of reference clause dictionaries.
        Idempotent by text hash: clauses already indexed are skipped.
        """
        if not clauses:
            return {"total": 0, "indexed": 0, "skipped": 0, "dry_run": dry_run}

        to_index: list[dict[str, Any]] = []
        skipped = 0

        for item in clauses:
            text_content = item.get("text", item.get("content", "")).strip()
            if not text_content:
                continue

            h = self._hash_text(text_content)
            if h in self._indexed_hashes:
                skipped += 1
                continue

            item_copy = dict(item)
            item_copy["text"] = text_content
            item_copy["text_hash"] = h
            if "source" not in item_copy:
                item_copy["source"] = source
            to_index.append(item_copy)

        if dry_run or not to_index:
            return {
                "total": len(clauses),
                "indexed": len(to_index) if dry_run else 0,
                "skipped": skipped,
                "dry_run": dry_run,
            }

        indexed_count = await self.retrieval_service.index_reference_clauses(to_index)
        for item in to_index:
            self._indexed_hashes.add(item["text_hash"])

        logger.info(
            "reference_clauses_indexed",
            total=len(clauses),
            indexed=indexed_count,
            skipped=skipped,
        )

        return {
            "total": len(clauses),
            "indexed": indexed_count,
            "skipped": skipped,
            "dry_run": False,
        }

    async def ingest_file(
        self,
        file_path: str | Path,
        title: str | None = None,
        document_type: str | None = None,
        jurisdiction: str | None = None,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """
        Ingest a file (PDF, DOCX, TXT, Markdown, JSON) into the Knowledge Base.
        Extracts text, segments into logical clauses, generates embeddings,
        and saves into vector store and relational database (if session is present).
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        ext = path.suffix.lower()
        effective_title = title or path.stem.replace("_", " ").title()
        effective_type = document_type or "general_reference"

        # 1. If it's a JSON file with an array of reference clauses, route to reference clause indexer
        if ext == ".json":
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                if (
                    isinstance(data, list)
                    and len(data) > 0
                    and isinstance(data[0], dict)
                    and "text" in data[0]
                ):
                    return await self.index_reference_clauses(
                        data, source=path.name, dry_run=dry_run
                    )
            except Exception:
                pass  # Fall through to general extraction

        # 2. Extract document text using multi-format extract_document
        extraction = extract_document(path)
        if extraction.errors and not extraction.raw_text:
            raise ValidationError(f"Extraction failed for {path.name}: {extraction.errors}")

        # 3. Segment into logical clauses
        segments = segment_document(extraction, doc_id=path.stem)
        if not segments:
            raise ValidationError(f"No usable clauses segmented from {path.name}")

        # 4. Check idempotency by text hash
        to_embed_segments = []
        skipped_count = 0
        for seg in segments:
            h = self._hash_text(seg.text)
            if h in self._indexed_hashes:
                skipped_count += 1
                continue
            to_embed_segments.append(seg)

        if dry_run:
            return {
                "file": path.name,
                "title": effective_title,
                "document_type": effective_type,
                "clauses_extracted": len(segments),
                "clauses_to_index": len(to_embed_segments),
                "clauses_skipped": skipped_count,
                "dry_run": True,
            }

        # 5. Embed and index into VectorStore
        indexed_count = 0
        if to_embed_segments:
            clause_dicts = [
                {
                    "id": f"{path.stem}_{seg.id}",
                    "title": seg.title or f"Clause {seg.clause_number or ''}".strip(),
                    "text": seg.text,
                    "category": seg.category or "General",
                    "document_type": effective_type,
                    "source": path.name,
                    "jurisdiction": jurisdiction or "General",
                    "version": "1.0.0",
                    "language": "en",
                    "why_standard_or_risky": f"Standard clause from {effective_title}",
                    "text_hash": self._hash_text(seg.text),
                }
                for seg in to_embed_segments
            ]
            indexed_count = await self.retrieval_service.index_reference_clauses(clause_dicts)
            for c in clause_dicts:
                self._indexed_hashes.add(c["text_hash"])

        # 6. Optional DB persistence if session is active
        kb_doc_id = None
        if (
            self.session is not None
            and self.kb_doc_repo is not None
            and self.kb_clause_repo is not None
        ):
            kb_doc = await self.kb_doc_repo.create(
                title=effective_title,
                document_type=effective_type,
                source=path.name,
                jurisdiction=jurisdiction,
                content=extraction.raw_text,
                status="active",
            )
            kb_doc_id = kb_doc.id

            db_clauses = [
                KBClause(
                    id=uuid4(),
                    kb_document_id=kb_doc.id,
                    clause_number=seg.clause_number,
                    title=seg.title,
                    content=seg.text,
                    category=seg.category or "General",
                    metadata_={
                        "page": seg.page,
                        "text_hash": self._hash_text(seg.text),
                        "bounding_boxes": [
                            b.model_dump() if hasattr(b, "model_dump") else b
                            for b in seg.bounding_boxes
                        ],
                    },
                )
                for seg in segments
            ]
            await self.kb_clause_repo.bulk_create(db_clauses)
            await self.session.commit()

        logger.info(
            "file_ingested_successfully",
            path=path.name,
            total_clauses=len(segments),
            indexed=indexed_count,
            skipped=skipped_count,
        )

        return {
            "file": path.name,
            "title": effective_title,
            "document_type": effective_type,
            "document_id": str(kb_doc_id) if kb_doc_id else None,
            "clauses_extracted": len(segments),
            "clauses_indexed": indexed_count,
            "clauses_skipped": skipped_count,
            "dry_run": False,
        }

    async def ingest_document(
        self,
        file: UploadFile,
        title: str,
        document_type: str,
        jurisdiction: str | None = None,
    ) -> KBIngestionResponse:
        """Upload and ingest a document via FastAPI UploadFile."""
        if not file.filename:
            raise FileUploadError("No filename provided.")

        with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{file.filename}") as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_path = temp_file.name

        try:
            res = await self.ingest_file(
                file_path=temp_path,
                title=title,
                document_type=document_type,
                jurisdiction=jurisdiction,
            )
            doc_id = UUID(res["document_id"]) if res.get("document_id") else uuid4()
            return KBIngestionResponse(
                document_id=doc_id,
                title=title,
                clauses_extracted=res.get("clauses_extracted", 0),
                clauses_embedded=res.get("clauses_indexed", 0),
                status="success",
                message=f"Successfully ingested and embedded {res.get('clauses_indexed', 0)} clauses.",
            )
        finally:
            if os.path.exists(temp_path):
                try:
                    os.unlink(temp_path)
                except Exception:
                    pass

    async def retrieve(
        self,
        query_text: str,
        top_k: int | None = None,
        category: str | None = None,
        min_similarity: float | None = None,
    ) -> RetrievalResponse:
        """Search reference clauses for matching query clause text."""
        return await self.retrieval_service.retrieve(
            query_text=query_text,
            top_k=top_k,
            category=category,
            min_similarity=min_similarity,
        )

    async def get_stats(self) -> dict[str, Any]:
        """Report statistics on indexed reference clauses, model, and categories."""
        # Query vector store internal records if InMemoryVectorStore
        records: list[Any] = []
        if hasattr(self.vector_store, "_records"):
            records = list(self.vector_store._records.values())
        elif hasattr(self.vector_store, "_fallback") and hasattr(
            self.vector_store._fallback, "_records"
        ):
            records = list(self.vector_store._fallback._records.values())

        categories: dict[str, int] = {}
        doc_types: dict[str, int] = {}
        for r in records:
            cat = r.metadata.get("category", "General")
            categories[cat] = categories.get(cat, 0) + 1
            dt = r.metadata.get("document_type", "General")
            doc_types[dt] = doc_types.get(dt, 0) + 1

        db_docs_count = 0
        if self.session is not None and self.kb_doc_repo is not None:
            try:
                _, db_docs_count = await self.kb_doc_repo.get_all(limit=1)
            except Exception:
                pass

        return {
            "embedding_model": self.embedder.model_name,
            "embedding_dimension": self.embedder.dimension,
            "vector_store_type": self.settings.vector_store_type,
            "total_vectors": len(records),
            "total_clauses": len(records),
            "total_db_documents": db_docs_count,
            "categories": categories,
            "document_types": doc_types,
        }

    async def list_clauses(
        self,
        category: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """List indexed reference clauses with metadata."""
        records: list[Any] = []
        if hasattr(self.vector_store, "_records"):
            records = list(self.vector_store._records.values())
        elif hasattr(self.vector_store, "_fallback") and hasattr(
            self.vector_store._fallback, "_records"
        ):
            records = list(self.vector_store._fallback._records.values())

        filtered: list[dict[str, Any]] = []
        for r in records:
            if category and r.metadata.get("category", "").lower() != category.lower():
                continue
            filtered.append(
                {
                    "id": r.id,
                    "title": r.metadata.get("title", ""),
                    "category": r.metadata.get("category", ""),
                    "document_type": r.metadata.get("document_type", ""),
                    "jurisdiction": r.metadata.get("jurisdiction", ""),
                    "why_standard_or_risky": r.metadata.get("why_standard_or_risky", ""),
                    "text_preview": r.metadata.get("text", "")[:120] + "..."
                    if len(r.metadata.get("text", "")) > 120
                    else r.metadata.get("text", ""),
                }
            )
            if len(filtered) >= limit:
                break
        return filtered

    async def delete_clause(self, clause_id: str) -> bool:
        """Delete a vector clause by ID from vector store."""
        await self.vector_store.delete_vectors([clause_id])
        return True

    async def get_all_documents(
        self, offset: int = 0, limit: int = 20
    ) -> tuple[list[KBDocument], int]:
        """List all KB documents from DB if session is available."""
        if self.kb_doc_repo is None:
            return [], 0
        items, total = await self.kb_doc_repo.get_all(offset=offset, limit=limit)
        return list(items), total

    async def get_document(self, document_id: UUID) -> KBDocument:
        """Get a KB document by ID from DB."""
        if self.kb_doc_repo is None:
            raise NotFoundError("KBDocument", str(document_id))
        document = await self.kb_doc_repo.get_by_id(document_id)
        if not document:
            raise NotFoundError("KBDocument", str(document_id))
        return document

    async def get_clauses_for_document(self, document_id: UUID) -> list[KBClause]:
        """Get all clauses for a specific KB document from DB."""
        if self.kb_clause_repo is None:
            return []
        await self.get_document(document_id)
        clauses = await self.kb_clause_repo.get_by_document(document_id)
        return list(clauses)

    async def delete_document(self, document_id: UUID) -> None:
        """Delete a KB document and cascade delete clauses."""
        if self.kb_doc_repo is not None and self.session is not None:
            await self.get_document(document_id)
            await self.kb_doc_repo.delete(document_id)
            await self.session.commit()
