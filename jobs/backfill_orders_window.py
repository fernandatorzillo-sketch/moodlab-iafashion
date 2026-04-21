import asyncio
import os
from datetime import datetime, timezone

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
    order.status = to_str(detail.get("