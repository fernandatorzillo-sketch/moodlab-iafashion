"""
backfill_specs.py
Popula print_name, occasion, collection, product_type, color, gender
em catalog_products buscando specs da API VTEX.
Idempotente — só atualiza produtos onde print_name IS NULL.
"""
import asyncio, os, sys, time, requests
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import text

def get_db_url():
    url = os.getenv("DATABASE_URL","").strip()
    if url.startswith("postgresql://") and "+asyncpg" not in url:
        url = url.replace("postgresql://","postgresql+asyncpg://",1)
    return url

VTEX_ACCOUNT = os.getenv("VTEX_ACCOUNT","")
VTEX_KEY     = os.getenv("VTEX_APP_KEY","")
VTEX_TOKEN   = os.getenv("VTEX_APP_TOKEN","")

SPEC_MAP = {
    "cores": "color", "cor": "color",
    "estamparia": "print_name",
    "1- estamparia": "print_name", "0- estamparia": "print_name",
    "ocasião": "occasion", "ocasiao": "occasion",
    "1- ocasião": "occasion", "1- ocasiao": "occasion",
    "0- linha": "collection", "1- linha": "collection", "linha": "collection",
    "1- coleção": "collection", "colecao": "collection",
    "tipo de produto": "product_type",
    "1- tipo de produto": "product_type", "0- produto": "product_type",
    "0- gênero": "gender", "genero": "gender",
    "1- gênero": "gender", "1- genero": "gender",
}

def fetch_specs(product_id: str) -> dict:
    try:
        url = f"https://{VTEX_ACCOUNT}.vtexcommercestable.com.br/api/catalog_system/pvt/products/{product_id}/specification"
        r = requests.get(url, headers={
            "X-VTEX-API-AppKey": VTEX_KEY,
            "X-VTEX-API-AppToken": VTEX_TOKEN,
        }, timeout=10)
        if r.status_code != 200:
            return {}
        result = {}
        for spec in (r.json() or []):
            name = str(spec.get("Name") or "").strip().lower()
            vals = spec.get("Value") or []
            if name and vals:
                field = SPEC_MAP.get(name)
                if field:
                    result[field] = str(vals[0]).strip()
        return result
    except Exception:
        return {}

async def main():
    engine = create_async_engine(get_db_url(), pool_size=5, max_overflow=10)
    Session = async_sessionmaker(engine, expire_on_commit=False)
    start = time.time()
    updated = errors = skipped = 0

    async with Session() as s:
        # Pega produtos sem print_name (não sincronizados ainda)
        r = await s.execute(text("""
            SELECT DISTINCT product_id FROM catalog_products
            WHERE product_id IS NOT NULL
            AND print_name IS NULL
            ORDER BY product_id
        """))
        product_ids = [row[0] for row in r.fetchall()]
        total = len(product_ids)
        print(f"Produtos sem specs: {total:,}")

        for i, pid in enumerate(product_ids):
            specs = fetch_specs(pid)
            if not specs:
                skipped += 1
            else:
                sets = ", ".join(f"{k}=:{k}" for k in specs)
                specs["pid"] = pid
                await s.execute(text(
                    f"UPDATE catalog_products SET {sets} WHERE product_id=:pid"
                ), specs)
                updated += 1

            if (i+1) % 100 == 0:
                await s.commit()
                el = time.time()-start
                rate = (i+1)/el if el>0 else 1
                rem = (total-i-1)/rate
                print(f"  {i+1}/{total} | {updated} atualizados | ~{rem:.0f}s restantes", flush=True)
                time.sleep(0.05)

        await s.commit()

    print(f"\nCONCLUIDO: {updated} atualizados, {skipped} sem specs, em {time.time()-start:.0f}s")
    await engine.dispose()

asyncio.run(main())
