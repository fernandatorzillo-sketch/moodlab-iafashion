from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.customer import Customer
from models.customer_closet_item import CustomerClosetItem
from services.closet_db import AsyncSessionLocal
from services.recommendation_service import get_customer_recommendations


def normalize_email(email: str) -> str:
    return str(email or "").strip().lower()


async def get_customer_closet_payload(email: str) -> dict:
    email = normalize_email(email)

    if not email:
        return {
            "found": False,
            "customer": None,
            "closet": [],
            "looks": [],
            "recommendations": [],
            "debug": {
                "email": "",
                "closet_count": 0,
                "message": "E-mail vazio.",
            },
        }

    async with AsyncSessionLocal() as session:
        customer = await _get_customer(session, email)
        closet_items = await _get_customer_closet_items(session, email)

    recommendations = await get_customer_recommendations(email)

    customer_name = None
    if customer:
        customer_name = customer.full_name or customer.first_name or email.split("@")[0]
    else:
        customer_name = email.split("@")[0]

    closet_payload = [
        {
            "sku_id": item.sku_id,
            "product_id": item.product_id,
            "ref_id": item.ref_id,
            "name": item.name,
            "category": item.category,
            "department": item.department,
            "brand": item.brand,
            "image_url": item.image_url,
            "url": item.product_url,
            "purchase_count": item.purchase_count,
            "quantity": item.total_quantity,
            "total_spent": float(item.total_spent or 0),
            "last_purchase_at": item.last_purchase_at.isoformat() if item.last_purchase_at else None,
        }
        for item in closet_items
    ]

    return {
        "found": len(closet_payload) > 0,
        "customer": {
            "name": customer_name,
            "email": email,
        },
        "closet": closet_payload,
        "looks": [],
        "recommendations": recommendations,
        "debug": {
            "email": email,
            "closet_count": len(closet_payload),
            "recommendation_count": len(recommendations),
            "message": "Closet e recomendações lidos do banco consolidado.",
        },
    }


async def _get_customer(session: AsyncSession, email: str):
    result = await session.execute(
        select(Customer).where(Customer.email == email)
    )
    return result.scalar_one_or_none()


async def _get_customer_closet_items(session: AsyncSession, email: str):
    result = await session.execute(
        select(CustomerClosetItem)
        .where(CustomerClosetItem.email == email)
        .order_by(CustomerClosetItem.last_purchase_at.desc().nullslast())
    )
    return result.scalars().all()