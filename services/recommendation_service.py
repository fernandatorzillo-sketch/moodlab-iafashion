from sqlalchemy import select
from services.closet_db import AsyncSessionLocal
from models.customer_recommendation import CustomerRecommendation


def normalize(value):
    return str(value or "").strip().lower()


async def get_customer_recommendations(
    email: str,
    occasion: str = "",
    goal: str = "",
    style: str = "",
    limit: int = 8,
) -> list[dict]:
    email = normalize(email)
    occasion = normalize(occasion)
    goal = normalize(goal)
    style = normalize(style)

    async with AsyncSessionLocal() as session:
        query = select(CustomerRecommendation).where(
            CustomerRecommendation.email == email
        )

        if goal:
            query = query.where(CustomerRecommendation.recommendation_type == goal)

        query = query.order_by(CustomerRecommendation.score.desc())

        result = await session.execute(query)
        items = result.scalars().all()

    recommendations = []

    for item in items:
        reason_text = normalize(item.reason)
        category_text = normalize(item.category)
        department_text = normalize(item.department)
        name_text = normalize(item.name)

        # filtro leve por ocasião
        if occasion:
            searchable_text = " ".join([reason_text, category_text, department_text, name_text])
            if occasion not in searchable_text:
                continue

        # filtro leve por estilo
        if style:
            searchable_text = " ".join([reason_text, category_text, department_text, name_text])
            if style not in searchable_text:
                # não elimina imediatamente se houver score bom
                if float(item.score or 0) < 6:
                    continue

        recommendations.append(
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
                "score": float(item.score or 0),
            }
        )

        if len(recommendations) >= limit:
            break

    return recommendations