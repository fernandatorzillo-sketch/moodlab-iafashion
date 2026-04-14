import asyncio
from collections import defaultdict

from sqlalchemy import delete, select

from models.catalog_product import CatalogProduct
from models.customer_closet_item import CustomerClosetItem
from models.customer_questionnaire_answer import CustomerQuestionnaireAnswer
from models.customer_recommendation import CustomerRecommendation
from models.inventory_by_sku import InventoryBySku
from services.closet_db import AsyncSessionLocal, init_closet_db
from services.sync_control_service import mark_sync_error, mark_sync_success

JOB_NAME = "rebuild_recommendations"


def normalize(value):
    return str(value or "").strip().lower()


def build_reason(goal: str, occasion: str, style: str, product: CatalogProduct) -> str:
    parts = []

    if goal == "cross_sell":
        parts.append("Escolhi esta peça para complementar melhor o seu closet.")
    elif goal == "up_sell":
        parts.append("Separei uma opção com proposta mais sofisticada para elevar seus looks.")
    else:
        parts.append("Selecionei uma peça alinhada ao seu estilo e ao seu histórico.")

    if occasion:
        parts.append(f"Ela conversa bem com momentos de {occasion}.")
    if style:
        parts.append(f"O perfil visual está próximo de um estilo {style}.")

    if product.category:
        parts.append(f"Categoria: {product.category}.")

    return " ".join(parts)


async def run() -> None:
    await init_closet_db()

    async with AsyncSessionLocal() as session:
        try:
            await session.execute(delete(CustomerRecommendation))

            inventory_result = await session.execute(select(InventoryBySku))
            inventory_rows = inventory_result.scalars().all()

            available_skus = {
                row.sku_id
                for row in inventory_rows
                if int(row.quantity or 0) > 0 and int(row.is_available or 0) == 1
            }

            catalog_result = await session.execute(
                select(CatalogProduct).where(CatalogProduct.is_active == 1)
            )
            catalog_rows = catalog_result.scalars().all()

            closet_result = await session.execute(select(CustomerClosetItem))
            closet_rows = closet_result.scalars().all()

            answers_result = await session.execute(select(CustomerQuestionnaireAnswer))
            answers_rows = answers_result.scalars().all()
            answers_map = {row.email: row for row in answers_rows}

            closet_by_email = defaultdict(list)
            for row in closet_rows:
                closet_by_email[row.email].append(row)

            inserted = 0

            for email, closet_items in closet_by_email.items():
                owned_skus = {normalize(item.sku_id) for item in closet_items if item.sku_id}
                owned_categories = {normalize(item.category) for item in closet_items if item.category}
                owned_departments = {normalize(item.department) for item in closet_items if item.department}
                owned_brands = {normalize(item.brand) for item in closet_items if item.brand}

                answers = answers_map.get(email)
                goal = normalize(answers.goal if answers else "")
                occasion = normalize(answers.occasion if answers else "")
                style = normalize(answers.style if answers else "")

                candidates = []

                for product in catalog_rows:
                    sku_norm = normalize(product.sku_id)
                    if not sku_norm or sku_norm in owned_skus:
                        continue

                    if product.sku_id not in available_skus:
                        continue

                    score = 0

                    if normalize(product.category) in owned_categories:
                        score += 4
                    if normalize(product.department) in owned_departments:
                        score += 3
                    if normalize(product.brand) in owned_brands:
                        score += 1
                    if occasion and normalize(product.occasion) == occasion:
                        score += 5
                    if style and normalize(product.product_type) == style:
                        score += 2

                    rec_type = "new_in"
                    if goal == "cross_sell":
                        rec_type = "cross_sell"
                        score += 3
                    elif goal == "up_sell":
                        rec_type = "up_sell"
                        score += 2

                    candidates.append((score, rec_type, product))

                candidates.sort(key=lambda x: x[0], reverse=True)
                top_candidates = candidates[:12]

                for score, rec_type, product in top_candidates:
                    session.add(
                        CustomerRecommendation(
                            email=email,
                            sku_id=product.sku_id,
                            product_id=product.product_id,
                            ref_id=product.ref_id,
                            name=product.name,
                            category=product.category,
                            department=product.department,
                            image_url=product.image_url,
                            product_url=product.product_url,
                            reason=build_reason(goal, occasion, style, product),
                            recommendation_type=rec_type,
                            score=float(score),
                        )
                    )
                    inserted += 1

                if inserted % 200 == 0:
                    await session.commit()

            await mark_sync_success(
                session=session,
                job_name=JOB_NAME,
                reference_value=str(inserted),
                notes=f"recommendations={inserted}",
            )
            await session.commit()

            print(f"rebuild_recommendations concluído: {inserted}")

        except Exception as e:
            await session.rollback()
            await mark_sync_error(session, JOB_NAME, notes=str(e))
            await session.commit()
            raise


if __name__ == "__main__":
    asyncio.run(run())