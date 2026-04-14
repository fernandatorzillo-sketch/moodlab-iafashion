import asyncio
from sqlalchemy import text

from services.closet_db import AsyncSessionLocal, init_closet_db


async def run():
    await init_closet_db()

    statements = [
        "CREATE INDEX IF NOT EXISTS idx_orders_email ON orders(email)",
        "CREATE INDEX IF NOT EXISTS idx_orders_creation_date ON orders(creation_date)",
        "CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status)",
        "CREATE INDEX IF NOT EXISTS idx_order_items_order_id ON order_items(order_id)",
        "CREATE INDEX IF NOT EXISTS idx_order_items_email ON order_items(email)",
        "CREATE INDEX IF NOT EXISTS idx_order_items_sku_id ON order_items(sku_id)",
        "CREATE INDEX IF NOT EXISTS idx_order_items_product_id ON order_items(product_id)",
        "CREATE INDEX IF NOT EXISTS idx_customer_closet_email ON customer_closet_items(email)",
        "CREATE INDEX IF NOT EXISTS idx_catalog_products_sku_id ON catalog_products(sku_id)",
        "CREATE INDEX IF NOT EXISTS idx_catalog_products_product_id ON catalog_products(product_id)",
        "CREATE INDEX IF NOT EXISTS idx_inventory_sku_id ON inventory_by_sku(sku_id)",
        "CREATE INDEX IF NOT EXISTS idx_customer_recommendations_email ON customer_recommendations(email)",
    ]

    async with AsyncSessionLocal() as session:
        for sql in statements:
            print(sql, flush=True)
            await session.execute(text(sql))
        await session.commit()

    print("Índices criados com sucesso.", flush=True)


if __name__ == "__main__":
    asyncio.run(run())