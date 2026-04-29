import asyncio

from models.catalog_product import CatalogProduct
from services.closet_db import AsyncSessionLocal, init_closet_db
from services.sync_control_service import mark_sync_error, mark_sync_success
from services.vtex_catalog_service import (
    enrich_product_fields,
    fetch_product_and_sku_ids,
    fetch_product_by_id,
    fetch_sku_by_id,
)

JOB_NAME = "catalog_incremental"

PAGE_SIZE = 100
MAX_EMPTY_PAGES = 3


async def run() -> None:
    print("1. Iniciando sync_catalog_incremental...", flush=True)
    await init_closet_db()
    print("2. Banco inicializado.", flush=True)

    async with AsyncSessionLocal() as session:
        try:
            start = 0
            total_upserts = 0
            total_errors = 0
            empty_pages = 0

            while True:
                end = start + PAGE_SIZE - 1
                print(f"3. Buscando catálogo VTEX: {start} até {end}", flush=True)

                payload = fetch_product_and_sku_ids(start, end)
                data = payload.get("data") or {}

                if not data:
                    empty_pages += 1
                    print(f"4. Página vazia. empty_pages={empty_pages}", flush=True)

                    if empty_pages >= MAX_EMPTY_PAGES:
                        break

                    start += PAGE_SIZE
                    continue

                empty_pages = 0

                for product_id, sku_ids in data.items():
                    try:
                        product_id = str(product_id)
                        sku_list = [str(sku) for sku in (sku_ids or []) if sku]

                        if not sku_list:
                            print(f"Produto sem SKU: {product_id}", flush=True)
                            continue

                        product = fetch_product_by_id(product_id)

                        first_sku_id = sku_list[0]
                        first_sku = fetch_sku_by_id(first_sku_id)

                        fields = enrich_product_fields(product, first_sku)

                        row = await session.get(CatalogProduct, product_id)
                        if not row:
                            row = CatalogProduct(product_id=product_id)
                            session.add(row)

                        row.sku_id = first_sku_id
                        row.ref_id = str(product.get("RefId") or product_id) or None
                        row.name = fields["name"]
                        row.brand = fields["brand"]
                        row.department = fields["department"]
                        row.category = fields["category"]
                        row.product_type = fields["product_type"]
                        row.occasion = fields["occasion"]
                        row.color = fields["color"]
                        row.print_name = fields["print_name"]
                        row.size = fields["size"]
                        row.gender = fields["gender"]
                        row.collection = fields["collection"]
                        row.image_url = fields["image_url"]
                        row.product_url = fields["product_url"]
                        row.is_active = 1
                        row.raw_json = {
                            "product": product,
                            "first_sku": first_sku,
                            "all_sku_ids": sku_list,
                        }

                        total_upserts += 1

                        if total_upserts % 100 == 0:
                            await session.commit()
                            print(
                                f"5. Checkpoint | catalog_upserts={total_upserts} | errors={total_errors}",
                                flush=True,
                            )

                    except Exception as item_error:
                        total_errors += 1
                        print(
                            f"ERRO ao processar product_id={product_id}: {item_error}",
                            flush=True,
                        )

                await session.commit()
                start += PAGE_SIZE

            await mark_sync_success(
                session=session,
                job_name=JOB_NAME,
                reference_value=str(total_upserts),
                notes=f"catalog_upserts={total_upserts}; errors={total_errors}",
            )
            await session.commit()

            print(
                f"6. sync_catalog_incremental concluído | upserts={total_upserts} | errors={total_errors}",
                flush=True,
            )

        except Exception as e:
            print(f"ERRO GERAL no sync_catalog_incremental: {e}", flush=True)
            await session.rollback()
            await mark_sync_error(session, JOB_NAME, notes=str(e))
            await session.commit()
            raise


if __name__ == "__main__":
    asyncio.run(run())