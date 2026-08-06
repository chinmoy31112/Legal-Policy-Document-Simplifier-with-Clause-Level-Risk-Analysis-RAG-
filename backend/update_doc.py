import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

async def check():
    db_url = "postgresql+asyncpg://postgres:chinmoy@localhost:5432/legal_simplifier"
    engine = create_async_engine(db_url)
    try:
        async with engine.connect() as conn:
            doc_id = '5fda3c99-dc62-415c-9a77-23f6b4c3dbf1'
            await conn.execute(text("UPDATE documents SET status = 'failed' WHERE id = :doc_id"), {"doc_id": doc_id})
            await conn.commit()
            print("Successfully updated document status to 'failed'")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        await engine.dispose()

if __name__ == '__main__':
    asyncio.run(check())
