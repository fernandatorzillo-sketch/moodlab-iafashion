import asyncio
from sqlalchemy import text
from services.closet_db import AsyncSessionLocal

async def run():
    async with AsyncSessionLocal() as session:
        await session.execute(text("""
            ALTER TABLE orders
            ALTER COLUMN raw_json TYPE TEXT;
        """))
        await session.commit()
        print("✅ Coluna raw_json alterada para TEXT com sucesso!")

if __name__ == "__main__":
    asyncio.run(run())