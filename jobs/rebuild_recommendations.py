import asyncio
from collections import defaultdict

from sqlalchemy import delete, select

from models.catalog_product import CatalogProduct
from models.customer_closet_item import CustomerClosetItem
from models.customer_questionnaire_answer import CustomerQuestionnaireAnswer
from models.customer_recommendation import CustomerRecommendation
from models.inventory_by_sku import InventoryBySku

from services.closet_db import AsyncSessionLocal, init_closet_db
from services.sync_control_service import mark_sync_error, mark_sync_success
from services.recommendation_engine import build_recommendations

JOB_NAME = "rebuild_recommendations"

EMAIL_BATCH_SIZE = 100
RECOMMENDATION_LIMIT = 12


async def fetch_email_batch(session, offset: int, limit: int):
    result = await session.execute(
        select(CustomerClosetItem.email)
        .where(CustomerClosetItem.email.is_not(None))
        .distinct()
        .order_by(CustomerClosetItem.email)
        .offset(offset)
        .limit(limit)
    )
    return [row[0] for row in result.fetchall() if row[0]]


async def fetch_closet_batch(session, emails):
    result = await session.execute(
        select(CustomerClosetItem).where(CustomerClosetItem.email.in_(emails))
    )
    rows = result.scalars().all()

    data = defaultdict(list)
    for r in rows:
        data[r.email].append(
            {
                # ── Identifiers ──────────────────────────────────────────
                "sku_id":       r.sku_id,
                "product_id":   r.product_id,
                "ref_id":       r.ref_id,

                # ── Campos no formato esperado pelo recommendation_engine ─
                "nome":         r.name,          # engine usa "nome"
                "name":         r.name,          # fallback
                "categoria":    r.category,      # engine usa "categoria"
                "category":     r.category,      # fallback
                "departamento": r.department,    # engine usa "departamento"
                "department":   r.department,    # fallback
                "cor":          getattr(r, "color", ""),   # engine usa "cor"
                "color":        getattr(r, "color", ""),   # fallback
                "colecao":      getattr(r, "collection", ""),
                "estilo":       getattr(r, "style", ""),

                # ── Campos extras ────────────────────────────────────────
                "brand":        r.brand,
                "imagem_url":   r.image_url,
                "image_url":    r.image_url,
                "link_produto": r.product_url,
                "product_url":  r.product_url,
                "product_type": getattr(r, "product_type", ""),
                "occasion":     getattr(r, "occasion", ""),
                "ocasiao":      getattr(r, "occasion", ""),
                "estamparia":   getattr(r, "estamparia", ""),
                "size":         getattr(r, "size", ""),
                "stock_quantity": 1,
                "in_stock":     True,
            }
        )
    return data


async def fetch_answers_batch(session, emails):
    result = await session.execute(
        select(CustomerQuestionnaireAnswer).where(
            CustomerQuestionnaireAnswer.email.in_(emails)
        )
    )
    rows = result.scalars().all()

    return {
        r.email: {
            # ── Campos no formato esperado pelo recommendation_engine ─
            "objetivo":  r.goal,      # engine usa "objetivo"
            "goal":      r.goal,      # fallback
            "ocasiao":   r.occasion,  # engine usa "ocasiao"
            "occasion":  r.occasion,  # fallback
            "estilo":    r.style,     # engine usa "estilo"
            "style":     r.style,     # fallback
        }
        for r in rows
    }


async def fetch_catalog(session):
    result = await session.execute(
        select(CatalogProduct, InventoryBySku)
        .join(InventoryBySku, InventoryBySku.sku_id == CatalogProduct.sku_id)
        .where(
            CatalogProduct.is_active == 1,
            InventoryBySku.is_available == 1,
            InventoryBySku.quantity > 0,
        )
    )

    rows = result.all()

    catalog = []
    seen_skus = set()

    for product, inventory in rows:
        sku_id = str(product.sku_id or "").strip()
        if not sku_id:
            continue

        # Evita repetir o mesmo SKU se houver múltiplos warehouses
        if sku_id in seen_skus:
            continue
        seen_skus.add(sku_id)

        catalog.append(
            {
                # ── Identifiers ──────────────────────────────────────────
                "sku_id":       product.sku_id,
                "product_id":   product.product_id,
                "ref_id":       product.ref_id,

                # ── Campos no formato esperado pelo recommendation_engine ─
                "nome":         product.name,        # engine usa "nome"
                "name":         product.name,        # fallback
                "categoria":    product.category,    # engine usa "categoria"
                "category":     product.category,    # fallback
                "departamento": product.department,  # engine usa "departamento"
                "department":   product.department,  # fallback
                "cor":          getattr(product, "color", ""),  # engine usa "cor"
                "color":        getattr(product, "color", ""),  # fallback
                "colecao":      getattr(product, "collection", ""),
                "estilo":       getattr(product, "style", ""),

                # ── Campos extras ────────────────────────────────────────
                "imagem_url":   product.image_url,
                "image_url":    product.image_url,
                "link_produto": product.product_url,
                "product_url":  product.product_url,
                "product_type": product.product_type,
                "occasion":     product.occasion,
                "ocasiao":      product.occasion,
                "estamparia":   getattr(product, "print_name", ""),
                "price":        getattr(product, "price", 0) or 0,
                "stock_quantity": int(inventory.quantity or 0),
                "in_stock":     int(inventory.quantity or 0) > 0,
            }
        )

    return catalog


async def run():
    await init_closet_db()

    async with AsyncSessionLocal() as session:
        try:
            print("1. Limpando recomendações antigas...", flush=True)
            await session.execute(delete(CustomerRecommendation))
            await session.commit()

            print("2. Carregando catálogo com estoque...", flush=True)
            catalog = await fetch_catalog(session)
            print(f"2.1 Catálogo carregado: {len(catalog)} produtos elegíveis", flush=True)

            if not catalog:
                print("AVISO: catálogo vazio! Verifique se os produtos estão ativos e com estoque.", flush=True)
                return

            if catalog:
                print(f"2.2 Exemplo de item do catálogo: {catalog[0]}", flush=True)

            inserted = 0
            offset = 0
            batch = 0

            while True:
                batch += 1
                emails = await fetch_email_batch(session, offset, EMAIL_BATCH_SIZE)

                if not emails:
                    print("3. Nenhum cliente restante para processar. Encerrando.", flush=True)
                    break

                print(
                    f"4. Lote {batch} | clientes={len(emails)} | offset={offset}",
                    flush=True,
                )

                closet_map = await fetch_closet_batch(session, emails)
                answers_map = await fetch_answers_batch(session, emails)

                for idx, email in enumerate(emails):
                    closet = closet_map.get(email, [])
                    if not closet:
                        continue

                    answers = answers_map.get(email, {})

                    # DEBUG: primeiros lotes para verificar dados
                    if batch <= 2 and idx < 3:
                        print(f"DEBUG email={email}", flush=True)
                        print(f"DEBUG closet_count={len(closet)}", flush=True)
                        print(f"DEBUG answers={answers}", flush=True)
                        print(f"DEBUG closet_sample={closet[0]}", flush=True)

                    result = build_recommendations(
                        closet_products=closet,
                        catalog=catalog,
                        answers=answers,
                        limit=RECOMMENDATION_LIMIT,
                    )

                    recs = result["recommendations"]

                    if batch <= 2 and idx < 3:
                        print(f"DEBUG rec_count={len(recs)}", flush=True)
                        print(f"DEBUG profile={result.get('profile')}", flush=True)

                    for r in recs:
                        session.add(
                            CustomerRecommendation(
                                email=email,
                                sku_id=r.get("sku_id"),
                                product_id=r.get("produto_id") or r.get("product_id"),
                                ref_id=r.get("ref_id"),
                                name=r.get("nome") or r.get("name"),
                                category=r.get("categoria") or r.get("category"),
                                department=r.get("departamento") or r.get("department"),
                                image_url=r.get("imagem_url") or r.get("image_url"),
                                product_url=r.get("link_produto") or r.get("product_url"),
                                reason=r.get("motivo") or r.get("reason"),
                                recommendation_type=str(
                                    answers.get("objetivo") or answers.get("goal") or "engine"
                                ).strip().lower() or "engine",
                                score=float(r.get("score", 0)),
                            )
                        )
                        inserted += 1

                    if inserted > 0 and inserted % 200 == 0:
                        print(f"Checkpoint: {inserted}", flush=True)
                        await session.commit()

                await session.commit()
                print(
                    f"5. Lote {batch} concluído | total inserido até agora={inserted}",
                    flush=True,
                )

                offset += EMAIL_BATCH_SIZE

            print(f"6. Marcando sucesso. Total inserido: {inserted}", flush=True)
            await mark_sync_success(
                session=session,
                job_name=JOB_NAME,
                reference_value=str(inserted),
                notes=f"recommendations={inserted}",
            )
            await session.commit()

            print(f"rebuild_recommendations concluído: {inserted} recomendações geradas.", flush=True)

        except Exception as e:
            print(f"ERRO no rebuild_recommendations: {e}", flush=True)
            await session.rollback()
            await mark_sync_error(session, JOB_NAME, notes=str(e))
            await session.commit()
            raise


if __name__ == "__main__":
    asyncio.run(run())