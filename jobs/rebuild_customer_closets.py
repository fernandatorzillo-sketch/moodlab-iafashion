import asyncio
from datetime import datetime, timedelta, timezone

from sqlalchemy import text

from services.closet_db import AsyncSessionLocal, init_closet_db
from services.sync_control_service import mark_sync_error, mark_sync_success

JOB_NAME = "rebuild_customer_closets"
MONTHS_BACK = 24

IGNORED_STATUSES = (
    "canceled",
    "cancelado",
    "cancelled",
)


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


async def run() -> None:
    print("Iniciando rebuild_customer_closets SQL...", flush=True)
    await init_closet_db()

    cutoff = utcnow() - timedelta(days=30 * MONTHS_BACK)

    async with AsyncSessionLocal() as session:
        try:
            print(f"Cutoff: {cutoff.isoformat()}", flush=True)

            # 1. Limpa a tabela consolidada
            await session.execute(text("DELETE FROM customer_closet_items"))
            await session.commit()
            print("Tabela customer_closet_items limpa.", flush=True)

            # 2. Consolida usando catalog_products como fonte prioritária para atributos
            #    CORREÇÃO: filtro AND oi.email NOT LIKE '%vtex.com.br'
            #    garante que só e-mails reais de clientes entram no closet
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

                    COALESCE(MAX(cp.product_id), MAX(oi.product_id)) AS product_id,
                    COALESCE(MAX(cp.ref_id), MAX(oi.ref_id)) AS ref_id,

                    -- Nome: prefere catálogo (mais limpo) mas aceita order_item
                    COALESCE(MAX(cp.name), MAX(oi.name)) AS name,

                    -- Categoria e departamento VÊM DO CATÁLOGO (order_items não tem)
                    MAX(cp.category)   AS category,
                    MAX(cp.department) AS department,

                    COALESCE(MAX(cp.brand), MAX(oi.brand)) AS brand,

                    -- Imagem: corrige domínio lojaaguadecoco → aguadecoco na origem
                    REPLACE(
                        REPLACE(
                            COALESCE(MAX(cp.image_url), MAX(oi.image_url)),
                            'lojaaguadecoco.vteximg.com.br',
                            'aguadecoco.vteximg.com.br'
                        ),
                        'lojaaguadecoco.vtexassets.com',
                        'aguadecoco.vteximg.com.br'
                    ) AS image_url,

                    -- URL do produto: prefere catálogo (tem slug correto)
                    -- Garante URL absoluta: se começa com '/' adiciona domínio
                    CASE
                        WHEN MAX(cp.product_url) IS NOT NULL
                             AND MAX(cp.product_url) <> ''
                        THEN
                            CASE
                                WHEN MAX(cp.product_url) LIKE 'http%'
                                THEN MAX(cp.product_url)
                                ELSE 'https://www.aguadecoco.com.br' || MAX(cp.product_url)
                            END
                        WHEN MAX(oi.product_url) IS NOT NULL
                             AND MAX(oi.product_url) <> ''
                        THEN
                            CASE
                                WHEN MAX(oi.product_url) LIKE 'http%'
                                THEN MAX(oi.product_url)
                                ELSE 'https://www.aguadecoco.com.br' || MAX(oi.product_url)
                            END
                        ELSE NULL
                    END AS product_url,

                    COUNT(DISTINCT oi.order_id) AS purchase_count,
                    COALESCE(SUM(oi.quantity), 0) AS total_quantity,
                    COALESCE(SUM(oi.total_value), 0) AS total_spent,

                    MIN(o.creation_date) AS first_purchase_at,
                    MAX(o.creation_date) AS last_purchase_at,

                    NOW() AS created_at,
                    NOW() AS updated_at

                FROM order_items oi
                INNER JOIN orders o
                    ON o.order_id = oi.order_id

                -- INNER JOIN com catalog_products garante que só entram itens
                -- que existem no catálogo de moda (exclui Casa/Lifestyle
                -- automaticamente, pois esses produtos não são sincronizados)
                INNER JOIN catalog_products cp
                    ON cp.sku_id = oi.sku_id

                WHERE
                    o.creation_date >= :cutoff
                    AND oi.email IS NOT NULL
                    AND TRIM(oi.email) <> ''
                    AND oi.email NOT LIKE '%vtex.com.br'
                    AND COALESCE(LOWER(o.status), '') NOT IN ('canceled', 'cancelado', 'cancelled')
                    -- Exclui departamentos não-moda explicitamente (segurança extra)
                    AND COALESCE(LOWER(cp.department), '') NOT IN (
                        'casa', 'lifestyle', 'decor', 'decoracao', 'decoração',
                        'utilidades', 'cozinha', 'banheiro', 'quarto', 'sala'
                    )

                GROUP BY
                    oi.email,
                    oi.sku_id
            """)

            await session.execute(insert_sql, {"cutoff": cutoff})
            await session.commit()
            print("Insert consolidado concluído.", flush=True)

            # 3. Conta quantos itens ficaram no closet consolidado
            count_result = await session.execute(
                text("SELECT COUNT(*) FROM customer_closet_items")
            )
            inserted = count_result.scalar_one()

            # 4. Estatísticas úteis para log
            customer_count_result = await session.execute(
                text("SELECT COUNT(DISTINCT email) FROM customer_closet_items")
            )
            customer_count = customer_count_result.scalar_one()

            await mark_sync_success(
                session=session,
                job_name=JOB_NAME,
                reference_value=utcnow().isoformat(),
                notes=f"closet_items={inserted}; customers={customer_count}",
            )
            await session.commit()

            print(
                f"Rebuild SQL concluído: closet_items={inserted}, customers={customer_count}",
                flush=True,
            )

        except Exception as e:
            await session.rollback()
            print(f"Erro no rebuild SQL: {e}", flush=True)
            await mark_sync_error(session, JOB_NAME, notes=str(e))
            await session.commit()
            raise


if __name__ == "__main__":
    asyncio.run(run())