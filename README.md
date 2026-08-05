# AI Legal & Policy Document Simplifier

> AI-powered legal document analyzer with clause-level risk assessment using Retrieval-Augmented Generation (RAG). Powered by Google Gemini.

## Overview

This application helps users understand complex legal documents by:

1. **Extracting** text from uploaded legal documents (PDF, DOCX, TXT)
2. **Segmenting** documents into logical legal clauses
3. **Simplifying** each clause into plain English
4. **Comparing** clauses against a reference knowledge base using RAG
5. **Detecting** unusual or risky clauses with risk scoring (0-100)
6. **Explaining** why specific clauses are risky
7. **Suggesting** more balanced alternatives
8. **Producing** an overall document risk assessment
9. **Highlighting** risky clauses in an interactive PDF viewer

## Architecture

```
User Upload → PDF Extraction → Clause Segmentation → Embedding (gemini-embedding-2)
    → Vector Search (ChromaDB) → Retrieve Standard Clauses → Gemini LLM Comparison
    → Risk Analysis → Structured JSON Output → Frontend Visualization
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 15, React 19, TypeScript, Tailwind CSS v4, shadcn/ui |
| Backend | Python 3.12+, FastAPI, SQLAlchemy 2.0 (async), Pydantic v2 |
| Database | PostgreSQL 16 |
| Vector DB | ChromaDB (embedded mode) |
| AI/LLM | Google Gemini 2.5 Flash |
| Embeddings | Google gemini-embedding-2 |
| Document Processing | PyMuPDF, pytesseract (OCR) |
| Auth | JWT (access + refresh tokens) |

## Quick Start

### Prerequisites

- Python 3.12+
- Node.js 20+
- PostgreSQL 16+
- Google AI API Key ([Get one here](https://ai.google.dev/))
- Tesseract OCR (optional, for scanned PDFs)

### 1. Clone & Setup Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # macOS/Linux

pip install -r requirements.txt
cp .env.example .env
# Edit .env with your Google API key and database URL
```

### 2. Setup Database

```bash
# Start PostgreSQL (via Docker or local install)
docker run -d --name legal_db -e POSTGRES_DB=legal_simplifier -e POSTGRES_PASSWORD=postgres -p 5432:5432 postgres:16-alpine

# Run migrations
alembic upgrade head
```

### 3. Start Backend

```bash
uvicorn app.main:app --reload --port 8000
```

### 4. Setup Frontend

```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

### 5. Docker Compose (Alternative)

```bash
docker-compose up -d
```

## API Documentation

Once the backend is running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI Schema**: http://localhost:8000/api/openapi.json

## Project Structure

```
├── backend/           # FastAPI backend
│   ├── app/
│   │   ├── api/       # REST API endpoints (versioned)
│   │   ├── ai/        # AI pipeline (embeddings, LLM, retrieval)
│   │   ├── core/      # Database, security, logging, exceptions
│   │   ├── models/    # SQLAlchemy ORM models
│   │   ├── schemas/   # Pydantic v2 request/response schemas
│   │   ├── services/  # Business logic layer
│   │   ├── repositories/  # Data access layer
│   │   ├── document_processing/  # PDF extraction, segmentation
│   │   └── tasks/     # Background processing
│   ├── cli/           # CLI commands (KB ingestion, seeding)
│   ├── knowledge_base/  # Reference clause seed data
│   └── tests/         # Unit, integration, API tests
├── frontend/          # Next.js 15 frontend
│   └── src/
│       ├── app/       # App Router pages
│       ├── components/  # React components
│       ├── hooks/     # Custom hooks
│       ├── lib/       # Utilities, API client
│       ├── types/     # TypeScript types
│       └── providers/ # Context providers
├── docs/              # Architecture, API, deployment docs
└── docker-compose.yml
```

## Risk Categories

| Category | Score Range | Color |
|----------|-----------|-------|
| Standard | 0-20 | 🟢 Green |
| Slightly Unusual | 21-40 | 🟡 Yellow |
| One-Sided | 41-60 | 🟠 Orange |
| High Risk | 61-80 | 🔴 Red |
| Potentially Unenforceable | 81-100 | 🔴 Dark Red |

## License

MIT

# Legal-Policy-Document-Simplifier-with-Clause-Level-Risk-Analysis-RAG-
