import asyncio

from sqlalchemy import delete, select

from models.catalog_product import CatalogProduct
from models.inventory_by_sku import InventoryBySku
from services.closet_db import AsyncSessionLocal, init_closet_db
from services.sync_control_service import mark_sync_error, mark_sync_success
from services.vtex_inventory_service import fetch_inventory_for_sku

JOB_NAME = "inventory_incremental"
COMMIT_EVERY = 50


async def run() -> None:
    print("1. Iniciando sync_inventory_incremental...", flush=True)
    await init_closet_db()
    print("2. Banco inicializado.", flush=True)

    async with AsyncSessionLocal() as session:
        try:
            print("3. Buscando SKUs do catálogo...", flush=True)
            result = await session.execute(
                select(CatalogProduct.sku_id).where(CatalogProduct.sku_id.is_not(None))
            )
            sku_ids = [row[0] for row in result.all() if row[0]]
            total_skus = len(sku_ids)

            print(f"4. Total de SKUs encontrados: {total_skus}", flush=True)

            print("5. Limpando tabela inventory_by_sku...", flush=True)
            await session.execute(delete(InventoryBySku))
            await session.commit()
            print("6. Tabela inventory_by_sku limpa.", flush=True)

            processed = 0
            inserted_rows = 0
            error_count = 0

            for sku_id in sku_ids:
                try:
                    payload = fetch_inventory_for_sku(str(sku_id))
                    balances = payload.get("balance") or []

                    seen = set()

                    for balance in balances:
                        warehouse_id = str(balance.get("warehouseId") or "").strip()
                        key = (str(sku_id), warehouse_id)

                        # evita duplicidade do mesmo sku + warehouse no mesmo payload
                        if key in seen:
                            continue
                        seen.add(key)

                        qty = int(balance.get("totalQuantity") or 0)

                        session.add(
                            InventoryBySku(
                                sku_id=str(sku_id),
                                warehouse_id=warehouse_id or None,
                                quantity=qty,
                                is_available=1 if qty > 0 else 0,
                            )
                        )
                        inserted_rows += 1

                    processed += 1

                    if processed % COMMIT_EVERY == 0:
                        await session.commit()
                        print(
                            f"7. Checkpoint | processados={processed}/{total_skus} | "
                            f"linhas_estoque={inserted_rows} | erros={error_count}",
                            flush=True,
                        )

                except Exception as sku_error:
                    error_count += 1
                    print(
                        f"ERRO ao processar sku_id={sku_id}: {sku_error}",
                        flush=True,
                    )

                    # reseta a sessão para continuar processando os próximos SKUs
                    await session.rollback()

            await session.commit()
            print(
                f"8. Processamento concluído | processados={processed}/{total_skus} | "
                f"linhas_estoque={inserted_rows} | erros={error_count}",
                flush=True,
            )

            await mark_sync_success(
                session=session,
                job_name=JOB_NAME,
                reference_value=str(processed),
                notes=f"inventory_skus={processed}; inventory_rows={inserted_rows}; errors={error_count}",
            )
            await session.commit()

            print(
                f"sync_inventory_incremental concluído: processados={processed}, "
                f"linhas_estoque={inserted_rows}, erros={error_count}",
                flush=True,
            )

        except Exception as e:
            print(f"ERRO GERAL no sync_inventory_incremental: {e}", flush=True)
            await session.rollback()
            await mark_sync_error(session, JOB_NAME, notes=str(e))
            await session.commit()
            raise


if __name__ == "__main__":
    asyncio.run(run())