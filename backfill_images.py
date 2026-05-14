"""
backfill_images.py
Atualiza image_url em customer_closet_items e catalog_products
usando a API VTEX (que retorna URLs sem restrição de hotlink).
Idempotente — só atualiza onde image_url usa o formato antigo com nome de arquivo.
"""
import asyncio, os, time, requests
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import text

def get_db_url():
    url = os.getenv("DATABASE_URL","").strip()
    if url.startswith("postgresql://") and "+asyncpg" not in url:
        url = url.replace("postgresql://","postgresql+asyncpg://",1)
    return url

VTEX  = os.getenv("VTEX_ACCOUNT","")
KEY   = os.getenv("VTEX_APP_KEY","")
TOKEN = os.getenv("VTEX_APP_TOKEN","")

def fetch_vtex_image(sku_id: str) -> str | None:
    try:
        url = f"https://{VTEX}.vtexcommercestable.com.br/api/catalog_system/pvt/sku/stockkeepingunitbyid/{sku_id}"
        r = requests.get(url, headers={
            "X-VTEX-API-AppKey": KEY, "X-VTEX-API-AppToken": TOKEN
        }, timeout=8)
        if r.status_code == 200:
            imgs = r.json().get("Images") or []
            if imgs:
                return imgs[0].get("ImageUrl","").split("?")[0]
    except Exception:
        pass
    return None

async def main():
    engine = create_async_engine(get_db_url(), pool_size=5, max_overflow=10)
    Session = async_sessionmaker(engine, expire_on_commit=False)
    start = time.time()
    updated = errors = 0

    async with Session() as s:
        # SKUs cujas imagens têm o nome de arquivo no path (formato antigo bloqueado pela VTEX)
        r = await s.execute(text("""
            SELECT DISTINCT sku_id FROM customer_closet_items
            WHERE sku_id IS NOT NULL
            AND image_url IS NOT NULL
            AND image_url ~ '/arquivos/ids/[0-9]+-[0-9]+-[0-9]+/[A-Z0-9]'
        """))
        skus = [row[0] for row in r.fetchall()]
        total = len(skus)
        print(f"SKUs com imagem antiga: {total:,}")

        for i, sku in enumerate(skus):
            img = fetch_vtex_image(sku)
            if img:
                await s.execute(text(
                    "UPDATE customer_closet_items SET image_url=:img WHERE sku_id=:sku"
                ), {"img": img, "sku": sku})
                await s.execute(text(
                    "UPDATE catalog_products SET image_url=:img WHERE sku_id=:sku"
                ), {"img": img, "sku": sku})
                updated += 1
            else:
                errors += 1

            if (i+1) % 50 == 0:
                await s.commit()
                el = time.time()-start
                rate = (i+1)/el if el>0 else 1
                print(f"  {i+1}/{total} | {updated} ok | {errors} erros | ~{(total-i-1)/rate:.0f}s restantes", flush=True)
                time.sleep(0.05)

        await s.commit()

    print(f"\nCONCLUIDO: {updated} imagens atualizadas, {errors} sem imagem, em {time.time()-start:.0f}s")
    await engine.dispose()

asyncio.run(main())
