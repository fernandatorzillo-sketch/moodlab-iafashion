from sqlalchemy import select
from services.closet_db import AsyncSessionLocal
from models.customer_recommendation import CustomerRecommendation


async def get_customer_recommendations(email: str) -> list[dict]:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(CustomerRecommendation).where(CustomerRecommendation.email == email)
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
            "image_url": item.image_url,
            "url": item.product_url,
            "reason": item.reason,
            "recommendation_type": item.recommendation_type,
            "score": item.score,
        }
        for item in items
    ]