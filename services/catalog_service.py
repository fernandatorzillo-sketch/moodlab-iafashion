from services.database import database


async def get_catalog_products():
    rows = await database.fetch_all(
        query="""
            SELECT
                product_id,
                sku_id,
                ref_id,
                name,
                department,
                category,
                product_type,
                occasion,
                colors,
                estamparia,
                size,
                gender,
                image_url,
                product_url,
                brand,
                in_stock,
                stock_quantity
            FROM catalog_products
            WHERE in_stock = TRUE
              AND stock_quantity > 0
        """
    )

    products = []
    for row in rows:
        products.append({
            "product_id": row["product_id"],
            "sku_id": row["sku_id"],
            "ref_id": row["ref_id"],
            "name": row["name"],
            "department": row["department"],
            "category": row["category"],
            "product_type": row["product_type"],
            "occasion": row["occasion"],
            "colors": row["colors"] or [],
            "estamparia": row["estamparia"],
            "size": row["size"],
            "gender": row["gender"],
            "image_url": row["image_url"],
            "url": row["product_url"],
            "brand": row["brand"],
            "in_stock": row["in_stock"],
            "stock_quantity": row["stock_quantity"],
        })
    return products