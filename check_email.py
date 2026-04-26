import asyncio
from services.closet_db import AsyncSessionLocal, init_closet_db
from sqlalchemy import text

async def check():
    await init_closet_db()
    async with AsyncSessionLocal() as s:
        # Busca e-mails parecidos com torzillo
        r = await s.execute(text(
            "SELECT DISTINCT email FROM order_items "
            "WHERE email ILIKE '%torzillo%' LIMIT 10"
        ))
        rows = r.fetchall()
        if rows:
            print("E-mails encontrados:")
            for row in rows:
                print(" ->", row[0])
        else:
            print("Nenhum e-mail com 'torzillo' encontrado.")
            
        # Mostra total de registros no banco
        total = await s.execute(text("SELECT COUNT(*) FROM order_items"))
        print(f"\nTotal de itens no banco: {total.scalar()}")

asyncio.run(check())