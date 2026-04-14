import asyncio
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select

from models.customer_closet_item import CustomerClosetItem
from models.order import Order
from models.order_item import OrderItem
from services.closet_db import AsyncSessionLocal, init_closet_db
from services.sync_control_service import mark_sync_error, mark_sync_success

JOB_NAME = "rebuild_customer_closets"
MONTHS_BACK = 24


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


async def run() -> None:
    await init_closet_db()

    cutoff = utcnow() - timedelta(days=30 * MONTHS_BACK)

    async with AsyncSessionLocal() as session:
        try:
            result = await session.execute(
                select(OrderItem, Order)
                .join(Order, Order.order_id == OrderItem.order_id)
                .where(Order.creation_date >= cutoff)
            )

            rows = result.all()
            print(f"Linhas order_items encontradas para rebuild: {len(rows)}")

            aggregated = {}

            for order_item, order in rows:
                email = (order.email or "").strip().lower()
                if not email:
                    continue

                status = (order.status or "").strip().lower()
                if status in {"canceled", "cancelado"}:
                    continue

                unique_key = (
                    email,
                    order_item.sku_id or order_item.product_id or order_item.ref_id or order_item.name or "unknown",
                )

                if unique_key not in aggregated:
                    aggregated[unique_key] = {
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
                        "purchase_count": 0,
                        "total_quantity": 0,
                        "total_spent": 0.0,
                        "first_purchase_at": order.creation_date,
                        "last_purchase_at": order.creation_date,
                    }

                row = aggregated[unique_key]
                row["purchase_count"] += 1
                row["total_quantity"] += int(order_item.quantity or 0)
                row["total_spent"] += float(order_item.total_value or 0)

                if order.creation_date:
                    if not row["first_purchase_at"] or order.creation_date < row["first_purchase_at"]:
                        row["first_purchase_at"] = order.creation_date
                    if not row["last_purchase_at"] or order.creation_date > row["last_purchase_at"]:
                        row["last_purchase_at"] = order.creation_date

                if not row["image_url"] and order_item.image_url:
                    row["image_url"] = order_item.image_url

                if not row["product_url"] and order_item.product_url:
                    row["product_url"] = order_item.product_url

            await session.execute(delete(CustomerClosetItem))

            inserted = 0
            for item in aggregated.values():
                session.add(
                    CustomerClosetItem(
                        email=item["email"],
                        sku_id=item["sku_id"],
                        product_id=item["product_id"],
                        ref_id=item["ref_id"],
                        name=item["name"],
                        category=item["category"],
                        department=item["department"],
                        brand=item["brand"],
                        image_url=item["image_url"],
                        product_url=item["product_url"],
                        purchase_count=item["purchase_count"],
                        total_quantity=item["total_quantity"],
                        total_spent=item["total_spent"],
                        first_purchase_at=item["first_purchase_at"],
                        last_purchase_at=item["last_purchase_at"],
                    )
                )
                inserted += 1

                if inserted % 500 == 0:
                    await session.commit()
                    print(f"Checkpoint rebuild closet: {inserted} linhas")

            await mark_sync_success(
                session=session,
                job_name=JOB_NAME,
                reference_value=utcnow().isoformat(),
                notes=f"rows={len(rows)};closet_items={inserted}",
            )
            await session.commit()

            print(f"Rebuild concluído. closet_items={inserted}")

        except Exception as e:
            await session.rollback()
            await mark_sync_error(session, JOB_NAME, notes=str(e))
            await session.commit()
            raise


if __name__ == "__main__":
    asyncio.run(run())