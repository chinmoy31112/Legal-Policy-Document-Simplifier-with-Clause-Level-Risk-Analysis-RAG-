"""
CLI tool to ingest a document into the Knowledge Base.

Usage:
    python -m cli.kb_ingest --file path/to/doc.pdf --title "Example Doc" --type terms_of_service
"""

import argparse
import asyncio
from pathlib import Path

from fastapi import UploadFile

from app.core.database import async_session_factory
from app.services.knowledge_base_service import KnowledgeBaseService


async def ingest_document(file_path: str, title: str, doc_type: str, jurisdiction: str | None = None):
    """Ingest a document into the KB using the service layer."""
    path = Path(file_path)
    if not path.exists():
        print(f"Error: File not found at {path}")
        return

    print(f"Ingesting {path.name} into Knowledge Base...")
    
    # Create a mock UploadFile
    with open(path, "rb") as f:
        file_content = f.read()
        
    # We need a proper UploadFile-like object for the service
    # The service only uses filename and read()
    class MockUploadFile:
        def __init__(self, filename, content):
            self.filename = filename
            self._content = content
            
        async def read(self):
            return self._content

    upload_file = MockUploadFile(path.name, file_content)

    async with async_session_factory() as session:
        service = KnowledgeBaseService(session)
        try:
            result = await service.ingest_document(
                file=upload_file, # type: ignore
                title=title,
                document_type=doc_type,
                jurisdiction=jurisdiction,
            )
            print(f"Success! {result.message}")
        except Exception as e:
            print(f"Error during ingestion: {e}")
            await session.rollback()


def main():
    parser = argparse.ArgumentParser(description="Ingest a document into the Knowledge Base.")
    parser.add_argument("--file", "-f", required=True, help="Path to the document file")
    parser.add_argument("--title", "-t", required=True, help="Title of the document")
    parser.add_argument("--type", "-d", required=True, help="Document type (e.g., terms_of_service, privacy_policy)")
    parser.add_argument("--jurisdiction", "-j", help="Jurisdiction (e.g., US-CA, EU)")

    args = parser.parse_args()
    
    asyncio.run(ingest_document(args.file, args.title, args.type, args.jurisdiction))


if __name__ == "__main__":
    main()
