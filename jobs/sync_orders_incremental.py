import asyncio
from datetime import datetime, timedelta, timezone

from models.customer import Customer
from models.order import Order
from models.order_item import OrderItem
from services.closet_db import AsyncSessionLocal, init_closet_db
from services.sync_control_service import (
    get_last_reference_value,
    mark_sync_error,
    mark_sync_success,
)
from services.vtex_oms_service import (
    cents_to_float,
    fetch_order_detail,
    fetch_order_summaries_by_creation_date,
    normalize_email,
    parse_iso_datetime,
    to_str,
)

JOB_NAME = "orders_incremental"
INITIAL_MONTHS_BACK = 24
CHUNK_DAYS = 3
PER_PAGE = 100
MAX_PAGES_PER_CHUNK = 100
OVERLAP_HOURS = 2


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def dt_to_iso(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat()


def chunk_ranges(start_dt: datetime, end_dt: datetime, days: int):
    current = start_dt
    while current < end_dt:
        chunk_end = min(current + timedelta(days=days), end_dt)
        yield current, chunk_end
        current = chunk_end


async def upsert_customer(session, detail: dict) -> None:
    client = detail.get("clientProfileData") or {}
    email = normalize_email(client.get("email"))

    if not email:
        return

    customer = await session.get(Customer, email)
    full_name = " ".join(
        [
            str(client.get("firstName") or "").strip(),
            str(client.get("lastName") or "").strip(),
        ]
    ).strip()

    if not customer:
        customer = Customer(email=email)
        session.add(customer)

    customer.first_name = client.get("firstName")
    customer.last_name = client.get("lastName")
    customer.full_name = full_name or email.split("@")[0]


async def upsert_order(session, detail: dict) -> None:
    order_id = to_str(detail.get("orderId"))
    if not order_id:
        return

    client = detail.get("clientProfileData") or {}
    email = normalize_email(client.get("email"))
    customer_name = " ".join(
        [
            str(client.get("firstName") or "").strip(),
            str(client.get("lastName") or "").strip(),
        ]
    ).strip()

    order = await session.get(Order, order_id)
    if not order:
        order = Order(order_id=order_id)
        session.add(order)

    order.sequence = to_str(detail.get("sequence"))
    order.email = email or None
    order.status = to_str(detail.get("status")) or None
    order.creation_date = parse_iso_datetime(detail.get("creationDate"))
    order.last_change = parse_iso_datetime(detail.get("lastChange"))
    order.total_value = cents_to_float(detail.get("value"))
    order.currency_code = to_str(detail.get("storePreferencesData", {}).get("currencyCode")) or "BRL"
    order.customer_name = customer_name or (email.split("@")[0] if email else None)
    order.raw_json = detail


async def replace_order_items(session, detail: dict) -> None:
    order_id = to_str(detail.get("orderId"))
    if not order_id:
        return

    client = detail.get("clientProfileData") or {}
    email = normalize_email(client.get("email"))
    created_at_order = parse_iso_datetime(detail.get("creationDate"))

    await session.execute(
        OrderItem.__table__.delete().where(OrderItem.order_id == order_id)
    )

    items = detail.get("items") or []
    for item in items:
        additional_info = item.get("additionalInfo") or {}
        categories = item.get("productCategories") or {}

        category = None
        if isinstance(categories, dict) and categories:
            values = [v for v in categories.values() if v]
            if values:
                category = values[-1]

        quantity = int(item.get("quantity") or 0)
        price = cents_to_float(item.get("price"))
        total_value = round(price * quantity, 2)

        row = OrderItem(
            order_id=order_id,
            email=email or None,
            sku_id=to_str(item.get("id")) or None,
            product_id=to_str(item.get("productId")) or None,
            ref_id=to_str(additional_info.get("productRefId") or item.get("refId")) or None,
            name=to_str(item.get("name")) or None,
            category=category,
            department=None,
            brand=to_str(additional_info.get("brandName")) or None,
            quantity=quantity,
            price=price,
            total_value=total_value,
            image_url=to_str(item.get("imageUrl")) or None,
            product_url=None,
            created_at_order=created_at_order,
            raw_json=item,
        )
        session.add(row)


async def process_order_detail(session, order_id: str) -> None:
    detail = fetch_order_detail(order_id)
    await upsert_customer(session, detail)
    await upsert_order(session, detail)
    await replace_order_items(session, detail)


async def run() -> None:
    print("Iniciando sync_orders_incremental...", flush=True)
    await init_closet_db()
    print("Banco inicializado.", flush=True)

    async with AsyncSessionLocal() as session:
        try:
            last_reference = await get_last_reference_value(session, JOB_NAME)
            print(f"last_reference={last_reference}", flush=True)

            if last_reference:
                start_dt = parse_iso_datetime(last_reference)
                if not start_dt:
                    start_dt = utcnow() - timedelta(days=30 * INITIAL_MONTHS_BACK)
                start_dt = start_dt.replace(tzinfo=timezone.utc) - timedelta(hours=OVERLAP_HOURS)
            else:
                start_dt = utcnow() - timedelta(days=30 * INITIAL_MONTHS_BACK)

            end_dt = utcnow()

            processed_orders = 0
            processed_chunks = 0

            print(f"Janela total: {start_dt.isoformat()} -> {end_dt.isoformat()}", flush=True)

            for chunk_start, chunk_end in chunk_ranges(start_dt, end_dt, CHUNK_DAYS):
                processed_chunks += 1
                print(
                    f"Chunk {processed_chunks}: {chunk_start.isoformat()} -> {chunk_end.isoformat()}",
                    flush=True,
                )

                seen_order_ids = set()

                for page in range(1, MAX_PAGES_PER_CHUNK + 1):
                    print(f"Consultando chunk={processed_chunks} page={page}...", flush=True)

                    payload = fetch_order_summaries_by_creation_date(
                        start_dt=chunk_start,
                        end_dt=chunk_end,
                        page=page,
                        per_page=PER_PAGE,
                    )
                    orders = payload.get("list", []) or []

                    if not orders:
                        print(f"Chunk {processed_chunks} page {page}: 0 pedidos", flush=True)
                        break

                    print(
                        f"Chunk {processed_chunks} page {page}: {len(orders)} pedido(s)",
                        flush=True,
                    )

                    for summary in orders:
                        order_id = to_str(summary.get("orderId"))
                        if not order_id or order_id in seen_order_ids:
                            continue

                        seen_order_ids.add(order_id)
                        await process_order_detail(session, order_id)
                        processed_orders += 1

                        if processed_orders % 50 == 0:
                            await session.commit()
                            print(
                                f"Checkpoint parcial: {processed_orders} pedidos processados",
                                flush=True,
                            )

                    if len(orders) < PER_PAGE:
                        break

                await session.commit()
                print(f"Chunk {processed_chunks} concluído.", flush=True)

            await mark_sync_success(
                session=session,
                job_name=JOB_NAME,
                reference_value=dt_to_iso(end_dt),
                notes=f"processed_orders={processed_orders};chunks={processed_chunks}",
            )
            await session.commit()

            print(f"Finalizado com sucesso. processed_orders={processed_orders}", flush=True)

        except Exception as e:
            await session.rollback()
            print(f"Erro no sync_orders_incremental: {e}", flush=True)
            await mark_sync_error(session, JOB_NAME, notes=str(e))
            await session.commit()
            raise


if __name__ == "__main__":
    asyncio.run(run())