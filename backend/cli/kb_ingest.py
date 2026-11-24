"""
CLI tool to ingest a document into the Knowledge Base.

For full CLI capabilities (index, update, list, stats, delete), see:
    python -m backend.cli.kb --help

Usage:
    python -m backend.cli.kb_ingest --file path/to/doc.pdf --title "Example Doc" --type terms_of_service
"""

import argparse
import asyncio
import sys
from pathlib import Path

# Ensure backend and root are on sys.path
BASE_DIR = Path(__file__).resolve().parent.parent.parent
BACKEND_DIR = BASE_DIR / "backend"
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.services.knowledge_base_service import KnowledgeBaseService


async def ingest_document(
    file_path: str,
    title: str,
    doc_type: str,
    jurisdiction: str | None = None,
    dry_run: bool = False,
):
    """Ingest a document into the KB using the service layer."""
    path = Path(file_path)
    if not path.exists():
        print(f"Error: File not found at {path}")
        return

    print(f"Ingesting {path.name} into Knowledge Base...")
    service = KnowledgeBaseService()
    try:
        result = await service.ingest_file(
            file_path=path,
            title=title,
            document_type=doc_type,
            jurisdiction=jurisdiction,
            dry_run=dry_run,
        )
        print(
            f"Success! Indexed: {result.get('clauses_indexed', 0)}, Skipped: {result.get('clauses_skipped', 0)}"
        )
    except Exception as e:
        print(f"Error during ingestion: {e}")


def main():
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    parser = argparse.ArgumentParser(description="Ingest a document into the Knowledge Base.")
    parser.add_argument("--file", "-f", required=True, help="Path to the document file")
    parser.add_argument("--title", "-t", required=False, help="Title of the document")
    parser.add_argument("--type", "-d", required=False, default="general", help="Document type")
    parser.add_argument("--jurisdiction", "-j", help="Jurisdiction (e.g., US-CA, EU)")
    parser.add_argument("--dry-run", action="store_true", help="Preview without indexing")

    args = parser.parse_args()
    title = args.title or Path(args.file).stem.replace("_", " ").title()

    asyncio.run(ingest_document(args.file, title, args.type, args.jurisdiction, args.dry_run))


if __name__ == "__main__":
    main()
