"""
ChromaDB retrieval service.

Manages the vector database for storing and retrieving legal clauses.
"""

from typing import Any, Sequence
import uuid
import chromadb
from chromadb.config import Settings as ChromaSettings
from chromadb.api.models.Collection import Collection

from app.config import get_settings
from app.core.exceptions import AIServiceError
from app.core.logging import get_logger

logger = get_logger(__name__)


class RetrievalService:
    """Service for managing vector storage and similarity search with ChromaDB."""

    def __init__(self):
        self.settings = get_settings()
        
        # Configure ChromaDB client (Server mode)
        # Using HTTPClient to connect to the Docker container in production
        if self.settings.is_production:
            try:
                # Assuming ChromaDB is running at chroma:8000 in docker-compose
                # We could pull these from config in the future
                self.client = chromadb.HttpClient(host="chroma", port=8000)
            except Exception as e:
                logger.warning("chroma_http_client_failed", error=str(e), fallback="PersistentClient")
                self.client = chromadb.PersistentClient(path=str(self.settings.chroma_path))
        else:
            # Embedded mode for local development
            self.client = chromadb.PersistentClient(path=str(self.settings.chroma_path))
            
        self.collection_name = self.settings.chroma_collection_name
        self._collection = None

    @property
    def collection(self) -> Collection:
        """Get or create the ChromaDB collection."""
        if self._collection is None:
            # We don't provide an embedding function here because we'll compute
            # embeddings explicitly using Google GenAI before inserting.
            try:
                self._collection = self.client.get_or_create_collection(
                    name=self.collection_name,
                    metadata={"hnsw:space": "cosine"} # Use cosine similarity
                )
                logger.info("chroma_collection_loaded", name=self.collection_name)
            except Exception as e:
                logger.error("chroma_collection_error", error=str(e))
                raise AIServiceError(f"Failed to access ChromaDB collection: {e}")
                
        return self._collection

    async def index_clauses(
        self, 
        ids: Sequence[str], 
        texts: Sequence[str], 
        embeddings: Sequence[list[float]],
        metadatas: Sequence[dict[str, Any]] | None = None
    ) -> None:
        """
        Index a batch of clauses with their embeddings into ChromaDB.
        
        Args:
            ids: List of unique string IDs (usually stringified UUIDs).
            texts: List of the raw clause text.
            embeddings: List of embedding vectors.
            metadatas: Optional list of metadata dictionaries.
        """
        if not ids or len(ids) != len(texts) or len(ids) != len(embeddings):
            raise ValueError("ids, texts, and embeddings must have the same length")
            
        if metadatas and len(metadatas) != len(ids):
            raise ValueError("metadatas must have the same length as ids if provided")
            
        try:
            # Ensure metadatas is the right shape even if None
            final_metadatas = metadatas if metadatas is not None else [{} for _ in ids]
            
            # ChromaDB doesn't allow None values in metadata dicts
            for meta in final_metadatas:
                keys_to_delete = [k for k, v in meta.items() if v is None]
                for k in keys_to_delete:
                    del meta[k]
                    
            self.collection.upsert(
                ids=list(ids),
                documents=list(texts),
                embeddings=list(embeddings),
                metadatas=list(final_metadatas)
            )
            
            logger.info("clauses_indexed", count=len(ids))
        except Exception as e:
            logger.error("chroma_index_error", error=str(e))
            raise AIServiceError(f"Failed to index clauses in ChromaDB: {e}")

    async def search(
        self, 
        query_embedding: list[float], 
        top_k: int | None = None,
        where_filter: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """
        Search for similar clauses using a query embedding.
        
        Args:
            query_embedding: The embedding vector of the search query.
            top_k: Number of results to return.
            where_filter: Optional ChromaDB where clause for metadata filtering.
            
        Returns:
            List of dictionaries containing id, distance, text, and metadata.
        """
        try:
            k = top_k or self.settings.retrieval_top_k
            
            # Execute query
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=k,
                where=where_filter,
                include=["documents", "metadatas", "distances"]
            )
            
            formatted_results = []
            
            # ChromaDB returns lists of lists because we can pass multiple query embeddings
            # We only passed one, so we take the 0th element of each return list
            if results["ids"] and len(results["ids"]) > 0:
                for i in range(len(results["ids"][0])):
                    formatted_results.append({
                        "id": results["ids"][0][i],
                        "distance": results["distances"][0][i] if "distances" in results and results["distances"] else 0.0,
                        "similarity": 1.0 - (results["distances"][0][i] if "distances" in results and results["distances"] else 0.0), # Assuming cosine distance
                        "text": results["documents"][0][i] if "documents" in results and results["documents"] else "",
                        "metadata": results["metadatas"][0][i] if "metadatas" in results and results["metadatas"] else {}
                    })
                    
            return formatted_results
            
        except Exception as e:
            logger.error("chroma_search_error", error=str(e))
            raise AIServiceError(f"Failed to search ChromaDB: {e}")

    async def delete_document(self, document_id: str | uuid.UUID) -> None:
        """
        Delete all clauses belonging to a specific document.
        
        This relies on the metadata containing 'kb_document_id'.
        """
        try:
            self.collection.delete(
                where={"kb_document_id": str(document_id)}
            )
            logger.info("chroma_document_deleted", document_id=str(document_id))
        except Exception as e:
            logger.error("chroma_delete_error", error=str(e), document_id=str(document_id))
            raise AIServiceError(f"Failed to delete document from ChromaDB: {e}")
