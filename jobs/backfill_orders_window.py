import asyncio
import os
from datetime import datetime, timezone

print("1. arquivo carregado")

from models.customer import Customer
from models.order import Order
from models.order_item import OrderItem
from services.closet_db import AsyncSessionLocal, init_closet_db
from services.vtex_oms_service import (
    cents_to_float,
    fetch_order_detail,
    fetch_order_summaries_by_creation_date,
    normalize_email,
    parse_iso_datetime,
    to_str,
)

print("2. imports concluídos")

PER_PAGE = 100
MAX_PAGES_PER_WINDOW = 100

IGNORED_STATUSES = {
    "cancelled",
    "canceled",
}


def get_env_required(name: str) -> str:
    print(f"3. lendo variável: {name}")
    value = os.getenv(name, "").strip()
    if not value:
        raise Exception(f"Variável obrigatória não configurada: {name}")
    print(f"3.1 variável ok: {name}={value}")
    return value


def parse_window_date(value: str) -> datetime:
    print(f"4. parseando data: {value}")
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


async def upsert_items(session, order_id: str, items: list) -> None:
    for item in items:
        order_item = OrderItem(
            order_id=order_id,
            sku_id=to_str(item.get("id")),
            quantity=item.get("quantity") or 1,
            price=cents_to_float(item.get("price")),
        )
        session.add(order_item)


async def process_window(date_from: str, date_to: str):
    print(f"5. iniciando process_window: {date_from} -> {date_to}")

    async with AsyncSessionLocal() as session:
        processed = 0
        ignored_canceled = 0

        for page in range(1, MAX_PAGES_PER_WINDOW + 1):
            print(f"6. consultando page={page}")

            summaries = fetch_order_summaries_by_creation_date(
                start_dt=parse_window_date(date_from),
                end_dt=parse_window_date(date_to),
                page=page,
                per_page=PER_PAGE,
            )

            orders = summaries.get("list", []) if isinstance(summaries, dict) else []
            if not orders:
                print("7. nenhuma ordem encontrada, encerrando")
                break

            print(f"8. page {page}: {len(orders)} pedido(s)")

            for summary in orders:
                order_id = summary.get("orderId")
                if not order_id:
                    continue

                try:
                    detail = fetch_order_detail(order_id)
                    if not detail:
                        print(f"9. detalhe vazio para {order_id}")
                        continue

                    status = to_str(detail.get("status")).lower()
                    if status in IGNORED_STATUSES:
                        ignored_canceled += 1
                        print(f"Pedido {order_id} com status '{status}' ignorado.")
                        continue

                    await upsert_customer(session, detail)
                    await upsert_order(session, detail)
                    await upsert_items(session, order_id, detail.get("items") or [])

                    processed += 1

                    if processed % 50 == 0:
                        print(f"10. checkpoint parcial: {processed}")
                        await session.commit()

                except Exception as e:
                    print(f"ERRO ao processar pedido {order_id}: {e}")

            await session.commit()

        print(
            f"11. backfill concluído com sucesso. processed_orders={processed}, "
            f"ignored_canceled={ignored_canceled}"
        )


async def main():
    print("🔥 MAIN INICIOU")
    await init_closet_db()
    print("🔥 banco inicializado")

    date_from = get_env_required("BACKFILL_START")
    date_to = get_env_required("BACKFILL_END")

    await process_window(date_from, date_to)


if __name__ == "__main__":
    print("12. chamando asyncio.run(main())")
    asyncio.run(main())