# Developer Guide

This guide is for developers looking to extend or modify the application.

## Local Development (Without Docker)

If you prefer to run the services locally on your machine for easier debugging:

### 1. Database
Ensure you have PostgreSQL installed and running on port 5432.
Create a database named `legal_simplifier`.

### 2. Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies (requires Tesseract OCR installed on your system for OCR fallback)
pip install -r requirements.txt

# Run migrations
alembic upgrade head

# Run server
uvicorn app.main:app --reload
```

### 3. Frontend
```bash
cd frontend
npm install
npm run dev
```

## Adding a New Document Type

If you want the AI to recognize a new document type (e.g., "NDA"):
1. **Frontend**: Add "NDA" to the `DocumentType` enum in `src/types/document.ts` and the `<select>` in `upload/page.tsx`.
2. **Backend**: 
   - Add it to the `DocumentType` enum in `app/schemas/document.py`.
   - Provide a set of standard reference clauses for NDAs and ingest them using the CLI:
     ```bash
     python -m cli.kb_ingest --source path/to/nda_standards.json --type nda
     ```

## AI Pipeline Adjustments

The core prompt templates are located in `backend/app/ai/prompts/`.
- `clause_analysis.py`: Modify how the LLM evaluates risk severity or extracts missing protections.
- `document_summary.py`: Modify how the LLM aggregates the individual clauses.

If you change the expected JSON output structure in the prompt, you MUST also update the corresponding Pydantic schemas in `backend/app/ai/response_parser.py` so the validation doesn't fail.
