import asyncio

from services.closet_db import AsyncSessionLocal, init_closet_db
from services.sync_control_service import mark_sync_error, mark_sync_success
from services.vtex_catalog_service import (
    fetch_product_and_sku_ids,
    fetch_product_by_id,
    fetch_sku_by_id,
)
from models.catalog_product import CatalogProduct

JOB_NAME = "catalog_incremental"


def extract_first_spec(product_data: dict, keys: list[str]) -> str | None:
    specs = product_data.get("SpecificationGroups") or []
    wanted = {k.lower() for k in keys}

    for group in specs:
        for field in group.get("Specifications", []) or []:
            name = str(field.get("Name") or "").strip().lower()
            if name in wanted:
                values = field.get("Values") or []
                if values:
                    return str(values[0]).strip()
    return None


async def run() -> None:
    await init_closet_db()

    async with AsyncSessionLocal() as session:
        try:
            start = 0
            page_size = 100
            total_upserts = 0

            while True:
                payload = fetch_product_and_sku_ids(start, start + page_size - 1)
                data = payload.get("data") or {}

                if not data:
                    break

                for product_id, sku_ids in data.items():
                    product = fetch_product_by_id(str(product_id))

                    first_sku = None
                    sku_list = sku_ids or []
                    if sku_list:
                        first_sku = fetch_sku_by_id(str(sku_list[0]))

                    row = await session.get(CatalogProduct, str(product_id))
                    if not row:
                        row = CatalogProduct(product_id=str(product_id))
                        session.add(row)

                    row.ref_id = str(product.get("RefId") or "") or None
                    row.sku_id = str(first_sku.get("Id") or "") if first_sku else None
                    row.name = product.get("Name")
                    row.brand = product.get("BrandName")
                    row.department = product.get("DepartmentName")
                    row.category = product.get("CategoryName")
                    row.product_type = extract_first_spec(product, ["tipo de produto", "tipo"])
                    row.occasion = extract_first_spec(product, ["ocasião", "ocasiao"])
                    row.color = extract_first_spec(product, ["cor", "cores"])
                    row.print_name = extract_first_spec(product, ["estamparia"])
                    row.size = extract_first_spec(product, ["tamanho"])
                    row.gender = extract_first_spec(product, ["gênero", "genero"])
                    row.collection = extract_first_spec(product, ["coleção", "colecao"])
                    row.image_url = (first_sku or {}).get("ImageUrl")
                    row.product_url = product.get("DetailUrl")
                    row.is_active = 1
                    row.raw_json = {
                        "product": product,
                        "sku": first_sku,
                    }

                    total_upserts += 1

                    if total_upserts % 100 == 0:
                        await session.commit()

                start += page_size

            await mark_sync_success(
                session=session,
                job_name=JOB_NAME,
                reference_value=str(total_upserts),
                notes=f"catalog_upserts={total_upserts}",
            )
            await session.commit()

            print(f"sync_catalog_incremental concluído: {total_upserts}")

        except Exception as e:
            await mark_sync_error(session, JOB_NAME, notes=str(e))
            await session.commit()
            raise


if __name__ == "__main__":
    asyncio.run(run())