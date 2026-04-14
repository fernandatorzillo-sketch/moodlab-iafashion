import asyncio
from datetime import datetime, timedelta, timezone

from sqlalchemy import text

from services.closet_db import AsyncSessionLocal, init_closet_db
from services.sync_control_service import mark_sync_error, mark_sync_success

JOB_NAME = "rebuild_customer_closets"
MONTHS_BACK = 24


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


async def run() -> None:
    print("Iniciando rebuild_customer_closets SQL...", flush=True)
    await init_closet_db()

    cutoff = utcnow() - timedelta(days=30 * MONTHS_BACK)

    async with AsyncSessionLocal() as session:
        try:
            print(f"Cutoff: {cutoff.isoformat()}", flush=True)

            # Limpa a tabela consolidada
            await session.execute(text("DELETE FROM customer_closet_items"))
            await session.commit()
            print("Tabela customer_closet_items limpa.", flush=True)

            insert_sql = text("""
                INSERT INTO customer_closet_items (
                    email,
                    sku_id,
                    product_id,
                    ref_id,
                    name,
                    category,
                    department,
                    brand,
                    image_url,
                    product_url,
                    purchase_count,
                    total_quantity,
                    total_spent,
                    first_purchase_at,
                    last_purchase_at,
                    created_at,
                    updated_at
                )
                SELECT
                    oi.email AS email,
                    oi.sku_id AS sku_id,
                    MAX(oi.product_id) AS product_id,
                    MAX(oi.ref_id) AS ref_id,
                    MAX(oi.name) AS name,
                    MAX(oi.category) AS category,
                    MAX(oi.department) AS department,
                    MAX(oi.brand) AS brand,
                    MAX(oi.image_url) AS image_url,
                    MAX(oi.product_url) AS product_url,
                    COUNT(*) AS purchase_count,
                    COALESCE(SUM(oi.quantity), 0) AS total_quantity,
                    COALESCE(SUM(oi.total_value), 0) AS total_spent,
                    MIN(o.creation_date) AS first_purchase_at,
                    MAX(o.creation_date) AS last_purchase_at,
                    NOW() AS created_at,
                    NOW() AS updated_at
                FROM order_items oi
                INNER JOIN orders o
                    ON o.order_id = oi.order_id
                WHERE
                    o.creation_date >= :cutoff
                    AND oi.email IS NOT NULL
                    AND oi.email <> ''
                    AND COALESCE(LOWER(o.status), '') NOT IN ('canceled', 'cancelado')
                GROUP BY
                    oi.email,
                    oi.sku_id
            """)

            await session.execute(insert_sql, {"cutoff": cutoff})
            await session.commit()
            print("Insert consolidado concluído.", flush=True)

            count_result = await session.execute(
                text("SELECT COUNT(*) FROM customer_closet_items")
            )
            inserted = count_result.scalar_one()

            await mark_sync_success(
                session=session,
                job_name=JOB_NAME,
                reference_value=utcnow().isoformat(),
                notes=f"closet_items={inserted}",
            )
            await session.commit()

            print(f"Rebuild SQL concluído: {inserted}", flush=True)

        except Exception as e:
            await session.rollback()
            print(f"Erro no rebuild SQL: {e}", flush=True)
            await mark_sync_error(session, JOB_NAME, notes=str(e))
            await session.commit()
            raise


if __name__ == "__main__":
    asyncio.run(run())