import asyncio
import time
from sqlalchemy import select, update

from models.customer import Customer
from models.order import Order
from models.order_item import OrderItem
from services.closet_db import AsyncSessionLocal, init_closet_db
from services.vtex_oms_service import (
    fetch_order_detail,
    normalize_email,
    cents_to_float,
    parse_iso_datetime,
    to_str,
)

# ── Configurações ─────────────────────────────────────────────
BATCH_SIZE = 50          # Pedidos por lote antes de commitar
SLEEP_BETWEEN = 0.3      # Segundos entre chamadas à API VTEX
MAX_ERRORS = 20          # Para o job se errar demais seguido

# Domínios técnicos para identificar e-mails inválidos
DOMINIOS_INVALIDOS = (
    "@ct.vtex.com.br",
    "@act.vtex.com.br",
    "@vtex.com.br",
    "@marketplace.vtex.com.br",
)


def is_invalid_email(email: str) -> bool:
    if not email:
        return True
    email = str(email).lower().strip()
    return any(email.endswith(d) for d in DOMINIOS_INVALIDOS)


async def fetch_invalid_order_ids(session) -> list[str]:
    """Busca order_ids únicos com e-mail técnico da VTEX."""
    print("Buscando pedidos com e-mail inválido...", flush=True)

    result = await session.execute(
        select(OrderItem.order_id, OrderItem.email)
        .where(OrderItem.email.like("%ct.vtex.com.br"))
        .union(
            select(OrderItem.order_id, OrderItem.email)
            .where(OrderItem.email.like("%act.vtex.com.br"))
        )
        .distinct()
    )
    rows = result.fetchall()

    order_ids = list({row[0] for row in rows if row[0]})
    print(f"Encontrados {len(order_ids)} pedidos com e-mail inválido.", flush=True)
    return order_ids


async def update_order_email(session, order_id: str, real_email: str) -> bool:
    """
    Atualiza o e-mail em order_items, orders e customers
    para um pedido específico.
    """
    try:
        # Atualiza order_items
        await session.execute(
            update(OrderItem)
            .where(OrderItem.order_id == order_id)
            .values(email=real_email)
        )

        # Atualiza orders
        await session.execute(
            update(Order)
            .where(Order.order_id == order_id)
            .values(email=real_email)
        )

        # Garante que o customer existe
        customer = await session.get(Customer, real_email)
        if not customer:
            customer = Customer(email=real_email)
            session.add(customer)

        return True

    except Exception as e:
        print(f"  Erro ao atualizar order_id={order_id}: {e}", flush=True)
        return False


async def run():
    print("=" * 60, flush=True)
    print("fix_emails: iniciando correção de e-mails técnicos", flush=True)
    print("=" * 60, flush=True)

    await init_closet_db()

    async with AsyncSessionLocal() as session:
        # Busca pedidos com e-mail inválido
        order_ids = await fetch_invalid_order_ids(session)

        if not order_ids:
            print("Nenhum pedido com e-mail inválido encontrado. Banco já está correto!", flush=True)
            return

        total = len(order_ids)
        corrigidos = 0
        sem_email_real = 0
        erros = 0
        erros_seguidos = 0

        print(f"\nIniciando correção de {total} pedidos...\n", flush=True)

        for i, order_id in enumerate(order_ids, 1):
            try:
                # Busca detalhe do pedido na VTEX
                detail = fetch_order_detail(order_id)

                # Extrai e-mail real
                client = detail.get("clientProfileData") or {}
                raw_email = client.get("email") or ""
                real_email = normalize_email(raw_email)

                if not real_email:
                    # Pedido realmente não tem e-mail de cliente válido
                    sem_email_real += 1
                    if i % 500 == 0:
                        print(f"  [{i}/{total}] sem e-mail real ainda: {sem_email_real}", flush=True)
                    time.sleep(SLEEP_BETWEEN)
                    continue

                # Atualiza no banco
                success = await update_order_email(session, order_id, real_email)

                if success:
                    corrigidos += 1
                    erros_seguidos = 0

                    if corrigidos % 100 == 0:
                        await session.commit()
                        print(
                            f"  Checkpoint: {corrigidos} corrigidos | "
                            f"{sem_email_real} sem e-mail real | "
                            f"{i}/{total} processados",
                            flush=True,
                        )
                else:
                    erros += 1
                    erros_seguidos += 1

                time.sleep(SLEEP_BETWEEN)

                # Segurança: para se errar demais
                if erros_seguidos >= MAX_ERRORS:
                    print(f"ALERTA: {MAX_ERRORS} erros seguidos. Pausando para não sobrecarregar a API.", flush=True)
                    await session.commit()
                    time.sleep(30)
                    erros_seguidos = 0

            except Exception as e:
                erros += 1
                erros_seguidos += 1
                print(f"  ERRO order_id={order_id}: {e}", flush=True)
                time.sleep(SLEEP_BETWEEN * 3)

        # Commit final
        await session.commit()

        print("\n" + "=" * 60, flush=True)
        print("fix_emails: CONCLUÍDO", flush=True)
        print(f"  Total processados:     {total}", flush=True)
        print(f"  E-mails corrigidos:    {corrigidos}", flush=True)
        print(f"  Sem e-mail real:       {sem_email_real}", flush=True)
        print(f"  Erros:                 {erros}", flush=True)
        print("=" * 60, flush=True)

        if corrigidos > 0:
            print(f"\nSucesso! {corrigidos} pedidos agora têm e-mail real.", flush=True)
            print("Rode o job rebuild_customer_closets para atualizar os closets.", flush=True)


if __name__ == "__main__":
    asyncio.run(run())