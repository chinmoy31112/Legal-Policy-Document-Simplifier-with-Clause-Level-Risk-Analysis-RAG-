# Legal & Policy Document Simplifier with Clause-Level Risk Analysis (RAG)

A production-ready legal tech platform that automatically extracts, segments, benchmarks, and evaluates contracts and policy documents. Using Retrieval-Augmented Generation (RAG) powered by Google Gemini and ChromaDB, the system performs clause-by-clause risk analysis, flags predatory terms, detects missing consumer protections, and provides balanced rewrites.

---

## System Architecture

```
                       +-----------------------------------+
                       |       Next.js 15 Web App          |
                       |  React 19, TypeScript, Tailwind   |
                       |     (Split-Screen Workspace)      |
                       +-----------------+-----------------+
                                         |
                                         | REST API / JWT
                                         v
+---------------------------------------------------------------------------------+
|                               FastAPI Backend                                   |
|                                                                                 |
|  +--------------------+     +---------------------+     +--------------------+  |
|  | Document Ingestion | --> | Clause Segmentation | --> |    RAG Pipeline    |  |
|  | PyMuPDF / OCR      |     | Regex + Heuristics  |     |  ChromaDB HNSW     |  |
|  +--------------------+     +---------------------+     +---------+----------+  |
|                                                                   |             |
|                                                                   v             |
|  +--------------------+     +---------------------+     +---------+----------+  |
|  | Background Tasks   | <-- | Structured Output   | <-- |   Gemini 2.5 Flash |  |
|  | Per-Clause Commits |     | Pydantic Validation |     |   Reasoning Engine |  |
|  +--------------------+     +---------------------+     +--------------------+  |
+-------------------+-----------------------------------------------+-------------+
                    |                                               |
                    v                                               v
        +-----------+-----------+                       +-----------+-----------+
        |   PostgreSQL 16 DB    |                       |   ChromaDB Vector DB  |
        | Relational & Metadata |                       | Cosine Embeddings     |
        +-----------------------+                       +-----------------------+
```

### Analysis Pipeline
1. **Multi-Format Extraction**: Ingests PDF, DOCX, TXT, Markdown, and JSON. PDFs are processed via PyMuPDF with font-span analysis to detect headers; image-only scanned pages automatically trigger Tesseract OCR fallback at 300 DPI.
2. **Clause Segmentation**: Text blocks are parsed into discrete legal clauses based on structural numbering patterns (`Article`, `Section`, `1.1.1`, Roman numerals) and heading bounds, rather than arbitrary token chunking.
3. **Semantic Retrieval (RAG)**: Each extracted clause is embedded via `gemini-embedding-2` (`RETRIEVAL_QUERY`) and matched against a ChromaDB vector store of standard, fair reference contracts using cosine similarity ($K=5$).
4. **Structured Reasoning**: The target clause, retrieved reference clauses, and document context are fed into `gemini-2.5-flash` with strict Pydantic JSON schema constraints (`response_schema`).
5. **Real-Time Delivery**: As each clause is evaluated, the backend commits its risk score, explanation, missing protections, and suggested rewrite to PostgreSQL. The frontend polls these records to stream results to the user interface.

---

## Tech Stack

| Component | Technology | Role |
| :--- | :--- | :--- |
| **Backend Framework** | FastAPI (Python 3.11+) | Async REST API, background worker orchestration |
| **Database ORM** | SQLAlchemy 2.0 + asyncpg | Asynchronous PostgreSQL driver and connection pooling |
| **Database Migration**| Alembic | Version-controlled schema migrations |
| **Vector Store** | ChromaDB | Persistent embedded vector index with HNSW cosine metric |
| **Embedding Model** | Google `gemini-embedding-2` | 768-dimensional semantic embeddings |
| **Reasoning LLM** | Google `gemini-2.5-flash` | Structured JSON risk assessment and clause rewriting |
| **Document Processing**| PyMuPDF, python-docx, pytesseract | Text extraction, layout analysis, and OCR fallback |
| **Frontend Framework**| Next.js 15 (App Router) + React 19 | Client application, server rendering |
| **State & Data Fetching**| TanStack Query v5 (React Query) | Server state management, auto-polling |
| **Styling & UI** | Tailwind CSS v4, Lucide Icons | Responsive dashboard, dark theme |

---

## Risk Scoring Framework

Every clause is evaluated on an objective 0–100 risk scale across 5 standard categories:

| Category | Score Range | Description |
| :--- | :---: | :--- |
| **Standard** | 0 – 20 | Balanced boilerplate clause following standard industry norms. |
| **Slightly Unusual** | 21 – 40 | Common terms that slightly favor the drafting party. |
| **One-Sided** | 41 – 60 | Significantly limits user rights or imposes disproportionate liability. |
| **High Risk** | 61 – 80 | Severe liability waivers, unilateral modifications, or aggressive data collection. |
| **Potentially Unenforceable** | 81 – 100 | Terms that frequently violate consumer protection laws or public policy. |

---

## Project Structure

```
.
├── docker-compose.yml              # Production multi-container composition
├── backend/
│   ├── app/
│   │   ├── ai/                     # Gemini SDK, ChromaDB retrieval, prompt templates
│   │   │   ├── embedding.py        # Vector embedding generation (gemini-embedding-2)
│   │   │   ├── llm.py              # Schema-constrained Gemini reasoning client
│   │   │   ├── pipeline.py         # End-to-end RAG orchestrator
│   │   │   ├── retrieval.py        # ChromaDB persistent collection interface
│   │   │   └── response_parser.py  # Pydantic schemas for LLM responses
│   │   ├── api/v1/endpoints/       # Versioned API routes (auth, documents, analysis)
│   │   ├── core/                   # Database engine, JWT security, structured logging
│   │   ├── document_processing/    # PyMuPDF parser, OCR fallback, clause segmenter
│   │   ├── models/                 # SQLAlchemy async ORM models (8 tables)
│   │   ├── repositories/           # Repository pattern data access layer
│   │   └── services/               # Business logic and background task handlers
│   ├── alembic/                    # Database schema migration revisions
│   ├── cli/                        # CLI utilities (seed_data, kb_ingest)
│   ├── knowledge_base/             # Baseline reference contracts (JSON format)
│   └── requirements.txt            # Python dependencies
└── frontend/
    ├── src/
    │   ├── app/                    # Next.js App Router (dashboard, upload, analysis)
    │   ├── components/             # Split-screen UI, clause cards, document viewer
    │   ├── hooks/                  # React Query hooks with intelligent polling
    │   ├── lib/                    # Axios API client with token interceptors
    │   └── providers/              # AuthContext and React Query providers
    └── package.json                # Frontend dependencies
```

---

## Getting Started

### Prerequisites
- [Google Gemini API Key](https://aistudio.google.com/app/apikey)
- Either:
  - **Docker Desktop** (recommended), or
  - **Python 3.11+**, **Node.js 20+**, and a running **PostgreSQL 16** instance

---

### Option 1: Running with Docker (Recommended)

1. **Configure Environment**
   Create `backend/.env` from the provided template:
   ```bash
   # Windows PowerShell
   Copy-Item backend/.env.example backend/.env

   # Linux / macOS
   cp backend/.env.example backend/.env
   ```
   Open `backend/.env` and insert your Gemini API key:
   ```env
   GOOGLE_API_KEY=your_actual_gemini_api_key_here
   ```

2. **Build and Start Containers**
   ```bash
   docker compose up --build
   ```
   This spins up PostgreSQL (`5432`), the FastAPI backend (`8000`), and the Next.js frontend (`3000`).

3. **Populate Reference Knowledge Base**
   In a separate terminal, seed the baseline contract standards:
   ```bash
   docker compose exec backend python -m cli.seed_data
   ```

4. **Access the Application**
   - Web App: [http://localhost:3000](http://localhost:3000)
   - Interactive API Docs (Swagger): [http://localhost:8000/docs](http://localhost:8000/docs)

---

### Option 2: Running Locally (Bare Metal)

#### 1. Backend Setup
```bash
cd backend

# Create and activate virtual environment
python -m venv venv
# Windows:
.\venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure backend/.env with your DATABASE_URL and GOOGLE_API_KEY
# Then run migrations:
alembic upgrade head

# Seed the reference knowledge base into ChromaDB and PostgreSQL
python -m cli.seed_data

# Start FastAPI development server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

#### 2. Frontend Setup
```bash
cd frontend

# Install Node dependencies
npm install

# Start Next.js development server
npm run dev
```

---

## API Reference Overview

All API endpoints are versioned under `/api/v1` and return standardized JSON responses.

| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :---: |
| `POST` | `/api/v1/auth/register` | Register a new user account | No |
| `POST` | `/api/v1/auth/login` | Authenticate and obtain JWT access/refresh tokens | No |
| `POST` | `/api/v1/auth/refresh` | Exchange a refresh token for a new access token | No |
| `GET` | `/api/v1/auth/me` | Fetch authenticated user profile | Yes |
| `POST` | `/api/v1/documents/upload` | Upload document and dispatch background analysis | Yes |
| `GET` | `/api/v1/documents/` | List paginated documents with status filters | Yes |
| `GET` | `/api/v1/documents/{id}` | Retrieve document processing status and metadata | Yes |
| `DELETE`| `/api/v1/documents/{id}` | Delete document, disk files, and related analysis | Yes |
| `GET` | `/api/v1/analysis/{id}/summary` | Retrieve overall document risk score and recommendations | Yes |
| `GET` | `/api/v1/analysis/{id}/clauses` | Retrieve clause-by-clause risk analysis and rewrites | Yes |
| `GET` | `/api/v1/knowledge-base/` | List reference benchmark documents in knowledge base | Yes |
| `POST` | `/api/v1/knowledge-base/upload` | Ingest new reference standards into ChromaDB vector store | Yes |

Interactive Swagger documentation is available at `/docs` when the backend is running.

---

## Testing

```bash
cd backend
pytest tests/ -v
```

---

## License

This project is licensed under the MIT License.
