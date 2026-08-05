# Legal & Policy Document Simplifier with Clause-Level Risk Analysis (RAG)

An enterprise-grade, full-stack application that leverages Retrieval-Augmented Generation (RAG) and Google's Gemini models to automatically extract, segment, and analyze legal documents (Terms of Service, Privacy Policies, Rental Agreements, etc.) for risks and missing protections.

## Core Features

- **Document Ingestion**: Upload PDF, DOCX, or TXT documents.
- **Smart Extraction**: Intelligent clause segmentation using PyMuPDF and Regex, with a Tesseract OCR fallback for scanned PDFs.
- **RAG Pipeline**: Clauses are embedded using `gemini-embedding-2` and matched against a standard ChromaDB knowledge base to detect deviations from the norm.
- **AI Risk Analysis**: Evaluates clauses using `gemini-2.5-flash` to assign risk scores, highlight "one-sided" language, suggest fair rewrites, and explain legalese in plain English.
- **Interactive Dashboard**: A Next.js split-pane UI where clicking an AI risk finding automatically scrolls to and highlights the corresponding text in the document viewer.

## Architecture Stack

- **Frontend**: Next.js 15, React 19, Tailwind CSS v4, React Query, shadcn/ui.
- **Backend**: FastAPI, SQLAlchemy (Async), Pydantic v2.
- **Database**: PostgreSQL (relational structured data).
- **Vector Store**: ChromaDB (embedded mode).
- **AI/ML**: Google GenAI SDK (`gemini-embedding-2`, `gemini-2.5-flash`).

## Quickstart

### Prerequisites
- Docker and Docker Compose
- A Google AI Studio API Key (`GOOGLE_API_KEY`)

### Setup

1. **Clone the repository**
   ```bash
   git clone <repo-url>
   cd Legal-Policy-Document-Simplifier-with-Clause-Level-Risk-Analysis-RAG-
   ```

2. **Configure Environment Variables**
   ```bash
   cp backend/.env.example backend/.env
   # Edit backend/.env and add your GOOGLE_API_KEY
   ```

3. **Start the Application**
   ```bash
   docker-compose up --build
   ```

4. **Initialize the Database & Knowledge Base**
   In a separate terminal, seed the ChromaDB standard reference clauses:
   ```bash
   # Enter the backend container
   docker exec -it legal_simplifier_backend bash
   
   # Run Alembic migrations
   alembic upgrade head
   
   # Ingest seed data
   python -m cli.seed_data
   ```

5. **Access the App**
   - Frontend Dashboard: `http://localhost:3000`
   - Backend API Docs (Swagger): `http://localhost:8000/docs`

## Documentation

Comprehensive documentation is available in the `docs/` directory:
- [Architecture](docs/architecture.md)
- [API Reference](docs/api-reference.md)
- [Deployment Guide](docs/deployment.md)
- [Developer Guide](docs/developer-guide.md)
