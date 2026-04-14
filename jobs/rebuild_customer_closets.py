import asyncio
from datetime import datetime, timedelta, timezone
from collections import defaultdict

from sqlalchemy import select

from models.customer_closet_item import CustomerClosetItem
from models.order import Order
from models.order_item import OrderItem
from services.closet_db import AsyncSessionLocal, init_closet_db
from services.sync_control_service import mark_sync_error, mark_sync_success

JOB_NAME = "rebuild_customer_closets"
MONTHS_BACK = 24
BATCH_SIZE = 500


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


async def run() -> None:
    print("Iniciando rebuild_customer_closets...", flush=True)
    await init_closet_db()

    cutoff = utcnow() - timedelta(days=30 * MONTHS_BACK)

    async with AsyncSessionLocal() as session:
        try:
            query = (
                select(OrderItem, Order)
                .join(Order, Order.order_id == OrderItem.order_id)
                .where(Order.creation_date >= cutoff)
            )

            result = await session.stream(query)

            aggregated = defaultdict(lambda: {
                "purchase_count": 0,
                "total_quantity": 0,
                "total_spent": 0.0,
                "first_purchase_at": None,
                "last_purchase_at": None,
                "data": None,
            })

            processed = 0

            async for order_item, order in result:
                email = (order.email or "").strip().lower()
                if not email:
                    continue

                status = (order.status or "").strip().lower()
                if status in {"canceled", "cancelado"}:
                    continue

                key = (
                    email,
                    order_item.sku_id or order_item.product_id or order_item.ref_id or order_item.name or "unknown",
                )

                agg = aggregated[key]

                if not agg["data"]:
                    agg["data"] = {
                        "email": email,
                        "sku_id": order_item.sku_id,
                        "product_id": order_item.product_id,
                        "ref_id": order_item.ref_id,
                        "name": order_item.name,
                        "category": order_item.category,
                        "department": order_item.department,
                        "brand": order_item.brand,
                        "image_url": order_item.image_url,
                        "product_url": order_item.product_url,
                    }

                agg["purchase_count"] += 1
                agg["total_quantity"] += int(order_item.quantity or 0)
                agg["total_spent"] += float(order_item.total_value or 0)

                if order.creation_date:
                    if not agg["first_purchase_at"] or order.creation_date < agg["first_purchase_at"]:
                        agg["first_purchase_at"] = order.creation_date
                    if not agg["last_purchase_at"] or order.creation_date > agg["last_purchase_at"]:
                        agg["last_purchase_at"] = order.creation_date

                processed += 1

                if processed % 500 == 0:
                    print(f"Processados {processed} itens...", flush=True)

            print(f"Total agregados: {len(aggregated)}", flush=True)

            # limpa tabela
            await session.execute(CustomerClosetItem.__table__.delete())
            await session.commit()

            inserted = 0

            for item in aggregated.values():
                data = item["data"]

                session.add(
                    CustomerClosetItem(
                        email=data["email"],
                        sku_id=data["sku_id"],
                        product_id=data["product_id"],
                        ref_id=data["ref_id"],
                        name=data["name"],
                        category=data["category"],
                        department=data["department"],
                        brand=data["brand"],
                        image_url=data["image_url"],
                        product_url=data["product_url"],
                        purchase_count=item["purchase_count"],
                        total_quantity=item["total_quantity"],
                        total_spent=item["total_spent"],
                        first_purchase_at=item["first_purchase_at"],
                        last_purchase_at=item["last_purchase_at"],
                    )
                )

                inserted += 1

                if inserted % BATCH_SIZE == 0:
                    await session.commit()
                    print(f"Inseridos {inserted} itens...", flush=True)

            await mark_sync_success(
                session=session,
                job_name=JOB_NAME,
                reference_value=utcnow().isoformat(),
                notes=f"closet_items={inserted}",
            )
            await session.commit()

            print(f"Rebuild concluído: {inserted}", flush=True)

        except Exception as e:
            await session.rollback()
            print(f"Erro: {e}", flush=True)
            await mark_sync_error(session, JOB_NAME, notes=str(e))
            await session.commit()
            raise


if __name__ == "__main__":
    asyncio.run(run())