from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.catalog_product import CatalogProduct
from models.customer_closet_item import CustomerClosetItem
from services.closet_db import AsyncSessionLocal
from services.recommendation_service import get_customer_recommendations

SITE_BASE = "https://www.aguadecoco.com.br"


def normalize_email(email: str) -> str:
    return str(email or "").strip().lower()


def build_email_like(email: str) -> str:
    """
    Corrige problema da VTEX (emails com hash)
    """
    email = normalize_email(email)
    return f"{email}%"


def build_product_url(name, product_id, url):
    if url:
        if url.startswith("http"):
            return url
        return f"{SITE_BASE}/{url}"

    if name:
        slug = name.lower().replace(" ", "-")
        return f"{SITE_BASE}/{slug}/p"

    return SITE_BASE


async def get_customer_closet_payload(email: str) -> dict:
    email = normalize_email(email)
    email_like = build_email_like(email)

    async with AsyncSessionLocal() as session:
        closet_items = await session.execute(
            select(CustomerClosetItem, CatalogProduct)
            .outerjoin(
                CatalogProduct,
                CatalogProduct.sku_id == CustomerClosetItem.sku_id,
            )
            .where(CustomerClosetItem.email.ilike(email_like))
        )

        closet_items = closet_items.all()

    # 🔥 RECOMENDAÇÕES AGORA FUNCIONAM COM EMAIL LIKE
    recommendations = await get_customer_recommendations(
        email=email_like,
        limit=12,
    )

    closet_payload = []

    for item, catalog in closet_items:
        name = item.name or (catalog.name if catalog else None)

        product_url = build_product_url(
            name=name,
            product_id=item.product_id,
            url=item.product_url or (catalog.product_url if catalog else None),
        )

        closet_payload.append(
            {
                "id": item.product_id,
                "nome": name,
                "imagem_url": item.image_url or (catalog.image_url if catalog else ""),
                "link_produto": product_url,
            }
        )

    return {
        "found": len(closet_payload) > 0,
        "closet": closet_payload,
        "recommendations": recommendations,
        "debug": {
            "email_original": email,
            "email_like": email_like,
            "closet_count": len(closet_payload),
            "recommendation_count": len(recommendations),
        },
    }