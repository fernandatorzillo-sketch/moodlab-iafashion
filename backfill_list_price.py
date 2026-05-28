"""
backfill_list_price.py
Popula catalog_products.list_price extraindo de raw_json["sku"].sellers[0].commertialOffer.ListPrice
Idempotente — só atualiza onde list_price IS NULL.

Uso:
    python backfill_list_price.py
"""
import asyncio, os, json, time
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import text


def get_db_url():
    url = os.getenv("DATABASE_URL", "").strip()
    if url.startswith("postgresql://") and "+asyncpg" not in url:
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url


def extract_list_price(raw_json) -> float | None:
    """Extrai ListPrice do raw_json VTEX (preço 'De' — antes do desconto)."""
    if not raw_json:
        return None
    try:
        rj = json.loads(raw_json) if isinstance(raw_json, str) else raw_json
        sku = rj.get("sku") or {}
        sellers = sku.get("sellers") or sku.get("Sellers") or []
        if sellers:
            offer = sellers[0].get("commertialOffer") or {}
            lp = offer.get("ListPrice") or offer.get("listPrice")
            if lp and float(lp) > 0:
                return float(lp)
        # Fallback: nível raiz do sku
        lp = sku.get("ListPrice") or sku.get("listPrice")
        if lp and float(lp) > 0:
            return float(lp)
    except Exception:
        pass
    return None


async def main():
    engine = create_async_engine(get_db_url(), pool_size=5, max_overflow=10)
    Session = async_sessionmaker(engine, expire_on_commit=False)
    start = time.time()
    updated = skipped = no_data = 0

    async with Session() as s:
        r = await s.execute(text("""
            SELECT product_id, price, raw_json
            FROM catalog_products
            WHERE raw_json IS NOT NULL
              AND list_price IS NULL
            ORDER BY product_id
        """))
        rows = r.fetchall()
        total = len(rows)
        print(f"Produtos a processar: {total:,}")

        for i, (pid, price, raw_json) in enumerate(rows):
            lp = extract_list_price(raw_json)
            # Só salva se ListPrice > Price (é desconto real, não erro de cadastro)
            if lp and price and float(lp) > float(price):
                await s.execute(text(
                    "UPDATE catalog_products SET list_price=:lp WHERE product_id=:pid"
                ), {"lp": lp, "pid": pid})
                updated += 1
            else:
                no_data += 1

            if (i + 1) % 500 == 0:
                await s.commit()
                elapsed = time.time() - start
                rate = (i + 1) / elapsed if elapsed > 0 else 1
                rem = (total - i - 1) / rate
                print(f"  {i+1}/{total} | {updated} atualizados | ~{rem:.0f}s restantes")

        await s.commit()

    print(f"\nCONCLUÍDO: {updated} com desconto, {no_data} sem ListPrice, em {time.time()-start:.0f}s")
    await engine.dispose()


asyncio.run(main())
