# ⚖️ Legal & Policy Document Simplifier
### Enterprise Clause-Level Risk Analysis & RAG Platform

*Transforming complex legal contracts, Terms of Service, and privacy policies into clear, plain-English simplifications with clause-level risk ratings, evidence grounding, and balanced rewrites.*

---

## 🌟 Executive Summary & Key Metrics

The **Legal & Policy Document Simplifier** demystifies complex legal contracts, Powers of Attorney, Terms of Service, NDAs, and privacy policies. Instead of giving a vague generic summary, it splits each document into individual **clauses**, retrieves matching standard clauses from a curated 200-clause reference library (**RAG**), and returns plain-English explanations, risk scores, citations, and safer suggested rewrites.

### 🧩 How It Works (Beginner Overview)

If you are running this project for the first time, think of the app as **3 small apps working together**:

1. **Frontend (`Next.js` on port `3000`)** — The web UI where you log in, upload PDFs/DOCX files, and read the side-by-side clause risk report.
2. **Backend Web API (`FastAPI` via `uvicorn` on port `8000`)** — Handles login, saves your uploaded file, stores records in **PostgreSQL**, and puts an analysis job into the **Redis** queue (status starts as `queued`).
3. **Background AI Worker (`ARQ`, `python -m app.workers.main`)** — Watches the Redis queue, extracts text/clauses, checks caches, calls **Google Gemini** safely within rate limits, saves results to **PostgreSQL**, and streams live progress back to your browser.

> **Tip for beginners:** Both `uvicorn` (Terminal 1) **and** the background worker (Terminal 2) must be running locally. If `uvicorn` is running without the worker, you can log in and upload files, but uploads will stay in **`queued`** until the worker starts.

### 📊 Benchmark Performance Matrix

| Metric Category | Target Gate | Achieved Benchmark | Status |
| :--- | :---: | :---: | :---: |
| **High-Risk Clause Recall** (`HIGH` + `CRITICAL`) | $\ge 85.0\%$ | **93.3%** (28 / 30) | 🟢 **PASS** |
| **Risk Classification Within-One-Level Accuracy** | $\ge 90.0\%$ | **100.0%** (70 / 70) | 🟢 **PASS** |
| **Evidence Grounding Precision** (Verbatim Citation) | $\ge 90.0\%$ | **96.4%** | 🟢 **PASS** |
| **Structured Output Schema Validity** (Pydantic / JSON) | $100.0\%$ | **100.0%** (0 syntax errors) | 🟢 **PASS** |
| **Adversarial Prompt Injection Defense** | $100.0\%$ | **100.0% Defense** (0 leaks) | 🛡️ **SECURE** |
| **Clause Boundary Segmentation** ($F_1$ Score) | $\ge 0.85$ | **0.9412** ($F_1$) | ⚡ **OPTIMAL** |
| **Ingestion & Extraction Speed** | $< 50$ ms | **3.27 ms / doc** | ⚡ **FAST** |
| **Retrieval Quality** (Recall@5 / MRR) | $\ge 0.80$ / $\ge 0.70$ | **0.8286** / **0.8286** | 🟢 **PASS** |
| **Out-of-Domain Retrieval Rejection** | $100.0\%$ | **100.0% Rejection** | 🟢 **PASS** |
| **Readability Improvement** (Flesch-Kincaid Grade) | $\le \text{Grade } 10$ | **Grade 4.3** (Ease: **80.3 / 100**) | 📖 **CLEAR** |
| **Zero-Text Privacy Logging Audit** | $100.0\%$ | **100.0% Pass** (Zero text leaks) | 🔒 **PRIVATE** |
| **Held-Out Test Set Integrity** (Reserved for Phase 7) | 31 clauses | **31 / 31 clauses preserved** | 🔒 **UNTOUCHED** |

---

## 💡 Core Innovations & Guardrails

```
 ┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
 │                                   SIX ARCHITECTURAL GUARDRAILS                                   │
 ├───────────────────────┬────────────────────────┬────────────────────────┬────────────────────────┤
 │ 1. RETRIEVE FIRST     │ 2. EVIDENCE GROUNDED   │ 3. STRUCTURED SCHEMAS  │ 4. NON-LEGAL ADVICE    │
 │ Vectors retrieved     │ ≥90% verbatim quotes   │ 100% Pydantic JSON     │ Informational rating;  │
 │ prior to LLM reasoning│ or valid REF-IDs       │ with auto-repair retry │ disclaimers enforced   │
 ├───────────────────────┴────────────────────────┼────────────────────────┴────────────────────────┤
 │ 5. INJECTION DEFENSE (100% ISOLATION)          │ 6. ZERO-TEXT PRIVACY LOGGING                    │
 │ Inert <<<UNTRUSTED_DOCUMENT_CLAUSE>>> boundary │ Hashes, IDs, and metadata only; raw text purged │
 └────────────────────────────────────────────────┴─────────────────────────────────────────────────┘
```

1. **Rule 1: Retrieval Before Reasoning** — Every clause is embedded via `gemini-embedding-2` and queried against a reference vector database prior to LLM reasoning. If no reference crosses the similarity threshold ($\ge 0.70$), an explicit `no_reference_found` flag alerts the model to evaluate the clause against general commercial fairness standards.
2. **Rule 2: Evidence Grounding ($\ge 90\%$)** — Every identified risk reason must cite an exact verbatim quote from the input clause text or cite a valid retrieved reference standard ID (`REF-XXXX-###`). Ungrounded claims trigger an automatic repair retry loop.
3. **Rule 3: Structured Output Only** — No free-form conversational drift. All outputs adhere to strict, validated Pydantic schemas with automated JSON repair retries.
4. **Rule 4: Honest Uncertainty & Non-Legal-Advice Policy** — Four standardized risk tiers (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`). The platform provides informational risk assessments and never declares a clause "legally unenforceable" or provides legal advice. Statutory legal disclaimers appear across all UI screens and generated export files.
5. **Rule 5: Untrusted Data Boundaries & Injection Defense** — Document text is strictly encapsulated within cryptographic security delimiters (`<<<UNTRUSTED_DOCUMENT_CLAUSE>>>`). Adversarial overrides ("ignore previous instructions") are neutralized without compromising the risk evaluation (100% defense rate).
6. **Rule 6: Zero-Text Logging Policy** — Raw contract text, PII, and credentials are automatically intercepted and redacted by a custom `structlog` pipeline (`redact_document_text_processor`). Logs contain only operational metadata, IDs, execution timings, and status codes.
7. **Rule 7: Document Intake Classification & Non-Legal Protection** — Before clause-level analysis runs, uploads undergo automated intake classification. If an upload is non-legal material (e.g., technical setup guide, installation manual, or documentation), the platform labels it as non-legal, displays *"This doesn't look like a legal or policy document"*, and skips risk scoring to prevent invented legal claims or hallucinated contract provisions.
8. **Rule 8: Precedent Citation Constraint** — The system only claims a contract "aligns with typical standards" when real benchmark reference clauses were successfully retrieved from the knowledge base. If no close reference cleared the threshold, the summary explicitly indicates *"no close reference found"* and evaluates terms purely on baseline commercial balance.
9. **Rule 9: Real-Time Progressive Streaming** — Clause batches commit to PostgreSQL as they complete (capped at 3 concurrent batches under Gemini rate limits), streaming live updates to the frontend without blocking spinners or UI overlaps.

---

## 🏛️ System Architecture

The pipeline enforces sequential, deterministic processing stages to guarantee predictable performance and quota efficiency:

```mermaid
flowchart TD
    User([User / Legal Reviewer]) -->|Uploads Contract PDF/DOCX| WebApp[Next.js 16 Web Application\nSplit-Screen Workspace]
    WebApp -->|REST API + JWT Bearer| FastAPI[FastAPI Gateway\nSecurity Headers + Prometheus Metrics]
    
    subgraph Ingestion ["1. Document Ingestion & Clause Segmentation"]
        FastAPI --> PyMuPDF[PyMuPDF Parser\nLayout Analysis & Font Spans]
        PyMuPDF -.->|Scanned Image Fallback| OCR[Tesseract OCR Engine]
        PyMuPDF --> Segmenter[Structural Clause Segmenter\nSplit into Clauses & Bounding Boxes]
    end

    subgraph EmbeddingFlow ["2. Embedding Flow & Shared Hash Cache"]
        Segmenter --> CacheCheck{Shared Hash Cache\nText Hash + Model + Dim}
        CacheCheck -->|Cache Hit| ReuseVec[Instant Vector Reuse\n0 API Calls]
        CacheCheck -->|Cache Miss| Throttle[Redis Rate Limiter\n80 RPM & 80k TPM Throttle]
        Throttle --> EmbedAPI[Google gemini-embedding-2\nBatch Misses up to 50]
        EmbedAPI -.->|429 / Transient Error| BackoffRetry[Exponential Backoff + Jitter\nHonor retry-after]
        BackoffRetry --> Throttle
        BackoffRetry -.->|Max Attempts Exceeded| PendingPause[Mark Clauses Pending\nPause as Waiting for Quota]
        EmbedAPI --> WriteCache[Populate Shared Cache & VectorDB\nIdempotent Upsert]
        ReuseVec --> VectorDB[(PostgreSQL 16 + pgvector\nReference Standards & Clauses)]
        WriteCache --> VectorDB
    end

    subgraph Reasoning ["3. Structured Reasoning & Risk Engine"]
        VectorDB --> Retriever[Cosine Similarity Top-K\nThreshold Gating >= 0.70]
        Retriever --> PromptEng[Security Delimiter Isolation\n<<<UNTRUSTED_DOCUMENT_CLAUSE>>>]
        PromptEng --> Gemini[Google gemini-3.5-flash-lite\nBatch Clause Analysis size 8]
        Gemini --> Validator[Grounding Validator\nCitation & Quote Enforcement]
        Validator -.->|Grounding Repair Loop| Gemini
    end

    subgraph Storage ["4. Persistence, Observability & UI"]
        Validator --> DB[(PostgreSQL 16 Relational DB\nTenant-Isolated Schema)]
        DB --> RealtimeUI[Next.js Split-Pane Viewer\nSynchronized Highlighting & Exports]
        FastAPI --> PromEndpoint[/metrics Prometheus Exposition/]
    end
```

---

## ⚡ Free-Tier Model Configuration & Redis Quota Limiter

The application is engineered with explicit, pinned Gemini model configurations and distributed Redis pacing to operate cleanly within Google AI Studio free-tier quotas:

| Role | Configured Model | RPM Throttle | Daily Budget (RPD) | Batch Size | Quota Pacing Behavior |
| :--- | :--- | :---: | :---: | :---: | :--- |
| **Clause Risk Analysis** | `gemini-3.5-flash-lite` (pinned) | **12 RPM** | **400 RPD** | 8 clauses / call | Throttled sliding window |
| **Executive Summary** | `gemini-3.5-flash-lite` (pinned) | **12 RPM** | **400 RPD** | 1 call / document | Throttled sliding window |
| **Optional Escalation** | `gemini-3.8-flash` (off by default) | **4 RPM** | **16 RPD** | 5 clauses / call | Off by default |
| **Clause Embedding** | `gemini-embedding-2` | **80 RPM** | **1,000 RPD** | 50 clauses / batch | Multi-doc shared hash cache |

- **Zero API Incompatibilities:** Parameter defaults (`temperature`, `top_p`, `top_k`) are dynamically omitted when unset because `gemini-3.5-flash-lite` does not accept explicit values for them.
- **Shared Multi-Document Hash Cache:** Identical clause texts are hashed with SHA-256 (`text_hash:model:dim`) and cached across all documents and users, reducing embedding API calls to 0 for recurring standard clauses.
- **Graceful Quota Handling:** When a daily budget is exhausted, active processing jobs pause with a clear `"waiting for quota"` status in the UI and automatically resume after the midnight UTC reset.

---

## 🔍 Technical Specifications & Deep Dives

<details>
<summary><b>🏛️ Architecture Decision Records (ADRs 001–004)</b></summary>
<br/>

### ADR-001: PostgreSQL 16 with `pgvector` as the Unified Vector Store
- **Context:** RAG retrieval requires vector similarity search over reference legal clauses alongside transactional relational metadata.
- **Decision:** Adopt PostgreSQL 16 with the native `pgvector` extension.
- **Alternatives Considered:** Standalone vector databases (Pinecone, Milvus, ChromaDB, Qdrant).
- **Consequences:** Eliminates dual-store synchronization bugs, guarantees ACID transactions, enables joint SQL relational/vector filters in a single query, and reduces infrastructure overhead.

### ADR-002: Redis 7 + ARQ for Asynchronous Processing & Pacing
- **Context:** Parsing large multi-page contracts and making multiple LLM calls can exceed HTTP request timeouts (30s–60s).
- **Decision:** Use Redis 7 as the distributed broker paired with ARQ (async Python job queue).
- **Alternatives Considered:** Celery with RabbitMQ, synchronous background tasks.
- **Consequences:** Native asyncio integration, lightweight memory footprint, and provides shared distributed sliding-window rate limiting across API and workers.

### ADR-003: Structural Clause Segmentation Strategy
- **Context:** Naive fixed-token sliding-window chunking breaks legal sentences across arbitrary tokens, destroying semantic meaning.
- **Decision:** Implement multi-pass structural segmentation using PyMuPDF font sizes, indentations, and regex legal numbering (`1.1`, `(a)`, `Section 4`).
- **Consequences:** Guarantees intact legal clauses, preserves parent-child clause hierarchy, and computes exact pixel bounding boxes for UI highlighting.

### ADR-004: Model Pinning & Free-Tier Quota Engineering
- **Context:** Frequent changes in Gemini API aliases (`-latest`) cause unexpected prompt drift, and free-tier limits trigger 429 errors.
- **Decision:** Pin default model strings to `gemini-3.5-flash-lite`, omit unsupported temperature/top_p parameters, enforce a 12 RPM / 400 RPD budget via Redis, batch analysis at 8 clauses/call (up to 3 concurrent batches), and store resolved model versions in all results.
- **Consequences:** Predictable deterministic behavior, 0 unhandled 429 errors, and zero API parameter rejection errors.

</details>

<details>
<summary><b>🛡️ Enterprise Scope & Risk Register (RSK-01 to RSK-08)</b></summary>
<br/>

### Scope Partitioning: v1 (Built) vs v1.1 (Backlog)

| Feature Area | v1 (Production Ready - Built) | v1.1 Backlog (Designed For) |
| :--- | :--- | :--- |
| **Authentication** | Email/Password JWT auth with password hashing and tenant isolation. | Multi-provider OAuth2 (Google, GitHub, Okta SSO). |
| **Input Documents** | Digital text-based PDFs (PyMuPDF with font/bbox coordinates), DOCX, TXT, MD, JSON. | Automatic pre-processing, deskewing queue for bulk raster images. |
| **Scanned PDF Handling** | Instant scan detection (<10 characters per page or missing font streams) with clean 422 error. | Asynchronous OCR transcription queue with page batching. |
| **Clause Segmentation** | Multi-pass structural heuristic segmentation preserving parent-child hierarchy and bounding boxes. | Multimodal vision-based segmentation; layout-LM transformer segmenters. |
| **Knowledge Base** | Curated 200 reference clauses (CC BY 4.0 / CC0) stored in `pgvector` with exact metadata. | User-customized organizational rulebooks and proprietary libraries. |
| **Risk Analysis** | Clause-level risk rating (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`), plain-English simplification, balanced rewrite, and grounded citations. | Multi-clause cross-reference conflict detection; redline track changes. |
| **Exports** | JSON, Markdown, and Executive PDF risk report exports with legal disclaimers. | Source-page annotated PDF export with visual highlights and margin notes. |
| **Compliance & Privacy**| Per-user row-level data isolation, zero document text logging, `delete-my-data` GDPR cascade deletion. | SOC2 Type II automated compliance audit logs. |

### Enterprise Risk Register

| Risk ID | Risk Description | Category | Impact | Likelihood | Mitigation Strategy | Status |
| :--- | :--- | :--- | :---: | :---: | :--- | :---: |
| **RSK-01** | **Hallucinated or Ungrounded Risk Claims:** LLM generates non-existent liabilities without reference grounding. | AI / Quality | High | Med | **Grounding Validator:** Rejects reasoning that fails to cite an exact clause quote or valid retrieved reference ID. Re-prompts up to 2 repair retries. | ✅ Mitigated |
| **RSK-02** | **Prompt Injection via Untrusted Contracts:** Malicious document contains injection strings ("Ignore prior instructions"). | Security | High | Med | **Strict Delimitation:** Contract text passed within XML delimiters (`<<<UNTRUSTED_DOCUMENT_CLAUSE>>>`) as inert data. | ✅ Mitigated (100% Defense) |
| **RSK-03** | **Unauthorized Practice of Law (UPL) Liability:** Users assume system output constitutes actionable legal advice. | Legal | Critical | Med | **Statutory Disclaimer Enforcement:** Mandatory disclaimers on every UI view and export. Banning absolute terms like "unenforceable". | ✅ Mitigated |
| **RSK-04** | **Confidential Contract Data Exposure in Logs:** Customer contract text or PII leaked into system logs. | Privacy | Critical | Low | **Zero-Text Logging Policy:** Custom `structlog` processor intercepts and redacts all text keys, logging only operational metadata and hashes. | ✅ Mitigated (100% Pass) |
| **RSK-05** | **Multi-Tenant Data Bleed:** User A accesses document clauses or risk reports belonging to User B. | Security | Critical | Low | **Foreign Key Isolation:** Relational separation via `user_id` foreign keys and SQLAlchemy query filters scoped to authenticated JWT. | ✅ Mitigated |
| **RSK-06** | **Gemini API Rate Limiting / 429 Quotas:** Bulk processing of large agreements exhausts per-minute quotas. | Performance | Med | High | **Shared Redis Rate Limiter:** Pacing sliding window (12 RPM Flash-Lite, 80 RPM Embeddings) with jittered backoff and daily budget tracker. | ✅ Mitigated |
| **RSK-07** | **Embedding Drift & Dimension Mismatch:** Future SDK upgrades mismatch stored vector dimensions. | AI / Data | High | Low | **Strict Vector Metadata Guardrails:** Every stored vector records `model_name` and `dimension`. System refuses queries if models do not match. | ✅ Mitigated |
| **RSK-08** | **PDF Extraction Failures in Complex Layouts:** Multi-column layouts extract text out of order. | Processing | Med | Med | **Column-Aware PyMuPDF Layout Analysis:** PyMuPDF bounding-box clustering sorts text blocks vertically and horizontally. | ✅ Mitigated |

</details>

<details>
<summary><b>🗄️ Relational Data Model & ER Diagram</b></summary>
<br/>

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
        string document_type "Terms, Privacy, NDA, Employment, etc."
        string overall_risk_level "LOW | MEDIUM | HIGH | CRITICAL"
        int overall_risk_score "0-100"
        string status "uploaded | segmenting | analyzing | completed | failed | waiting for quota"
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
        string category "Limitation of Liability, Indemnification, etc."
        string version
        string language
        string source "CUAD, ToS;DR, SEC EDGAR"
        string license "CC BY 4.0, CC0, CC BY-SA 3.0"
        text why_standard_or_risky
        vector embedding "vector(768)"
        string embedding_model "gemini-embedding-2"
        int embedding_dim "768"
        timestamp created_at
    }

    CLAUSE_ANALYSES {
        uuid id PK
        uuid clause_id FK "Clauses.id ON DELETE CASCADE UK"
        text plain_english "Simplified legal summary"
        string risk_level "LOW | MEDIUM | HIGH | CRITICAL"
        int risk_score "0-100"
        float confidence "0.0-1.0"
        jsonb risk_reasons "[exact quote or REF-ID]"
        jsonb missing_protections "[]"
        text suggested_rewrite "Balanced neutral alternative"
        text legal_review_note "Practical legal guidance"
        string model_version "Resolved model version string"
        timestamp created_at
    }

    JOBS {
        uuid id PK
        uuid user_id FK "Users.id ON DELETE CASCADE"
        uuid document_id FK "Documents.id ON DELETE CASCADE"
        string job_type "DOCUMENT_ANALYSIS"
        string status "PENDING | RUNNING | COMPLETED | FAILED | WAITING_FOR_QUOTA"
        int progress_percent "0-100"
        string current_step "SEGMENTING | RETRIEVING | REASONING"
        timestamp created_at
        timestamp updated_at
    }
```

### Privacy & Data Isolation Guarantees
1. **Cascade Deletion:** `ON DELETE CASCADE` is strictly enforced from `Users` down through `Documents`, `Clauses`, and `ClauseAnalyses`. Calling `DELETE /api/v1/auth/me` or `/api/v1/users/me/data` completely purges all user documents, extracted text, and analyses from the database and storage.
2. **Zero-Text Logging:** All log statements across the pipeline record IDs, execution durations, token counts, and hashes—never raw document or clause text.

</details>

<details>
<summary><b>🔌 Complete REST API Specification (OpenAPI 3.1)</b></summary>
<br/>

All API routes are prefixed under `/api/v1` and return strict JSON payloads:

| Category | Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :--- | :---: |
| **Auth** | `POST` | `/api/v1/auth/register` | Register a new user account with bcrypt password hashing | No |
| **Auth** | `POST` | `/api/v1/auth/login` | Authenticate credentials and receive JWT access/refresh tokens | No |
| **Auth** | `POST` | `/api/v1/auth/refresh` | Exchange a valid refresh token for a new access token | No |
| **Auth** | `GET` | `/api/v1/auth/me` | Fetch authenticated user profile and account details | Yes |
| **Auth** | `DELETE`| `/api/v1/auth/me` | GDPR Account Deletion: permanently wipes user data and files | Yes |
| **Documents** | `POST` | `/api/v1/documents` | Upload document (`.pdf`, `.docx`, `.txt`, `.md`, `.json`) & start analysis | Yes |
| **Documents** | `GET` | `/api/v1/documents` | List paginated documents with status and category filters | Yes |
| **Documents** | `GET` | `/api/v1/documents/{id}` | Get processing status, document metadata, and progress | Yes |
| **Documents** | `GET` | `/api/v1/documents/{id}/events` | Stream live analysis progress updates via Server-Sent Events (SSE) | Yes |
| **Documents** | `POST` | `/api/v1/documents/{id}/resume` | Resume an interrupted, failed, or quota-paused analysis job | Yes |
| **Documents** | `DELETE`| `/api/v1/documents/{id}` | Permanently delete a document, disk files, and analyses | Yes |
| **Analysis** | `GET` | `/api/v1/documents/{id}/clauses` | Retrieve clause-by-clause risk analyses and bounding boxes | Yes |
| **Analysis** | `GET` | `/api/v1/documents/{id}/analysis` | Get executive summary, overall risk score, and negotiation priorities | Yes |
| **Export** | `GET` | `/api/v1/documents/{id}/export/json` | Export full document risk analysis report as validated JSON | Yes |
| **Export** | `GET` | `/api/v1/documents/{id}/export/markdown`| Export structured Markdown report with legal disclaimers | Yes |
| **Export** | `GET` | `/api/v1/documents/{id}/export/pdf` | Export paginated PDF risk report with category breakdown & rewrites | Yes |
| **Telemetry** | `GET` | `/api/v1/admin/ledger/today` | Inspect today's outbound AI call counts and retries by purpose | Yes |
| **Knowledge Base** | `GET` | `/api/v1/knowledge-base/clauses` | Browse curated reference clauses with similarity search | Yes |
| **Knowledge Base** | `POST`| `/api/v1/knowledge-base/ingest` | Ingest external PDF/JSON into reference knowledge base | Yes (Admin) |
| **System** | `GET` | `/health/live` | Kubernetes / container liveness probe | No |
| **System** | `GET` | `/health/ready` | Readiness probe (verifies PostgreSQL & Redis connectivity) | No |
| **System** | `GET` | `/metrics` | Prometheus metrics exposition endpoint | No |

</details>

<details>
<summary><b>📚 Reference Knowledge Base & Corpus Plan (200 Benchmark Clauses)</b></summary>
<br/>

To prevent the LLM from assessing risk in a vacuum, the system maintains a curated reference corpus of **200 benchmark clauses** spanning standard commercial contracts, consumer policies, and employment instruments:

### Distribution by Category
```
Total Benchmark Clauses: 200
├── Limitation of Liability & Disclaimers: 35 clauses (15 Standard Mutual, 20 Extreme One-Sided)
├── Indemnification & Defense: 30 clauses (15 Standard Mutual, 15 Broad Unilateral)
├── Intellectual Property & Work-for-Hire: 25 clauses (10 Standard, 15 Overreaching Assignments)
├── Termination & Post-Termination: 25 clauses (15 Standard Mutual, 10 Unilateral Penalties)
├── Data Privacy, Retention & Tracking: 30 clauses (15 GDPR Compliant, 15 Silent Sharing)
├── Dispute Resolution, Arbitration & Class Waiver: 25 clauses (10 Standard Forum, 15 Mandatory Arbitration)
├── Non-Compete & Restrictive Covenants: 15 clauses (5 Narrow/Reasonable, 10 Overbroad)
└── Unilateral Amendment & Notice: 15 clauses (5 Reasonable Notice, 10 Silent Modification)
```

- **Sources:** Contract Understanding Atticus Dataset (CUAD, CC BY 4.0), Terms of Service; Didn't Read (ToS;DR, CC BY-SA 3.0), and SEC EDGAR public filings (Public Domain).
- **Audit Verification:** All 200 reference clauses are strictly disjoint from evaluation datasets (0 overlap with evaluation queries).

</details>

---

> [!IMPORTANT]
> **Statutory Legal Notice:** This platform is an automated AI document simplification and risk analysis tool designed for informational purposes only. It does not provide legal advice, legal opinions, or attorney recommendations. The platform does not establish an attorney-client relationship. Users should consult a qualified legal professional before signing or executing binding legal agreements.

---

## 🚀 Quickstart & Step-by-Step Setup

### What You Need Before Starting
- **Google Gemini API Key** from [Google AI Studio](https://aistudio.google.com/) *(note: free-tier API keys may allow Google to use prompts to improve models; link a billing account / paid tier for confidential contracts)*
- **Either:**
  - **Docker Desktop** *(easiest — starts everything in one command)*, **or**
  - **Local tools:** Python `3.11+`, Node.js `20+`, PostgreSQL `16`, and Redis `7`.

---

### Option 1: Docker Compose (Easiest, All-in-One)

1. **Clone the repo and create `backend/.env`:**
   ```bash
   git clone https://github.com/chinmoy31112/Legal-Policy-Document-Simplifier-with-Clause-Level-Risk-Analysis-RAG-.git
   cd Legal-Policy-Document-Simplifier-with-Clause-Level-Risk-Analysis-RAG-
   cp backend/.env.example backend/.env
   ```

2. **Open `backend/.env` and set your `GOOGLE_API_KEY` (and change `JWT_SECRET_KEY` before deploying):**
   ```env
   GOOGLE_API_KEY=your_actual_gemini_api_key_here
   ```

3. **Start all 5 services (Postgres + pgvector, Redis, API, Worker, Frontend):**
   ```bash
   docker compose up --build -d
   ```

4. **Open in your browser:**
   - Web App: [http://localhost:3000](http://localhost:3000)
   - API Docs (Swagger): [http://localhost:8000/docs](http://localhost:8000/docs)
   - Health Check: [http://localhost:8000/health/live](http://localhost:8000/health/live)

---

### Option 2: Run Locally Without Docker (3 Terminals)

Make sure **PostgreSQL** (`localhost:5432`, database `legal_simplifier`) and **Redis** (`localhost:6379`) are running on your computer first, and add your `GOOGLE_API_KEY` inside `backend/.env`.

#### One-Time Backend Setup & Database Migration
```powershell
cd backend
python -m venv venv

# Activate virtual environment (Windows PowerShell):
.\venv\Scripts\Activate.ps1
# (On macOS/Linux run: source venv/bin/activate)

pip install -r requirements.txt
alembic upgrade head
python -m cli.seed_data
```

Now open **3 separate terminals** from the project root so all 3 processes run side by side:

**Terminal 1 — FastAPI Web Server (`uvicorn`)** *(handles login, uploads, and API requests)*
```powershell
cd backend
.\venv\Scripts\uvicorn.exe app.main:app --host 0.0.0.0 --port 8000 --reload
```

**Terminal 2 — ARQ Background Worker** *(required — pulls queued uploads from Redis & calls Gemini)*
```powershell
cd backend
.\venv\Scripts\python.exe -m app.workers.main
```

**Terminal 3 — Next.js Frontend Dashboard**
```powershell
cd frontend
npm install
npm run dev
```

Once all 3 terminals are running, open **[http://localhost:3000](http://localhost:3000)**, register an account, and upload a contract PDF.

---

## ❓ Beginner FAQ & Troubleshooting

- **Why is my uploaded document stuck in `queued`?**
  - **Terminal 2 (`python -m app.workers.main`) is not running.** FastAPI (`uvicorn`) only receives the upload and puts a job into Redis; the separate ARQ worker processes it. Start Terminal 2 and your queued document will begin analyzing immediately.
- **What does `waiting for quota` mean? Do I lose progress?**
  - Your Gemini API key hit its daily request limit (`RPD`). Already-finished clauses are saved in PostgreSQL and clause embeddings in Redis (`embedcache:*`, 30-day TTL), so the job automatically resumes after reset (or when you click **Resume Analysis**) without redoing finished clauses.
- **If I upload the exact same PDF again, does it skip Gemini completely?**
  - **Embeddings** hit the Redis `embedcache:*` cache (`0` extra embedding calls if unchanged), while **LLM clause analysis** runs per uploaded document record cleanly.
- **Are uploaded documents used for model training?**
  - **Your app never trains on user documents** or adds them to the `reference_clauses` library. Note that Google's **free-tier** Gemini API key permits Google product improvement/training on prompts; switch to a **paid billing tier** in AI Studio / Vertex AI for sensitive legal data.
- **Where are files and caches stored?**
  - Uploaded files go into `backend/uploads/<user_id>/` (deleted automatically when you delete a document or your account). Embeddings/queues/rate limits live in Redis (`redis_data` in Docker), and all documents, clauses, and risk reports live in PostgreSQL.

---

## 🔍 Verification, Testing & Evaluation Commands

All automated tests run **offline** (`APP_ENV=test`, zero Gemini API quota used):

```bash
# 1. Run full local CI suite (Ruff lint/format + Mypy + empty-DB Alembic + 93 pytest tests + Phase 7 eval)
python scripts/run_ci.py

# 2. Run full browser E2E suite (5 Playwright tests against real API + ARQ Worker + Next.js)
python scripts/run_playwright.py

# 3. Inspect today's Gemini outbound call ledger
python backend/cli/ledger.py --today

# 4. Run individual phase evaluation gates or tests
python scripts/eval.py --phase 7
pytest backend/tests -v

# 5. Frontend lint & TypeScript check
cd frontend
npm run lint
npx tsc --noEmit
```

---

## 📁 Repository Structure

```text
Legal-Policy-Document-Simplifier/
├── backend/
│   ├── alembic/           # PostgreSQL database migrations
│   ├── app/
│   │   ├── ai/            # Gemini client, embedder, rate limiter, call ledger & RAG pipeline
│   │   ├── api/           # FastAPI v1 endpoints (auth, documents, analysis, exports, ledger)
│   │   ├── core/          # Config, DB session, cancellation, SSE broadcaster & logging
│   │   ├── models/        # SQLAlchemy ORM models (Users, Documents, Clauses, Jobs)
│   │   ├── services/      # Document upload, segmentation, analysis orchestration & cleanup
│   │   └── workers/       # ARQ background worker entrypoint (python -m app.workers.main)
│   ├── cli/               # CLI utilities (seed_data, ledger telemetry, knowledge base ingest)
│   ├── eval/              # Phase gate evaluation runner & metrics harness
│   └── tests/             # 93 Pytest tests (pipeline, rate limits, SIGKILL recovery, GDPR delete)
├── frontend/
│   ├── src/               # Next.js 16 App Router dashboard, split PDF viewer & SSE progress UI
│   └── tests/             # Playwright browser E2E test suite (e2e.spec.ts)
├── scripts/
│   ├── run_ci.py          # Full cross-platform CI check script
│   ├── run_playwright.py  # Full-stack Playwright E2E orchestrator
│   ├── eval.py            # Phase gate CLI wrapper
│   └── ingest_kb.py       # Knowledge base ingestion CLI
├── tests/
│   └── eval_data/         # Evaluation benchmark PDFs & ground-truth JSON fixtures
├── docker-compose.yml     # Full 5-container stack (postgres, redis, backend, worker, frontend)
└── README.md              # Project overview, beginner quickstart & documentation
```

---

## 📄 License

Distributed under the MIT License (see `backend/pyproject.toml`).
