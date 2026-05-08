"""
sync_closet_from_orders.py — popula customer_closet_items a partir de order_items.
Idempotente: pode rodar multiplas vezes sem duplicar.
Uso:
  python3 sync_closet_from_orders.py
  python3 sync_closet_from_orders.py --email seu@email.com
"""
import asyncio, os, sys, time
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

def get_db_url():
    url = os.getenv("DATABASE_URL","").strip()
    if not url: raise RuntimeError("DATABASE_URL nao definida")
    if url.startswith("postgresql://") and "+asyncpg" not in url:
        url = url.replace("postgresql://","postgresql+asyncpg://",1)
    if url.startswith("postgres://"):
        url = url.replace("postgres://","postgresql+asyncpg://",1)
    return url

UPSERT = text("""
INSERT INTO customer_closet_items (
    email,sku_id,product_id,ref_id,name,category,department,brand,
    image_url,product_url,purchase_count,total_quantity,total_spent,
    first_purchase_at,last_purchase_at,created_at,updated_at
) VALUES (
    :email,:sku_id,:product_id,:ref_id,:name,:category,:department,:brand,
    :image_url,:product_url,:purchase_count,:total_quantity,:total_spent,
    :first_purchase_at,:last_purchase_at,NOW(),NOW()
)
ON CONFLICT (email,sku_id) DO UPDATE SET
    name=EXCLUDED.name, category=EXCLUDED.category, department=EXCLUDED.department,
    brand=EXCLUDED.brand,
    image_url=COALESCE(EXCLUDED.image_url, customer_closet_items.image_url),
    product_url=COALESCE(EXCLUDED.product_url, customer_closet_items.product_url),
    purchase_count=EXCLUDED.purchase_count, total_quantity=EXCLUDED.total_quantity,
    total_spent=EXCLUDED.total_spent, first_purchase_at=EXCLUDED.first_purchase_at,
    last_purchase_at=EXCLUDED.last_purchase_at, updated_at=NOW()
""")

AGG = text("""
    SELECT oi.email, oi.sku_id, oi.product_id, oi.ref_id,
        TRIM(REGEXP_REPLACE(TRIM(oi.name),
            '[A-Z][A-Z/]+\\s+[A-Z]{1,3}/[A-Z]{1,3}\\s*$', '', 'g')) AS name,
        oi.category, oi.department, oi.brand,
        COALESCE(cp.image_url, oi.image_url) AS image_url,
        COALESCE(cp.product_url, oi.product_url) AS product_url,
        COUNT(*) AS purchase_count, SUM(oi.quantity) AS total_quantity,
        SUM(oi.price * oi.quantity) AS total_spent,
        MIN(o.created_at) AS first_purchase_at, MAX(o.created_at) AS last_purchase_at
    FROM order_items oi
    JOIN orders o ON o.order_id = oi.order_id
    LEFT JOIN catalog_products cp ON cp.sku_id = oi.sku_id
    WHERE oi.email = :email AND oi.sku_id IS NOT NULL AND oi.sku_id != ''
    GROUP BY oi.email,oi.sku_id,oi.product_id,oi.ref_id,oi.name,
             oi.category,oi.department,oi.brand,cp.image_url,oi.image_url,
             cp.product_url,oi.product_url
""")

async def sync_email(session, email):
    rows = (await session.execute(AGG, {"email": email})).fetchall()
    for r in rows:
        await session.execute(UPSERT, {
            "email": r.email, "sku_id": r.sku_id, "product_id": r.product_id,
            "ref_id": r.ref_id, "name": (r.name or "").strip() or None,
            "category": r.category, "department": r.department, "brand": r.brand,
            "image_url": r.image_url, "product_url": r.product_url,
            "purchase_count": int(r.purchase_count or 0),
            "total_quantity": int(r.total_quantity or 0),
            "total_spent": float(r.total_spent or 0),
            "first_purchase_at": r.first_purchase_at,
            "last_purchase_at": r.last_purchase_at,
        })
    await session.commit()
    return len(rows)

async def main():
    target = None
    for i,a in enumerate(sys.argv[1:]):
        if a == "--email" and i+2 < len(sys.argv):
            target = sys.argv[i+2].strip().lower()
    engine = create_async_engine(get_db_url(), pool_size=5, max_overflow=10)
    Session = async_sessionmaker(engine, expire_on_commit=False)
    start = time.time(); done = items = errs = 0
    async with Session() as s:
        if target:
            emails = [target]
        else:
            r = await s.execute(text(
                "SELECT DISTINCT email FROM order_items WHERE email IS NOT NULL AND email!='' ORDER BY email"
            ))
            emails = [row[0] for row in r.fetchall()]
        total = len(emails)
        print(f"Processando {total:,} clientes...")
        for i in range(0, total, 50):
            for email in emails[i:i+50]:
                try:
                    n = await sync_email(s, email); items += n; done += 1
                except Exception as e:
                    errs += 1; print(f"  ERRO {email}: {e}")
            el = time.time()-start
            rate = done/el if el>0 else 1
            print(f"  {done}/{total} | {items:,} itens | {errs} erros | ~{(total-done)/rate:.0f}s restantes", flush=True)
    print(f"CONCLUIDO: {done:,} clientes, {items:,} itens, {errs} erros em {time.time()-start:.0f}s")
    await engine.dispose()

asyncio.run(main())
