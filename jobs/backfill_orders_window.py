import asyncio
import os
from datetime import datetime, timezone

from services.closet_db import AsyncSessionLocal, init_closet_db
from services.vtex_oms_service import (
    fetch_order_summaries_by_creation_date,
    fetch_order_detail,
    normalize_email,
    parse_iso_datetime,
    to_str,
    cents_to_float,
)
from models.customer import Customer
from models.order import Order
from models.order_item import OrderItem


PER_PAGE = 100
MAX_PAGES_PER_WINDOW = 100


def get_env_required(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise Exception(f"Variável obrigatória não configurada: {name}")
    return value


def parse_window_date(value: str) -> datetime:
    dt = parse_iso_datetime(value)
    if not dt:
        raise Exception(f"Data inválida: {value}")
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


async def upsert_customer(session, detail: dict) -> None:
    client = detail.get("clientProfileData") or {}
    email = normalize_email(client.get("email"))

    if not email:
        return

    customer = await session.get(Customer, email)

    first_name = str(client.get("firstName") or "").strip()
    last_name = str(client.get("lastName") or "").strip()
    full_name = f"{first_name} {last_name}".strip() or email.split("@")[0]

    if not customer:
        customer = Customer(email=email)
        session.add(customer)

    customer.first_name = first_name or None
    customer.last_name = last_name or None
    customer.full_name = full_name


async def upsert_order(session, detail: dict) -> None:
    order_id = to_str(detail.get("orderId"))
    if not order_id:
        return

    client = detail.get("clientProfileData") or {}
    email = normalize_email(client.get("email"))

    first_name = str(client.get("firstName") or "").strip()
    last_name = str(client.get("lastName") or "").strip()
    customer_name = f"{first_name} {last_name}".strip() or (email.split("@")[0] if email else None)

    order = await session.get(Order, order_id)
    if not order:
        order = Order(order_id=order_id)
        session.add(order)

    order.sequence = to_str(detail.get("sequence")) or None
    order.email = email or None
    order.status = to_str(detail.get("status")) or None
    order.creation_date = parse_iso_datetime(detail.get("creationDate"))
    order.last_change = parse_iso_datetime(detail.get("lastChange"))
    order.total_value = cents_to_float(detail.get("value"))
    order.currency_code = to_str((detail.get("storePreferencesData") or {}).get("currencyCode")) or "BRL"
    order.customer_name = customer_name
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
            vals = [v for v in categories.values() if v]
            if vals:
                category = vals[-1]

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


async def process_order(session, order_id: str) -> None:
    detail = fetch_order_detail(order_id)
    await upsert_customer(session, detail)
    await upsert_order(session, detail)
    await replace_order_items(session, detail)


async def run():
    start_raw = get_env_required("BACKFILL_START")
    end_raw = get_env_required("BACKFILL_END")

    start_dt = parse_window_date(start_raw)
    end_dt = parse_window_date(end_raw)

    print(f"Iniciando backfill por janela...", flush=True)
    print(f"Janela: {start_dt.isoformat()} -> {end_dt.isoformat()}", flush=True)

    await init_closet_db()

    processed_orders = 0
    seen_order_ids = set()

    async with AsyncSessionLocal() as session:
        for page in range(1, MAX_PAGES_PER_WINDOW + 1):
            print(f"Consultando page={page}...", flush=True)

            payload = fetch_order_summaries_by_creation_date(
                start_dt=start_dt,
                end_dt=end_dt,
                page=page,
                per_page=PER_PAGE,
            )

            orders = payload.get("list", []) or []
            if not orders:
                print(f"Page {page}: 0 pedidos", flush=True)
                break

            print(f"Page {page}: {len(orders)} pedido(s)", flush=True)

            for summary in orders:
                order_id = to_str(summary.get("orderId"))
                if not order_id or order_id in seen_order_ids:
                    continue

                seen_order_ids.add(order_id)
                await process_order(session, order_id)
                processed_orders += 1

                if processed_orders % 50 == 0:
                    await session.commit()
                    print(f"Checkpoint parcial: {processed_orders} pedidos processados", flush=True)

            await session.commit()

            if len(orders) < PER_PAGE:
                break

    print(f"Backfill concluído com sucesso. processed_orders={processed_orders}", flush=True)


if __name__ == "__main__":
    asyncio.run(run())