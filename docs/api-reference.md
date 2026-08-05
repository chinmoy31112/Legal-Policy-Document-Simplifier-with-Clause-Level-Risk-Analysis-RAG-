# API Reference

The backend uses FastAPI, meaning a fully interactive Swagger UI is automatically generated and available at `http://localhost:8000/docs`.

Below is a summary of the core endpoints.

## Authentication
- `POST /api/v1/auth/register`: Register a new user account.
- `POST /api/v1/auth/login`: Authenticate and receive a JWT access token.
- `GET /api/v1/auth/me`: Retrieve the currently authenticated user's profile.

## Documents
- `GET /api/v1/documents/`: List all documents belonging to the user (Paginated).
- `POST /api/v1/documents/upload`: Upload a new document (multipart/form-data). Triggers background analysis.
- `GET /api/v1/documents/{id}`: Get a specific document and its current processing status.
- `DELETE /api/v1/documents/{id}`: Delete a document and cascade delete its vector embeddings and analysis results.

## Analysis
- `GET /api/v1/analysis/{id}/summary`: Retrieve the overall executive summary and risk score for a processed document.
- `GET /api/v1/analysis/{id}/clauses`: Retrieve the detailed risk analysis for every single clause in the document.

## Knowledge Base (Admin)
- `POST /api/v1/knowledge-base/ingest`: Upload standard/reference documents to add to the ChromaDB vector index.
