import asyncio

from sqlalchemy import delete, select

from models.catalog_product import CatalogProduct
from models.inventory_by_sku import InventoryBySku
from services.closet_db import AsyncSessionLocal, init_closet_db
from services.sync_control_service import mark_sync_error, mark_sync_success
from services.vtex_inventory_service import fetch_inventory_for_sku

JOB_NAME = "inventory_incremental"


async def run() -> None:
    await init_closet_db()

    async with AsyncSessionLocal() as session:
        try:
            result = await session.execute(
                select(CatalogProduct.sku_id).where(CatalogProduct.sku_id.is_not(None))
            )
            sku_ids = [row[0] for row in result.all() if row[0]]

            await session.execute(delete(InventoryBySku))

            processed = 0
            for sku_id in sku_ids:
                payload = fetch_inventory_for_sku(str(sku_id))
                balances = payload.get("balance") or []

                for balance in balances:
                    qty = int(balance.get("totalQuantity") or 0)
                    warehouse_id = str(balance.get("warehouseId") or "")

                    session.add(
                        InventoryBySku(
                            sku_id=str(sku_id),
                            warehouse_id=warehouse_id or None,
                            quantity=qty,
                            is_available=1 if qty > 0 else 0,
                        )
                    )

                processed += 1
                if processed % 100 == 0:
                    await session.commit()

            await mark_sync_success(
                session=session,
                job_name=JOB_NAME,
                reference_value=str(processed),
                notes=f"inventory_skus={processed}",
            )
            await session.commit()

            print(f"sync_inventory_incremental concluído: {processed}")

        except Exception as e:
            await session.rollback()
            await mark_sync_error(session, JOB_NAME, notes=str(e))
            await session.commit()
            raise


if __name__ == "__main__":
    asyncio.run(run())