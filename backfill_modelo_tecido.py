"""
Backfill campos modelo e tecido nos produtos existentes via VTEX specs API.
Roda uma vez para popular o banco com os dados já disponíveis.
"""
import asyncio, os, sys, time, requests
sys.path.insert(0, '.')
from services.closet_db import init_closet_db, AsyncSessionLocal
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from services.vtex_catalog_service import fetch_product_specifications

VTEX_ACCOUNT = os.getenv("VTEX_ACCOUNT", "")
VTEX_KEY     = os.getenv("VTEX_APP_KEY", "")
VTEX_TOKEN   = os.getenv("VTEX_APP_TOKEN", "")

async def main():
    await init_closet_db()
    url = os.getenv("DATABASE_URL","").replace("postgresql://","postgresql+asyncpg://",1)
    engine = create_async_engine(url, pool_size=3)
    Session = async_sessionmaker(engine, expire_on_commit=False)
    updated = skipped = errors = 0
    start = time.time()

    async with Session() as s:
        r = await s.execute(text(
            "SELECT product_id FROM catalog_products "
            "WHERE (modelo IS NULL OR tecido IS NULL) AND is_active=1 "
            "ORDER BY product_id LIMIT 5000"
        ))
        rows = [row[0] for row in r.fetchall()]
        print(f"Produtos sem modelo/tecido: {len(rows)}")

        for i, product_id in enumerate(rows):
            try:
                specs = fetch_product_specifications(str(product_id))
                if not specs:
                    skipped += 1
                    continue

                def get_spec(key):
                    val = specs.get(key.lower())
                    if val: return val
                    for k, v in specs.items():
                        if key.lower() in k or k in key.lower():
                            return v
                    return None

                modelo = get_spec("0- modelo") or get_spec("modelo")
                tecido = get_spec("tecido")

                if modelo or tecido:
                    await s.execute(text(
                        "UPDATE catalog_products SET "
                        "modelo = COALESCE(:m, modelo), tecido = COALESCE(:t, tecido) "
                        "WHERE product_id = :pid"
                    ), {"m": modelo.upper().strip() if modelo else None,
                        "t": tecido.strip() if tecido else None,
                        "pid": product_id})
                    updated += 1
                    if updated % 50 == 0:
                        await s.commit()
                        elapsed = time.time() - start
                        print(f"  [{i+1}/{len(rows)}] {updated} atualizados | {elapsed:.0f}s")
                else:
                    skipped += 1

                time.sleep(0.15)
            except Exception as e:
                errors += 1
                if errors % 20 == 0:
                    print(f"  Erros: {errors}")

        await s.commit()
    print(f"\nFIM: {updated} atualizados, {skipped} sem spec, {errors} erros | {time.time()-start:.0f}s")
    await engine.dispose()

asyncio.run(main())
