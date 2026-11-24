# ADR 001: Vector Store Selection (pgvector vs. ChromaDB)

## Status
Accepted

## Context
The application relies on dense vector retrieval over a curated knowledge base of 150–300 standard and risky legal reference clauses. Clause vectors are generated using Google's `gemini-embedding-2` model and must be compared against contract clause embeddings to surface relevant precedents before the LLM performs risk assessment.

We evaluated two vector storage architectures:
1. **pgvector** (PostgreSQL extension storing dense vectors directly inside relational tables).
2. **ChromaDB** (Standalone AI-native vector database run as an embedded or client-server service).

## Trade-offs in Three Lines
1. **pgvector** eliminates an additional distributed service by keeping vectors, clauses, and relational metadata in one ACID-compliant PostgreSQL instance with unified transactions and backups.
2. **ChromaDB** provides an out-of-the-box HNSW index with zero PostgreSQL extension compiling, but adds an isolated datastore process, separate backup lifecycle, and synchronization overhead.
3. For our dataset scale (150–10,000 vectors), **pgvector** IVFFlat/HNSW indexes run entirely in RAM with sub-5ms latency, whereas running Chroma alongside PostgreSQL doubles Docker memory footprints unnecessarily.

## Decision
We select **pgvector** (hosted on PostgreSQL 16 via the official `pgvector/pgvector:pg16` Docker container).

To ensure complete modularity and prevent vendor lock-in, all vector operations will be placed strictly behind an abstract Python interface:
```python
class VectorStore(ABC):
    @abstractmethod
    async def add_vectors(self, vectors: list[VectorRecord]) -> None: ...
    @abstractmethod
    async def search(self, query_vector: list[float], top_k: int, filters: dict | None = None) -> list[RetrievalResult]: ...
```

## Consequences
- Single PostgreSQL database container runs relational data and vector indexes.
- Complete support for transactional consistency and cascading deletes (`ON DELETE CASCADE`).
- Requires the `pgvector` extension enabled via Alembic migrations (`CREATE EXTENSION IF NOT EXISTS vector;`).
- Model name and dimension must be explicitly stored with every vector record to enforce schema validation on queries.
