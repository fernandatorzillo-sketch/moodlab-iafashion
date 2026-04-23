import asyncio
import time

from sqlalchemy import select, update

from models.customer import Customer
from models.order import Order
from models.order_item import OrderItem
from services.closet_db import AsyncSessionLocal, init_closet_db
from services.vtex_oms_service import fetch_order_detail, normalize_email

BATCH_SIZE = 100
SLEEP_BETWEEN = 0.3


async def fetch_invalid_order_ids(session) -> list[str]:
    """Busca order_ids únicos com e-mail técnico da VTEX."""
    print("Buscando pedidos com e-mail inválido...", flush=True)

    result = await session.execute(
        select(OrderItem.order_id)
        .where(
            OrderItem.order_id.is_not(None),
            OrderItem.email.like("%vtex.com.br"),
        )
        .distinct()
    )
    rows = result.fetchall()
    order_ids = list({row[0] for row in rows if row[0]})
    print(f"Encontrados {len(order_ids)} pedidos com e-mail inválido.", flush=True)
    return order_ids


async def process_single_order(order_id: str, real_email: str) -> bool:
    """
    Sessão ISOLADA por pedido.
    Um erro num pedido não trava os próximos.
    """
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(
                update(OrderItem)
                .where(OrderItem.order_id == order_id)
                .values(email=real_email)
            )
            await session.execute(
                update(Order)
                .where(Order.order_id == order_id)
                .values(email=real_email)
            )
            customer = await session.get(Customer, real_email)
            if not customer:
                customer = Customer(email=real_email)
                session.add(customer)
            await session.commit()
            return True
    except Exception as e:
        print(f"  Erro sessão order_id={order_id}: {e}", flush=True)
        return False


async def run():
    print("=" * 60, flush=True)
    print("fix_emails: iniciando correção de e-mails técnicos", flush=True)
    print("=" * 60, flush=True)

    await init_closet_db()

    # Busca IDs inválidos numa sessão separada e fecha logo
    async with AsyncSessionLocal() as session:
        order_ids = await fetch_invalid_order_ids(session)

    if not order_ids:
        print("Nenhum pedido com e-mail inválido. Banco já está correto!", flush=True)
        return

    total = len(order_ids)
    corrigidos = 0
    sem_email_real = 0
    erros = 0

    print(f"\nIniciando correção de {total} pedidos...\n", flush=True)

    for i, order_id in enumerate(order_ids, 1):
        try:
            detail = fetch_order_detail(order_id)
            client = detail.get("clientProfileData") or {}
            raw_email = client.get("email") or ""
            real_email = normalize_email(raw_email)

            if not real_email:
                sem_email_real += 1
                time.sleep(SLEEP_BETWEEN)
                continue

            success = await process_single_order(order_id, real_email)

            if success:
                corrigidos += 1
            else:
                erros += 1

            if corrigidos > 0 and corrigidos % BATCH_SIZE == 0:
                print(
                    f"  Checkpoint: {corrigidos} corrigidos | "
                    f"{sem_email_real} sem e-mail real | "
                    f"{i}/{total} processados",
                    flush=True,
                )

            time.sleep(SLEEP_BETWEEN)

        except Exception as e:
            erros += 1
            print(f"  ERRO order_id={order_id}: {e}", flush=True)
            time.sleep(SLEEP_BETWEEN * 2)

    print("\n" + "=" * 60, flush=True)
    print("fix_emails: CONCLUÍDO", flush=True)
    print(f"  Total processados:     {total}", flush=True)
    print(f"  E-mails corrigidos:    {corrigidos}", flush=True)
    print(f"  Sem e-mail real:       {sem_email_real}", flush=True)
    print(f"  Erros:                 {erros}", flush=True)
    print("=" * 60, flush=True)

    if corrigidos > 0:
        print(f"\nSucesso! {corrigidos} pedidos corrigidos.", flush=True)
        print("Próximo passo: python -m jobs.rebuild_customer_closets", flush=True)


if __name__ == "__main__":
    asyncio.run(run())