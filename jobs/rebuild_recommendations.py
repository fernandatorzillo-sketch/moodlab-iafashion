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

# 👉 IMPORTANTE: usando o engine novo
from services.recommendation_engine import build_recommendations

JOB_NAME = "rebuild_recommendations"

EMAIL_BATCH_SIZE = 100


async def fetch_email_batch(session, offset: int, limit: int):
    result = await session.execute(
        select(CustomerClosetItem.email)
        .where(CustomerClosetItem.email.is_not(None))
        .distinct()
        .order_by(CustomerClosetItem.email)
        .offset(offset)
        .limit(limit)
    )
    return [row[0] for row in result.fetchall() if row[0]]


async def fetch_closet_batch(session, emails):
    result = await session.execute(
        select(CustomerClosetItem).where(CustomerClosetItem.email.in_(emails))
    )
    rows = result.scalars().all()

    data = defaultdict(list)
    for r in rows:
        data[r.email].append({
            "sku_id": r.sku_id,
            "category": r.category,
            "department": r.department,
            "product_type": getattr(r, "product_type", ""),
            "color": getattr(r, "color", ""),
        })
    return data


async def fetch_answers_batch(session, emails):
    result = await session.execute(
        select(CustomerQuestionnaireAnswer).where(
            CustomerQuestionnaireAnswer.email.in_(emails)
        )
    )
    rows = result.scalars().all()

    return {
        r.email: {
            "goal": r.goal,
            "occasion": r.occasion,
            "style": r.style,
        }
        for r in rows
    }


async def fetch_catalog(session):
    result = await session.execute(
        select(CatalogProduct)
        .join(InventoryBySku, InventoryBySku.sku_id == CatalogProduct.sku_id)
        .where(
            CatalogProduct.is_active == 1,
            InventoryBySku.is_available == 1,
            InventoryBySku.quantity > 0,
        )
    )

    rows = result.scalars().all()

    catalog = []
    for p in rows:
        catalog.append({
            "sku_id": p.sku_id,
            "product_id": p.product_id,
            "ref_id": p.ref_id,
            "name": p.name,
            "category": p.category,
            "department": p.department,
            "product_type": p.product_type,
            "occasion": p.occasion,
            "estamparia": getattr(p, "estamparia", ""),
            "colors": getattr(p, "color", ""),
            "image_url": p.image_url,
            "product_url": p.product_url,
            "stock_quantity": 1,
            "in_stock": True,
        })

    return catalog


async def run():
    await init_closet_db()

    async with AsyncSessionLocal() as session:
        try:
            print("1. Limpando recomendações antigas...", flush=True)
            await session.execute(delete(CustomerRecommendation))
            await session.commit()

            print("2. Carregando catálogo...", flush=True)
            catalog = await fetch_catalog(session)
            print(f"Catálogo carregado: {len(catalog)} produtos", flush=True)

            inserted = 0
            offset = 0
            batch = 0

            while True:
                batch += 1
                emails = await fetch_email_batch(session, offset, EMAIL_BATCH_SIZE)

                if not emails:
                    print("3. Fim dos clientes", flush=True)
                    break

                print(f"4. Lote {batch} | {len(emails)} clientes", flush=True)

                closet_map = await fetch_closet_batch(session, emails)
                answers_map = await fetch_answers_batch(session, emails)

                for email in emails:
                    closet = closet_map.get(email, [])
                    if not closet:
                        continue

                    answers = answers_map.get(email, {})

                    result = build_recommendations(
                        closet_products=closet,
                        catalog=catalog,
                        answers=answers,
                        limit=12
                    )

                    recs = result["recommendations"]

                    for r in recs:
                        session.add(
                            CustomerRecommendation(
                                email=email,
                                sku_id=r.get("sku_id"),
                                product_id=r.get("product_id"),
                                ref_id=r.get("ref_id"),
                                name=r.get("name"),
                                category=r.get("category"),
                                department=r.get("department"),
                                image_url=r.get("image_url"),
                                product_url=r.get("url"),
                                reason=r.get("reason"),
                                recommendation_type="engine",
                                score=float(r.get("score", 0)),
                            )
                        )
                        inserted += 1

                    if inserted % 200 == 0:
                        print(f"Checkpoint: {inserted}", flush=True)
                        await session.commit()

                await session.commit()
                offset += EMAIL_BATCH_SIZE

            print(f"5. Finalizado | total inserido={inserted}", flush=True)

            await mark_sync_success(
                session=session,
                job_name=JOB_NAME,
                reference_value=str(inserted),
                notes=f"recommendations={inserted}",
            )
            await session.commit()

        except Exception as e:
            print(f"ERRO: {e}", flush=True)
            await session.rollback()
            await mark_sync_error(session, JOB_NAME, notes=str(e))
            await session.commit()
            raise


if __name__ == "__main__":
    asyncio.run(run())