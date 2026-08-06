import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from app.document_processing.extractor import extract_pdf
from app.document_processing.segmenter import DocumentSegmenter

async def check():
    db_url = "postgresql+asyncpg://postgres:chinmoy@localhost:5432/legal_simplifier"
    engine = create_async_engine(db_url)
    try:
        async with engine.connect() as conn:
            doc_id = '5fda3c99-dc62-415c-9a77-23f6b4c3dbf1'
            doc_result = await conn.execute(text("SELECT id, status, file_path, filename FROM documents WHERE id = :doc_id"), {"doc_id": doc_id})
            doc = doc_result.fetchone()
            print(f"Document: {doc}")
            if doc:
                file_path = doc[2]
                print(f"File Path: {file_path}")
                if os.path.exists(file_path):
                    print("File exists! Running extractor...")
                    ext_res = extract_pdf(file_path)
                    print(f"Extraction pages: {ext_res.page_count}")
                    print(f"Is scanned: {ext_res.is_scanned}")
                    print(f"Blocks count: {len(ext_res.blocks)}")
                    print(f"Raw text length: {len(ext_res.raw_text)}")
                    print(f"Errors: {ext_res.errors}")
                    
                    segmenter = DocumentSegmenter()
                    clauses = segmenter.segment(ext_res)
                    print(f"Segments generated: {len(clauses)}")
                else:
                    print("File DOES NOT EXIST!")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        await engine.dispose()

if __name__ == '__main__':
    asyncio.run(check())
