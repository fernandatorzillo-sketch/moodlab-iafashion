from sqlalchemy import func, or_, select

from models.catalog_product import CatalogProduct
from models.customer_recommendation import CustomerRecommendation
from models.inventory_by_sku import InventoryBySku
from services.closet_db import AsyncSessionLocal


def normalize(value):
    return str(value or "").strip().lower()


def clean_url(url):
    if not url:
        return None
    url = str(url).strip()
    if url.startswith("http"):
        return url
    if url.startswith("/"):
        return f"https://www.aguadecoco.com.br{url}"
    return f"https://www.aguadecoco.com.br/{url}"


async def get_customer_recommendations(
    email: str,
    occasion: str = "",
    goal: str = "",
    style: str = "",
    limit: int = 12,
) -> list[dict]:
    email = normalize(email)
    email_like = email if "%" in email else f"{email}%"
    limit = max(1, min(int(limit or 12), 24))

    async with AsyncSessionLocal() as session:
        saved_result = await session.execute(
            select(CustomerRecommendation)
            .where(CustomerRecommendation.email.ilike(email_like))
            .order_by(CustomerRecommendation.score.desc().nullslast())
            .limit(limit)
        )
        saved = saved_result.scalars().all()

        if saved:
            return [_format_saved_recommendation(item) for item in saved]

        filters = [
            CatalogProduct.is_active == 1,
            CatalogProduct.sku_id.is_not(None),
        ]

        query = (
            select(CatalogProduct)
            .join(InventoryBySku, InventoryBySku.sku_id == CatalogProduct.sku_id)
            .where(
                *filters,
                InventoryBySku.quantity > 0,
                InventoryBySku.is_available == 1,
            )
            .limit(limit)
        )

        if occasion:
            occ = f"%{normalize(occasion)}%"
            query = query.where(
                or_(
                    func.lower(func.coalesce(CatalogProduct.occasion, "")).like(occ),
                    func.lower(func.coalesce(CatalogProduct.name, "")).like(occ),
                    func.lower(func.coalesce(CatalogProduct.category, "")).like(occ),
                    func.lower(func.coalesce(CatalogProduct.department, "")).like(occ),
                )
            )

        result = await session.execute(query)
        products = result.scalars().all()

    return [_format_product_recommendation(product) for product in products]


def _format_saved_recommendation(item: CustomerRecommendation) -> dict:
    url = clean_url(item.product_url)

    return {
        "sku_id": item.sku_id,
        "product_id": item.product_id,
        "ref_id": item.ref_id,
        "name": item.name,
        "nome": item.name,
        "category": item.category,
        "categoria": item.category,
        "department": item.department,
        "departamento": item.department,
        "image_url": item.image_url,
        "imagem_url": item.image_url,
        "product_url": url,
        "link_produto": url,
        "url": url,
        "reason": item.reason or "Selecionado para você.",
        "motivo": item.reason or "Selecionado para você.",
        "recommendation_type": item.recommendation_type,
        "score": float(item.score or 0),
    }


def _format_product_recommendation(product: CatalogProduct) -> dict:
    url = clean_url(product.product_url)

    return {
        "sku_id": product.sku_id,
        "product_id": product.product_id,
        "ref_id": product.ref_id,
        "name": product.name,
        "nome": product.name,
        "category": product.category,
        "categoria": product.category,
        "department": product.department,
        "departamento": product.department,
        "image_url": product.image_url,
        "imagem_url": product.image_url,
        "product_url": url,
        "link_produto": url,
        "url": url,
        "reason": "Sugestão disponível em estoque para complementar seu closet.",
        "motivo": "Sugestão disponível em estoque para complementar seu closet.",
        "recommendation_type": "available_stock",
        "score": 1.0,
    }