"""
CLI tool to seed the Knowledge Base with standard reference clauses.

Usage:
    python -m cli.seed_data
"""

import asyncio
from pathlib import Path

from app.core.database import async_session_factory
from app.services.knowledge_base_service import KnowledgeBaseService


async def seed_data():
    """Seed the database with JSON files from the knowledge_base directory."""
    project_root = Path(__file__).parent.parent
    kb_dir = project_root / "knowledge_base" / "standard_clauses"
    
    if not kb_dir.exists():
        print(f"Error: Knowledge base directory not found at {kb_dir}")
        return

    json_files = list(kb_dir.glob("*.json"))
    if not json_files:
        print(f"No JSON files found in {kb_dir}")
        return

    print(f"Found {len(json_files)} seed files. Starting ingestion...")

    class MockUploadFile:
        def __init__(self, filename, content):
            self.filename = filename
            self._content = content
            
        async def read(self):
            return self._content

    async with async_session_factory() as session:
        service = KnowledgeBaseService(session)
        
        for file_path in json_files:
            print(f"Processing {file_path.name}...")
            
            with open(file_path, "rb") as f:
                content = f.read()
                
            upload_file = MockUploadFile(file_path.name, content)
            
            # Derive title and doc type from filename
            doc_type = file_path.stem
            title = doc_type.replace("_", " ").title()
            
            try:
                # First check if it already exists to avoid duplicates
                existing, _ = await service.get_all_documents(limit=100)
                if any(doc.title == title for doc in existing):
                    print(f"  Skipping {title} (already exists)")
                    continue
                    
                result = await service.ingest_document(
                    file=upload_file, # type: ignore
                    title=title,
                    document_type=doc_type,
                )
                print(f"  Success: {result.message}")
            except Exception as e:
                print(f"  Error processing {file_path.name}: {e}")
                await session.rollback()
                
        print("Seeding complete!")


def main():
    asyncio.run(seed_data())


if __name__ == "__main__":
    main()
