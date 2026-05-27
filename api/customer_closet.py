import json
import os
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from services.customer_closet_service import get_customer_closet_payload
from services.recommendation_service import get_customer_recommendations

router = APIRouter(prefix="/api/v1/customer-closet", tags=["customer-closet"])


class LookupRequest(BaseModel):
    email: str


class RecommendationRequest(BaseModel):
    email: str
    answers: dict[str, Any] = {}
    limit: int = 8


class StylistChatRequest(BaseModel):
    email: str
    message: str
    page_context: str = ""
    limit: int = 6


@router.post("/stylist-chat")
async def stylist_chat(payload: StylistChatRequest):
    """Personal shopper público com IA."""
    import re as _re
    import os as _os

    email = normalize_email(payload.email)
    if not email:
        raise HTTPException(status_code=400, detail="E-mail é obrigatório")
    message = str(payload.message or "").strip()
    if not message:
        raise HTTPException(status_code=400, detail="Mensagem é obrigatória")
    limit = max(2, min(int(payload.limit or 6), 8))

    # ── 1. Perfil da cliente (leve — só counters) ──────────────────────────
    client_name = email.split("@")[0]
    profile_text = ""
    tops_in_closet = []

    try:
        from services.closet_db import AsyncSessionLocal
        from sqlalchemy import text as _txt

        async with AsyncSessionLocal() as db:
            # Nome
            r = await db.execute(_txt(
                "SELECT name FROM customers WHERE email=:e LIMIT 1"
            ), {"e": email})
            row = r.fetchone()
            if row and row[0]:
                client_name = row[0].split()[0]

            # Perfil agregado do closet
            r2 = await db.execute(_txt("""
                SELECT
                  cp.color, cp.size, cp.print_name, cp.collection,
                  cci.name, cp.category
                FROM customer_closet_items cci
                LEFT JOIN catalog_products cp ON cp.sku_id = cci.sku_id
                WHERE cci.email = :e
                ORDER BY cci.purchase_count DESC
                LIMIT 30
            """), {"e": email})
            rows = r2.fetchall()

            from collections import Counter
            colors, sizes, prints, cats, colls = Counter(), Counter(), Counter(), Counter(), Counter()
            for color, size, print_name, coll, name, cat in rows:
                if color: colors[color.lower()] += 1
                if size:  sizes[size.upper()] += 1
                if print_name: prints[print_name.lower()] += 1
                if cat:   cats[cat.lower()] += 1
                if coll:  colls[coll.lower()] += 1
                if name:
                    n = name.lower()
                    if any(t in n for t in ["sutiã","sutia","top ","cropped","frente única","bandeau","faixa"]):
                        tops_in_closet.append({"name": name, "collection": coll or ""})

            parts = []
            if colors:  parts.append(f"Cores favoritas: {', '.join(c for c,_ in colors.most_common(4))}")
            if sizes:   parts.append(f"Tamanhos: {', '.join(s for s,_ in sizes.most_common(2))}")
            if cats:    parts.append(f"Categorias mais compradas: {', '.join(c for c,_ in cats.most_common(3))}")
            if colls:   parts.append(f"Coleções favoritas: {', '.join(c for c,_ in colls.most_common(2))}")
            if tops_in_closet:
                tops_str = ", ".join(t["name"] for t in tops_in_closet[:2])
                parts.append(f"Tops/sutiãs no closet (sugerir calcinhas do mesmo mix): {tops_str}")
            profile_text = "\n".join(parts)
    except Exception:
        pass  # Sem perfil — IA funciona mesmo assim

    # ── 2. Catálogo (query simples, sem JOIN pesado) ───────────────────────
    catalog_products = []
    try:
        from services.closet_db import AsyncSessionLocal
        from sqlalchemy import text as _txt2

        async with AsyncSessionLocal() as db:
            r3 = await db.execute(_txt2("""
                SELECT cp.product_id, cp.name, cp.price,
                       cp.category, cp.image_url, cp.product_url,
                       cp.color, cp.collection
                FROM catalog_products cp
                INNER JOIN inventory_by_sku inv ON inv.sku_id = cp.sku_id
                WHERE cp.is_active = 1
                  AND cp.image_url IS NOT NULL AND cp.image_url != ''
                  AND cp.product_url IS NOT NULL AND cp.product_url != ''
                  AND cp.price > 0
                  AND inv.is_available = 1 AND inv.quantity > 0
                ORDER BY cp.updated_at DESC
                LIMIT 40
            """))
            for pid, name, price, cat, img, url, color, coll in r3.fetchall():
                if not name or not img or not url:
                    continue
                # Limpa imagem
                img_clean = _re.sub(r'-\d+-\d+(/)', r'-500-500\1', img.split('?')[0])
                # Formata preço
                try:
                    cents = round(float(price) * 100)
                    price_fmt = f"R$ {cents//100:,}".replace(",",".") + f",{cents%100:02d}"
                except Exception:
                    price_fmt = str(price)
                # URL com /p
                url_clean = url if url.startswith("http") else f"https://www.aguadecoco.com.br{url}"

                catalog_products.append({
                    "product_id": str(pid),
                    "name": name,
                    "price": price_fmt,
                    "category": cat or "",
                    "image_url": img_clean,
                    "url": url_clean,
                    "color": color or "",
                    "collection": coll or "",
                })
    except Exception:
        pass

    # ── 3. Fallback sem IA ────────────────────────────────────────────────
    anthropic_key = _os.environ.get("ANTHROPIC_API_KEY", "")
    if not anthropic_key or not catalog_products:
        return {
            "message": f"Olá, {client_name}! Separei algumas peças que podem combinar com você.",
            "products": catalog_products[:limit],
        }

    # ── 4. Monta prompt enxuto ────────────────────────────────────────────
    page_ctx = f"Página atual: {payload.page_context}" if payload.page_context else ""
    size_hint = ""
    if "Tamanhos:" in profile_text:
        size_hint = profile_text.split("Tamanhos:")[1].split("\n")[0].strip().split(",")[0].strip()

    catalog_lines = "\n".join(
        f"ID:{p['product_id']}|NOME:{p['name']}|PRECO:{p['price']}|CAT:{p['category']}|IMG:{p['image_url']}|URL:{p['url']}"
        for p in catalog_products[:25]
    )

    system_prompt = f"""Você é personal shopper da Água de Coco. Responda em português, tom sofisticado e caloroso.

CLIENTE: {client_name}
{profile_text}
{page_ctx}

CATÁLOGO EM ESTOQUE:
{catalog_lines}

MISSÃO: Monte um look completo (3-{limit} peças) respondendo ao pedido.
- Priorize as cores e tamanhos favoritos da cliente.
- Se tem tops no closet, sugira calcinhas do mesmo mix.
- Mencione que selecionou baseado no histórico e peças do guarda-roupa.
- Look completo: top/sutiã + calcinha + saída + sandália/bolsa quando possível.

RETORNE APENAS este JSON (sem texto antes/depois, sem markdown):
{{"message":"frase calorosa máx 2 linhas mencionando histórico e complemento do guarda-roupa","products":[{{"id":"ID exato","name":"NOME exato","price":"PRECO exato","category":"CAT exato","image_url":"IMG exata","url":"URL exata"}}]}}"""

    # ── 5. Chama Claude Haiku ─────────────────────────────────────────────
    try:
        async with httpx.AsyncClient(timeout=25) as http:
            resp = await http.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": anthropic_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": "claude-haiku-4-5-20251001",
                    "max_tokens": 1024,
                    "system": system_prompt,
                    "messages": [{"role": "user", "content": f"Pedido de {client_name}: {message}"}],
                },
            )
        if resp.status_code != 200:
            raise ValueError(f"API error {resp.status_code}")
        text = resp.json().get("content", [{}])[0].get("text", "")
    except Exception:
        return {
            "message": f"Olá, {client_name}! Separei algumas peças para você.",
            "products": catalog_products[:limit],
        }

    # ── 6. Parse JSON robusto ─────────────────────────────────────────────
    result = None
    for attempt in [text, text[text.find("{"):text.rfind("}")+1]]:
        try:
            result = json.loads(attempt.strip().replace("```json","").replace("```",""))
            break
        except Exception:
            continue

    if not result or not isinstance(result.get("products"), list):
        result = {
            "message": f"Olá, {client_name}! Separei algumas sugestões para você.",
            "products": catalog_products[:limit],
        }

    # Garante image_url e url corretos usando dados reais do catálogo
    catalog_by_id = {p["product_id"]: p for p in catalog_products}
    clean_products = []
    for p in result.get("products", [])[:limit]:
        pid = str(p.get("id") or p.get("product_id") or "")
        real = catalog_by_id.get(pid, {})
        clean_products.append({
            "id": pid,
            "name": p.get("name") or real.get("name") or "",
            "price": p.get("price") or real.get("price") or "",
            "category": p.get("category") or real.get("category") or "",
            "image_url": real.get("image_url") or (p.get("image_url") or "").split("?")[0],
            "url": real.get("url") or p.get("url") or "",
            "is_complement": bool(p.get("is_complement")),
        })
    result["products"] = clean_products

    # Track
    try:
        from services.closet_db import AsyncSessionLocal
        from sqlalchemy import text as _txt3
        async with AsyncSessionLocal() as db:
            await db.execute(_txt3(
                "INSERT INTO recommendation_clicks (email, product_id, occasion, source, clicked_at) "
                "VALUES (:e, 'stylist_chat', :occ, 'widget_stylist_chat', NOW())"
            ), {"e": email, "occ": message[:100]})
            await db.commit()
    except Exception:
        pass

    return result


@router.post("/track-click")
async def track_recommendation_click(payload: dict):
    """
    Rastreia quando um cliente clica em 'Ver produto' a partir de uma recomendação.
    """
    from datetime import datetime
    from services.closet_db import AsyncSessionLocal
    from sqlalchemy import text

    email      = normalize_email(str(payload.get("email", "") or ""))
    product_id = str(payload.get("product_id", "") or "")
    occasion   = str(payload.get("occasion",   "") or "")
    source     = str(payload.get("source",     "widget") or "widget")

    if not product_id:
        return {"ok": False, "reason": "product_id obrigatório"}

    try:
        async with AsyncSessionLocal() as s:
            await s.execute(text("""
                INSERT INTO recommendation_clicks
                  (email, product_id, occasion, source, clicked_at)
                VALUES
                  (:email, :product_id, :occasion, :source, :clicked_at)
                ON CONFLICT DO NOTHING
            """), {
                "email": email,
                "product_id": product_id,
                "occasion": occasion,
                "source": source,
                "clicked_at": datetime.utcnow(),
            })
            await s.commit()
    except Exception:
        pass

    return {"ok": True}


@router.get("/conversion-stats")
async def get_conversion_stats():
    """
    Retorna métricas de conversão das recomendações para o dashboard.
    """
    from services.closet_db import AsyncSessionLocal
    from sqlalchemy import text

    try:
        async with AsyncSessionLocal() as s:
            r1 = await s.execute(text("""
                SELECT source, COUNT(*) as clicks, COUNT(DISTINCT email) as unique_users
                FROM recommendation_clicks
                GROUP BY source
                ORDER BY clicks DESC
            """))
            by_source = [{"source": r.source, "clicks": r.clicks, "unique_users": r.unique_users}
                         for r in r1.fetchall()]

            r2 = await s.execute(text("""
                SELECT occasion, COUNT(*) as clicks
                FROM recommendation_clicks
                WHERE occasion != ''
                GROUP BY occasion
                ORDER BY clicks DESC
            """))
            by_occasion = [{"occasion": r.occasion, "clicks": r.clicks} for r in r2.fetchall()]

            r3 = await s.execute(text("""
                SELECT rc.product_id, cp.name, cp.category, COUNT(*) as clicks
                FROM recommendation_clicks rc
                LEFT JOIN catalog_products cp ON cp.product_id = rc.product_id
                GROUP BY rc.product_id, cp.name, cp.category
                ORDER BY clicks DESC
                LIMIT 20
            """))
            top_products = [{"product_id": r.product_id, "name": r.name,
                             "category": r.category, "clicks": r.clicks}
                            for r in r3.fetchall()]

            r4 = await s.execute(text("""
                SELECT DATE(clicked_at) as day, COUNT(*) as clicks
                FROM recommendation_clicks
                WHERE clicked_at >= NOW() - INTERVAL '30 days'
                GROUP BY DATE(clicked_at)
                ORDER BY day DESC
            """))
            by_day = [{"day": str(r.day), "clicks": r.clicks} for r in r4.fetchall()]

            r5 = await s.execute(text("SELECT COUNT(*) FROM recommendation_clicks"))
            total = r5.scalar() or 0

            r6 = await s.execute(text("SELECT COUNT(DISTINCT email) FROM recommendation_clicks"))
            unique_users = r6.scalar() or 0

        return {
            "total_clicks": total,
            "unique_users": unique_users,
            "by_source": by_source,
            "by_occasion": by_occasion,
            "top_products": top_products,
            "by_day": by_day,
        }
    except Exception as e:
        return {"total_clicks": 0, "unique_users": 0, "by_source": [],
                "by_occasion": [], "top_products": [], "by_day": [], "error": str(e)}


@router.get("/debug")
async def debug_customer_closet(email: str):
    email = normalize_email(email)
    if not email:
        raise HTTPException(status_code=400, detail="E-mail é obrigatório")

    return await get_customer_closet_payload(email)
