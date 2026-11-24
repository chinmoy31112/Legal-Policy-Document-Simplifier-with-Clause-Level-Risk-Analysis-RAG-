# High-Level Data Model Sketch & API Surface Outline

## 1. High-Level Data Model Sketch

The data model uses PostgreSQL 16 with the `pgvector` extension. All tables enforce strict foreign key constraints, cascading deletes, and tenant isolation via `user_id`.

```mermaid
erDiagram
    USERS ||--o{ DOCUMENTS : "owns"
    USERS ||--o{ JOBS : "submits"
    DOCUMENTS ||--o{ CLAUSES : "contains"
    DOCUMENTS ||--o{ JOBS : "processed by"
    CLAUSES ||--o| CLAUSE_ANALYSES : "produces"
    CLAUSES ||--o{ CLAUSES : "parent of"
    REFERENCE_CLAUSES ||--o{ CLAUSE_ANALYSES : "retrieved for"

    USERS {
        uuid id PK
        string email UK
        string hashed_password
        string full_name
        boolean is_active
        timestamp created_at
        timestamp updated_at
    }

    DOCUMENTS {
        uuid id PK
        uuid user_id FK "Users.id ON DELETE CASCADE"
        string title
        string original_filename
        string file_path
        int file_size
        string file_hash "SHA-256 for deduplication"
        string mime_type
        int page_count
        string document_type "e.g. Terms, Privacy, NDA, Employment"
        string overall_risk_level "LOW | MEDIUM | HIGH"
        int overall_risk_score "0-100 indicative"
        string status "PENDING | EXTRACTING | SEGMENTING | EMBEDDING | ANALYZING | COMPLETED | FAILED"
        string error_message
        timestamp created_at
        timestamp updated_at
    }

    CLAUSES {
        uuid id PK
        uuid document_id FK "Documents.id ON DELETE CASCADE"
        uuid parent_clause_id FK "Clauses.id ON DELETE SET NULL"
        int clause_order
        string section_number "e.g. 1.2(a)"
        string title
        text raw_text
        int page_number
        jsonb bounding_boxes "[[page, x0, y0, x1, y1], ...]"
        string text_hash "SHA-256"
        timestamp created_at
    }

    REFERENCE_CLAUSES {
        string id PK "e.g. REF-LIAB-001"
        string title
        text text
        string document_type
        string jurisdiction
        string category "e.g. Limitation of Liability, Arbitration, Privacy"
        string version
        string language
        string source "e.g. CUAD, ToS;DR, CommonAccord"
        string license "e.g. CC BY 4.0, CC0"
        text why_standard_or_risky
        vector embedding "vector(768)"
        string embedding_model "gemini-embedding-2"
        int embedding_dim "768"
        timestamp created_at
    }

    CLAUSE_ANALYSES {
        uuid id PK
        uuid clause_id FK "Clauses.id ON DELETE CASCADE UK"
        text simplified_text "Plain English summary"
        string risk_level "LOW | MEDIUM | HIGH"
        int risk_score "0-100 indicative"
        float confidence_score "0.0-1.0 indicative"
        jsonb grounded_reasons "[exact quote or REF-ID]"
        text balanced_rewrite "Balanced neutral alternative"
        jsonb retrieved_references "[{ref_id, similarity, title}]"
        string validation_status "VALID | REPAIRED | FAILED"
        jsonb validation_errors "[]"
        timestamp created_at
    }

    JOBS {
        uuid id PK
        uuid user_id FK "Users.id ON DELETE CASCADE"
        uuid document_id FK "Documents.id ON DELETE CASCADE"
        string job_type "DOCUMENT_ANALYSIS"
        string status "PENDING | RUNNING | COMPLETED | FAILED"
        int progress_percent "0-100"
        string current_step "SEGMENTING | RETRIEVING | REASONING"
        string error_message
        timestamp started_at
        timestamp completed_at
    }
```

### Privacy & Data Isolation Guarantees
1. **Cascade Deletion:** `ON DELETE CASCADE` is enforced from `Users` down through `Documents`, `Clauses`, and `ClauseAnalyses`. Calling `DELETE /api/v1/users/me/data` completely purges all user documents, extracted text, and analyses from the database and storage.
2. **Zero-Text Logging:** All log statements across the pipeline record IDs, execution durations, token counts, and hashes—never raw document or clause text.

---

## 2. API Surface Outline

The REST API is versioned under `/api/v1` and returns standard JSON payloads adhering to OpenAPI 3.1 specifications.

### 2.1 Authentication & Profile (`/api/v1/auth`)
- `POST /api/v1/auth/register` — Create new user account (email, password, full_name).
- `POST /api/v1/auth/login` — Authenticate credentials and return JWT bearer token.
- `GET /api/v1/auth/me` — Return current authenticated user profile.

### 2.2 Document Processing & Analysis (`/api/v1/documents`)
- `POST /api/v1/documents/upload`
  - **Input:** Multipart form upload (`file: PDF`, `document_type: string`).
  - **Response:** `202 Accepted` with `{ "document_id": "...", "job_id": "...", "status": "PENDING" }`.
  - **Validation:** Detects corrupt, empty, encrypted, or scanned (<10 chars/page) PDFs and immediately rejects with `400 Bad Request`.
- `GET /api/v1/documents`
  - **Query:** `page`, `page_size`, `status`, `risk_level`.
  - **Response:** Paginated list of user documents with summary risk stats.
- `GET /api/v1/documents/{document_id}`
  - **Response:** Single document metadata, overall risk score, risk level, clause count, and status.
- `GET /api/v1/documents/{document_id}/clauses`
  - **Response:** Ordered list of segmented clauses, their bounding boxes, plain-English simplifications, risk levels, grounded reasons, and balanced rewrites.
- `GET /api/v1/documents/{document_id}/pdf`
  - **Response:** Streams original PDF binary with strict `Content-Disposition: inline` (authenticated user check enforced).
- `DELETE /api/v1/documents/{document_id}`
  - **Response:** `204 No Content`. Cascades and deletes file from disk and database.

### 2.3 Exports (`/api/v1/documents/{document_id}/export`)
- `GET /api/v1/documents/{document_id}/export/json`
  - **Response:** Downloadable structured JSON containing document metadata, risk score, all clauses, risk ratings, grounded citations, and legal disclaimer.
- `GET /api/v1/documents/{document_id}/export/markdown`
  - **Response:** Downloadable formatted Markdown executive briefing with high-risk callouts, clause summaries, and legal disclaimer.

### 2.4 Asynchronous Jobs (`/api/v1/jobs`)
- `GET /api/v1/jobs/{job_id}`
  - **Response:** Real-time job status (`PENDING`, `RUNNING`, `COMPLETED`, `FAILED`), `progress_percent` (0–100), `current_step`, and error logs if failed.

### 2.5 Knowledge Base (`/api/v1/knowledge-base`)
- `GET /api/v1/knowledge-base/clauses`
  - **Query:** `category`, `document_type`, `search_query`.
  - **Response:** Filterable catalog of curated reference clauses and their standard/risky explanations.
- `GET /api/v1/knowledge-base/clauses/{clause_id}`
  - **Response:** Full reference clause text, metadata, source, and standard benchmark description.

### 2.6 User Privacy & Data Deletion (`/api/v1/users/me`)
- `DELETE /api/v1/users/me/data`
  - **Response:** `200 OK` with `{ "deleted_documents": N, "message": "All user data purged successfully." }`.

### 2.7 Health & Readiness (`/api/v1/health`)
- `GET /api/v1/health` — Liveness probe (HTTP 200 `{ "status": "ok" }`).
- `GET /api/v1/health/ready` — Readiness probe (verifies PostgreSQL connection, `pgvector` extension availability, and Redis connectivity).
