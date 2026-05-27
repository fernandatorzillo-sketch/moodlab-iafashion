"""
daily_sync_job.py
-----------------
Job que roda 1x por dia para atualizar catálogo + estoque no banco.
Invocado pelo Render Cron Jobs (ou manualmente).

Render Cron: adicionar em render.yaml ou via painel:
  Schedule: 0 4 * * *   (todo dia às 04:00 UTC / 01:00 BRT)
  Command:  cd src && python jobs/daily_sync_job.py
"""
import asyncio
import logging
import os
import sys
import time
from datetime import datetime

# Adiciona src ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("daily_sync")


async def run_sync():
    from services.closet_db import AsyncSessionLocal, init_closet_db
    from models.catalog_product import CatalogProduct
    from models.inventory_by_sku import InventoryBySku
    from sqlalchemy import select, update, text

    await init_closet_db()

    log.info("=== MoodLab Daily Sync iniciado ===")
    start = time.time()

    # 1. Sync incremental de catálogo VTEX
    try:
        log.info("1/3 Sincronizando catálogo VTEX...")
        from jobs.sync_catalog_incremental import run as run_catalog
        await run_catalog()
        log.info("✓ Catálogo sincronizado")
    except Exception as e:
        log.error(f"✗ Erro no sync de catálogo: {e}")

    # 2. Sync incremental de estoque VTEX
    try:
        log.info("2/3 Sincronizando estoque VTEX...")
        from jobs.sync_inventory_incremental import run as run_inventory
        await run_inventory()
        log.info("✓ Estoque sincronizado")
    except Exception as e:
        log.error(f"✗ Erro no sync de estoque: {e}")

    # 3. Marca produtos sem estoque como inativos
    try:
        log.info("3/3 Atualizando is_active por estoque...")
        async with AsyncSessionLocal() as db:
            # Desativa produtos com SKU sem estoque disponível
            await db.execute(text("""
                UPDATE catalog_products cp
                SET is_active = 0
                WHERE cp.sku_id IS NOT NULL
                  AND NOT EXISTS (
                    SELECT 1 FROM inventory_by_sku i
                    WHERE i.sku_id = cp.sku_id
                      AND i.is_available = 1
                      AND i.quantity > 0
                  )
            """))
            # Reativa produtos que voltaram ao estoque
            await db.execute(text("""
                UPDATE catalog_products cp
                SET is_active = 1
                WHERE cp.sku_id IS NOT NULL
                  AND EXISTS (
                    SELECT 1 FROM inventory_by_sku i
                    WHERE i.sku_id = cp.sku_id
                      AND i.is_available = 1
                      AND i.quantity > 0
                  )
            """))
            await db.commit()
            # Conta ativos
            r = await db.execute(text(
                "SELECT COUNT(*) FROM catalog_products WHERE is_active = 1"
            ))
            active = r.scalar()
            r2 = await db.execute(text(
                "SELECT COUNT(*) FROM catalog_products WHERE is_active = 0"
            ))
            inactive = r2.scalar()
            log.info(f"✓ is_active atualizado: {active} ativos, {inactive} inativos")
    except Exception as e:
        log.error(f"✗ Erro ao atualizar is_active: {e}")

    elapsed = time.time() - start
    log.info(f"=== Sync concluído em {elapsed:.1f}s ===")


if __name__ == "__main__":
    asyncio.run(run_sync())
