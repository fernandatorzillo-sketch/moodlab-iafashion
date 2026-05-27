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


def normalize_email(email: Any) -> str:
    return str(email or "").strip().lower()


def normalize_answers(raw: dict[str, Any] | None) -> dict[str, str]:
    raw = raw or {}
    return {
        "occasion": str(
            raw.get("occasion")
            or raw.get("ocasiao")
            or raw.get("ocasião")
            or ""
        ).strip().lower(),
        "goal": str(
            raw.get("goal")
            or raw.get("objetivo")
            or ""
        ).strip().lower(),
        "style": str(
            raw.get("style")
            or raw.get("estilo")
            or ""
        ).strip().lower(),
    }


@router.post("/lookup")
async def lookup_customer_closet(payload: LookupRequest):
    email = normalize_email(payload.email)
    if not email:
        raise HTTPException(status_code=400, detail="E-mail é obrigatório")

    data = await get_customer_closet_payload(email)

    customer = data.get("customer") or {
        "name": email.split("@")[0],
        "email": email,
    }

    return {
        **data,
        "cliente": {
            "nome": customer.get("name") or email.split("@")[0],
            "email": customer.get("email") or email,
        },
        "closet_products": data.get("closet", []),
    }


@router.get("/questions")
async def get_questions():
    return {
        "questions": [
            {
                "id": "occasion",
                "label": "Para qual ocasião você quer sugestões agora?",
                "type": "single_select",
                "options": [
                    {"value": "praia", "label": "Praia"},
                    {"value": "resort", "label": "Resort"},
                    {"value": "jantar", "label": "Jantar"},
                    {"value": "viagem", "label": "Viagem"},
                    {"value": "dia_a_dia", "label": "Dia a dia"},
                ],
            },
            {
                "id": "goal",
                "label": "O que você quer encontrar?",
                "type": "single_select",
                "options": [
                    {"value": "cross_sell", "label": "Complementar meus looks"},
                    {"value": "up_sell", "label": "Peças mais sofisticadas"},
                    {"value": "novidades", "label": "Novidades para meu estilo"},
                ],
            },
            {
                "id": "style",
                "label": "Qual estilo você quer priorizar hoje?",
                "type": "single_select",
                "options": [
                    {"value": "elegante", "label": "Elegante"},
                    {"value": "casual", "label": "Casual"},
                    {"value": "sofisticado", "label": "Sofisticado"},
                    {"value": "leve", "label": "Leve"},
                ],
            },
        ]
    }


@router.post("/recommendations")
async def recommend(payload: RecommendationRequest):
    email = normalize_email(payload.email)
    if not email:
        raise HTTPException(status_code=400, detail="E-mail é obrigatório")

    answers = normalize_answers(payload.answers)
    limit = max(1, min(int(payload.limit or 8), 24))

    recommendations = await get_customer_recommendations(
        email=email,
        occasion=answers["occasion"],
        goal=answers["goal"],
        style=answers["style"],
        limit=limit,
    )

    return {
        "email": email,
        "answers": answers,
        "count": len(recommendations),
        "recommendations": recommendations,
        "debug": {
            "email": email,
            "limit": limit,
            "recommendation_count": len(recommendations),
            "message": "Recomendações lidas do banco consolidado.",
        },
    }


@router.post("/stylist-chat")
async def stylist_chat(payload: StylistChatRequest):
    """
    Personal shopper público: lê closet + pedidos do cliente e responde
    com sugestões de produtos baseadas na mensagem livre do usuário.
    """
    email = normalize_email(payload.email)
    if not email:
        raise HTTPException(status_code=400, detail="E-mail é obrigatório")

    message = str(payload.message or "").strip()
    if not message:
        raise HTTPException(status_code=400, detail="Mensagem é obrigatória")

    limit = max(1, min(int(payload.limit or 6), 12))

    # 1. Busca contexto do cliente (closet + pedidos)
    try:
        client_data = await get_customer_closet_payload(email)
    except Exception:
        client_data = {}

    customer = client_data.get("customer") or {}
    closet = client_data.get("closet") or []
    orders = client_data.get("orders") or []
    style_prefs = client_data.get("style_preferences") or {}
    client_name = customer.get("name") or email.split("@")[0]

    # 2. Busca produtos disponíveis no catálogo
    try:
        recs_data = await get_customer_recommendations(
            email=email, occasion="", goal="novidades", style="", limit=30
        )
        catalog_products = recs_data.get("recommendations") or []
    except Exception:
        catalog_products = []

    # 3. Monta contexto para a IA
    closet_lines = [
        f"- {p.get('name', '')} ({p.get('category', '')})"
        for p in closet[:10]
    ]
    closet_summary = ("Closet virtual da cliente:\n" + "\n".join(closet_lines)) if closet_lines else ""

    order_lines = []
    for o in orders[:5]:
        for item in (o.get("items") or [])[:3]:
            order_lines.append(f"- {item.get('name', '')} ({item.get('category', '')})")
    orders_summary = ("Compras anteriores:\n" + "\n".join(order_lines)) if order_lines else ""

    style_parts = []
    if style_prefs.get("estilo_favorito"):
        style_parts.append(f"Estilo favorito: {style_prefs['estilo_favorito']}")
    if style_prefs.get("ocasioes"):
        style_parts.append(f"Ocasiões: {', '.join(style_prefs['ocasioes'])}")
    style_summary = "\n".join(style_parts)

    def _safe_url(u):
        u = str(u or "").strip()
        if not u: return ""
        if u.startswith("/"): return "https://www.aguadecoco.com.br" + u
        if not u.startswith("http"): return "https://www.aguadecoco.com.br/" + u
        return u

    catalog_lines = [
        f"- ID:{p.get('id') or p.get('product_id')} | {p.get('name', '')} | "
        f"PRECO:R$ {p.get('price') or p.get('preco') or '?'} | "
        f"CAT:{p.get('category', '')} | "
        f"IMG:{p.get('image_url') or p.get('imagem_url') or ''} | "
        f"URL:{_safe_url(p.get('url') or p.get('product_url') or p.get('link') or '')}"
        for p in catalog_products[:20]
    ]
    catalog_summary = ("Produtos disponíveis no catálogo:\n" + "\n".join(catalog_lines)) if catalog_lines else ""

    page_ctx = f"\nContexto da página: {payload.page_context}" if payload.page_context else ""

    system_prompt = f"""Você é uma personal shopper sofisticada da Água de Coco, marca brasileira de moda praia e resort wear de luxo.
Seu papel é o de uma vendedora consultora de loja física — atenciosa, personalizada e especialista em moda.
Responda sempre em português, de forma calorosa e consultiva. Máximo 2 frases de introdução, depois os produtos.

{closet_summary}
{orders_summary}
{style_summary}
{page_ctx}

{catalog_summary}

REGRAS CRÍTICAS:
- Sugira entre 2 e {limit} produtos EXCLUSIVAMENTE do catálogo listado acima.
- Use EXATAMENTE os valores de IMG: e URL: de cada produto — NUNCA invente ou modifique URLs.
- Se IMG: estiver vazio, deixe image_url como string vazia "".
- URLs dos produtos SEMPRE começam com https://www.aguadecoco.com.br — copie EXATAMENTE do campo URL:.
- Retorne APENAS um JSON válido no formato abaixo, sem texto adicional antes ou depois:
{{
  "message": "frase consultiva personalizada (máx 2 frases)",
  "products": [
    {{
      "id": "valor exato do campo ID:",
      "name": "valor exato do campo nome",
      "price": "valor exato do campo PRECO:",
      "category": "valor exato do campo CAT:",
      "image_url": "valor exato do campo IMG: — copie sem alterar",
      "url": "valor exato do campo URL: — copie sem alterar"
    }}
  ]
}}"""

    user_prompt = f"Cliente {client_name} disse: \"{message}\""

    # 4. Chama Claude Haiku via Anthropic API
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY", "")

    if not anthropic_key:
        # Fallback sem IA: retorna os primeiros produtos do catálogo
        fallback = [
            {
                "id": str(p.get("id") or p.get("product_id") or ""),
                "name": p.get("name") or p.get("nome") or "",
                "price": f"R$ {p.get('price') or p.get('preco') or ''}" if (p.get("price") or p.get("preco")) else "",
                "category": p.get("category") or p.get("categoria") or "",
                "image_url": p.get("image_url") or p.get("imagem_url") or "",
                "url": p.get("url") or p.get("product_url") or p.get("link") or "",
            }
            for p in catalog_products[:limit]
        ]
        return {
            "message": f"Olá, {client_name}! Separei algumas peças que combinam com seu estilo.",
            "products": fallback,
        }

    async with httpx.AsyncClient(timeout=30) as http:
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
                "messages": [{"role": "user", "content": user_prompt}],
            },
        )

    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail="Erro ao consultar IA")

    raw = resp.json()
    text = raw.get("content", [{}])[0].get("text", "")

    # 5. Parse do JSON retornado pela IA
    try:
        clean = text.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
        result = json.loads(clean)
    except Exception:
        result = {
            "message": text[:200] if text else "Aqui estão algumas sugestões para você!",
            "products": [],
        }

    # 6. Registra interação no tracking
    try:
        from services.closet_db import AsyncSessionLocal
        from sqlalchemy import text as sql_text
        async with AsyncSessionLocal() as db:
            await db.execute(sql_text("""
                INSERT INTO recommendation_clicks
                  (email, product_id, occasion, source, clicked_at)
                VALUES (:email, 'stylist_chat', :occasion, 'widget_stylist_chat', NOW())
            """), {"email": email, "occasion": message[:100]})
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
