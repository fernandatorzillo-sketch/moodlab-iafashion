print("1. entrou no arquivo")

print("2. importando asyncio/os/datetime...")
import asyncio
import os
from datetime import datetime, timezone
print("2 ok")

print("3. importando models...")
from models.customer import Customer
print("3.1 customer ok")
from models.order import Order
print("3.2 order ok")
from models.order_item import OrderItem
print("3.3 order_item ok")

print("4. importando closet_db...")
from services.closet_db import AsyncSessionLocal, init_closet_db
print("4 ok")

print("5. importando vtex_oms_service...")
from services.vtex_oms_service import (
    cents_to_float,
    fetch_order_detail,
    fetch_order_summaries_by_creation_date,
    normalize_email,
    parse_iso_datetime,
    to_str,
)
print("5 ok")

print("6. terminou todos os imports com sucesso")