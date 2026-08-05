# Architecture Documentation

## System Architecture

```mermaid
graph TB
    subgraph Client["Client Layer"]
        Browser[Web Browser]
    end

    subgraph Frontend["Frontend (Next.js 15)"]
        AppRouter[App Router]
        Components[React Components]
        PDFViewer[PDF.js Viewer]
        StateManagement[TanStack Query]
    end

    subgraph API_Gateway["API Layer"]
        FastAPI[FastAPI Server]
        Auth[JWT Auth Middleware]
        RateLimit[Rate Limiter]
        CORS[CORS Middleware]
    end

    subgraph Business["Business Logic"]
        DocService[Document Service]
        AnalysisService[Analysis Service]
        KBService[KB Service]
        ExportService[Export Service]
        SearchService[Search Service]
    end

    subgraph AI_Layer["AI Pipeline"]
        Extractor[PDF Extractor<br/>PyMuPDF]
        Segmenter[Clause Segmenter]
        Embedder[Embedding Service<br/>gemini-embedding-2]
        Retriever[Retrieval Service<br/>ChromaDB]
        Reasoner[LLM Reasoner<br/>Gemini 2.5 Flash]
        PromptEngine[Prompt Engine]
        ResponseParser[Response Parser]
    end

    subgraph Data["Data Layer"]
        PostgreSQL[(PostgreSQL 16)]
        ChromaDB[(ChromaDB<br/>Embedded)]
        FileStorage[File Storage<br/>Local / S3]
    end

    Browser --> AppRouter
    AppRouter --> Components
    Components --> PDFViewer
    Components --> StateManagement
    StateManagement --> FastAPI

    FastAPI --> Auth
    FastAPI --> RateLimit
    FastAPI --> CORS
    FastAPI --> DocService
    FastAPI --> AnalysisService
    FastAPI --> KBService
    FastAPI --> ExportService
    FastAPI --> SearchService

    DocService --> Extractor
    Extractor --> Segmenter
    AnalysisService --> Embedder
    Embedder --> Retriever
    Retriever --> Reasoner
    Reasoner --> PromptEngine
    Reasoner --> ResponseParser
    KBService --> Embedder

    DocService --> PostgreSQL
    AnalysisService --> PostgreSQL
    KBService --> PostgreSQL
    Embedder --> ChromaDB
    Retriever --> ChromaDB
    DocService --> FileStorage
```

## RAG Pipeline Flow

```mermaid
sequenceDiagram
    participant U as User
    participant FE as Frontend
    participant API as FastAPI
    participant DP as Doc Processor
    participant EMB as Embedder
    participant VDB as ChromaDB
    participant LLM as Gemini Flash

    U->>FE: Upload Document
    FE->>API: POST /api/v1/documents/upload
    API->>DP: Extract Text (PyMuPDF)
    DP->>DP: Detect Scanned → OCR if needed
    DP->>DP: Segment into Clauses
    API-->>FE: Document ID + Status

    U->>FE: Start Analysis
    FE->>API: POST /api/v1/analysis/documents/{id}/analyze
    
    loop For Each Clause
        API->>EMB: Generate Embedding (gemini-embedding-2)
        EMB->>VDB: Store Clause Embedding
        EMB->>VDB: Query Top-K Similar (K=5)
        VDB-->>API: Retrieved Reference Clauses
        API->>LLM: Analyze Clause + Retrieved Context
        LLM-->>API: Structured JSON Analysis
        API->>API: Parse + Validate + Store
    end
    
    API->>LLM: Generate Document Summary
    LLM-->>API: Overall Risk Assessment
    API-->>FE: Analysis Complete (SSE)
    FE-->>U: Display Results
```

## Data Flow

1. **Upload**: User uploads PDF → stored on disk → metadata in PostgreSQL
2. **Extract**: PyMuPDF extracts text, detects structure (headings, lists, numbering)
3. **Segment**: Rule-based segmenter splits into logical legal clauses
4. **Embed**: Each clause → gemini-embedding-2 → vector stored in ChromaDB
5. **Retrieve**: For each clause, query ChromaDB for Top-5 similar reference clauses
6. **Analyze**: Gemini 2.5 Flash receives original + retrieved context → structured JSON
7. **Store**: Analysis results persisted in PostgreSQL
8. **Display**: Frontend renders clause cards, risk badges, PDF highlights

## Security Architecture

- **Authentication**: JWT access tokens (30 min) + refresh tokens (7 days)
- **Authorization**: User-scoped data access (users see only their documents)
- **Input Validation**: Pydantic v2 schemas on all inputs
- **File Validation**: Type checking, size limits, filename sanitization
- **Rate Limiting**: Per-IP throttling via SlowAPI
- **CORS**: Whitelisted origins only
- **Prompt Injection Prevention**: Delimited contexts, input validation, system-level instructions to ignore adversarial content
