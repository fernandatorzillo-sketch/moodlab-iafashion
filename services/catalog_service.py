from sqlalchemy import select
from services.closet_db import AsyncSessionLocal
from models.catalog_product import CatalogProduct


async def get_catalog_products() -> list[dict]:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(CatalogProduct).where(CatalogProduct.is_active == 1)
        )
        items = result.scalars().all()

    return [
        {
            "sku_id": item.sku_id,
            "product_id": item.product_id,
            "ref_id": item.ref_id,
            "name": item.name,
            "category": item.category,
            "department": item.department,
            "product_type": item.product_type,
            "occasion": item.occasion,
            "color": item.color,
            "print_name": item.print_name,
            "size": item.size,
            "gender": item.gender,
            "collection": item.collection,
            "image_url": item.image_url,
            "url": item.product_url,
        }
        for item in items
    ]