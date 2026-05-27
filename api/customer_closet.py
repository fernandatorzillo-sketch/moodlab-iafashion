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

    # 1. Busca perfil completo da cliente direto do banco
    client_name = email.split("@")[0]
    profile = {
        "colors": [],        # cores mais compradas
        "sizes": [],         # tamanhos mais usados
        "prints": [],        # preferência de estampa
        "categories": [],    # categorias mais compradas
        "collections": [],   # coleções favoritas
        "top_items": [],     # peças mais compradas (nome + categoria)
        "top_pieces": {},    # top/sutia comprados → para sugerir calcinhas do mesmo mix
    }

    try:
        client_data = await get_customer_closet_payload(email)
        customer = client_data.get("customer") or {}
        client_name = customer.get("name") or client_name
    except Exception:
        client_data = {}

    try:
        from services.closet_db import AsyncSessionLocal as _SL
        from models.customer_closet_item import CustomerClosetItem as _CCI
        from models.catalog_product import CatalogProduct as _CP
        from sqlalchemy import select as _sel, and_ as _and, func as _func

        async with _SL() as _db:
            # Busca closet enriquecido com dados do catálogo
            _closet_stmt = (
                _sel(_CCI, _CP.color, _CP.size, _CP.print_name,
                     _CP.collection, _CP.occasion, _CP.category.label("cat_category"))
                .outerjoin(_CP, _CP.sku_id == _CCI.sku_id)
                .where(_CCI.email == email)
                .order_by(_CCI.purchase_count.desc())
                .limit(50)
            )
            _rows = (await _db.execute(_closet_stmt)).all()

            from collections import Counter
            _color_ctr = Counter()
            _size_ctr = Counter()
            _print_ctr = Counter()
            _cat_ctr = Counter()
            _coll_ctr = Counter()
            _top_pieces = []
            _tops = []  # sutias/tops para parear calcinhas

            for _r in _rows:
                _item = _r[0]
                _color = _r[1]
                _size = _r[2]
                _print = _r[3]
                _coll = _r[4]
                _cat = _r[5] or _item.category or ""

                if _color: _color_ctr[_color.strip().lower()] += (_item.purchase_count or 1)
                if _size:  _size_ctr[_size.strip().upper()] += (_item.purchase_count or 1)
                if _print: _print_ctr[_print.strip().lower()] += 1
                if _cat:   _cat_ctr[_cat.strip().lower()] += (_item.purchase_count or 1)
                if _coll:  _coll_ctr[_coll.strip().lower()] += 1

                if _item.name:
                    _top_pieces.append(f"{_item.name} ({_cat})")
                    _name_lower = (_item.name or "").lower()
                    if any(t in _name_lower for t in ["sutiã","sutia","top","cropped","frente única","bandeau","faixa"]):
                        _tops.append({
                            "name": _item.name,
                            "collection": _coll or "",
                            "category": _cat,
                        })

            profile["colors"] = [c for c, _ in _color_ctr.most_common(5)]
            profile["sizes"] = [s for s, _ in _size_ctr.most_common(3)]
            profile["prints"] = [p for p, _ in _print_ctr.most_common(3)]
            profile["categories"] = [c for c, _ in _cat_ctr.most_common(5)]
            profile["collections"] = [c for c, _ in _coll_ctr.most_common(3)]
            profile["top_items"] = _top_pieces[:8]
            profile["top_pieces"] = _tops[:3]  # tops/sutias para parear

    except Exception as _profile_err:
        pass  # profile fica vazio, IA ainda funciona

    # Monta resumo do perfil para o prompt
    def _profile_line(label, items):
        return f"{label}: {', '.join(items)}" if items else ""

    profile_lines = [
        _profile_line("Cores favoritas", profile["colors"]),
        _profile_line("Tamanhos", profile["sizes"]),
        _profile_line("Estampas preferidas", profile["prints"]),
        _profile_line("Categorias mais compradas", profile["categories"]),
        _profile_line("Coleções favoritas", profile["collections"]),
    ]
    if profile["top_items"]:
        profile_lines.append(f"Peças no closet: {'; '.join(profile['top_items'][:5])}")
    if profile["top_pieces"]:
        tops_str = "; ".join(f"{t['name']} (coleção: {t['collection']})" for t in profile["top_pieces"])
        profile_lines.append(f"Tops/Sutiãs que já tem (sugerir calcinhas do mesmo mix): {tops_str}")

    client_profile = "\n".join(l for l in profile_lines if l)

    # 2. Busca produtos direto do banco — garante image_url, price e product_url reais
    catalog_products = []
    try:
        from services.closet_db import AsyncSessionLocal
        from models.catalog_product import CatalogProduct
        from models.inventory_by_sku import InventoryBySku
        from sqlalchemy import select, and_, or_

        async with AsyncSessionLocal() as db:
            stmt = (
                select(CatalogProduct)
                .join(InventoryBySku, InventoryBySku.sku_id == CatalogProduct.sku_id)
                .where(and_(
                    CatalogProduct.is_active == 1,
                    CatalogProduct.image_url.isnot(None),
                    CatalogProduct.image_url != "",
                    CatalogProduct.product_url.isnot(None),
                    CatalogProduct.product_url != "",
                    CatalogProduct.price.isnot(None),
                    CatalogProduct.price > 0,
                    InventoryBySku.is_available == 1,
                    InventoryBySku.quantity > 0,
                ))
                .order_by(CatalogProduct.updated_at.desc())
                .limit(60)
            )
            result = await db.execute(stmt)
            rows = result.scalars().all()

            def _clean_img_url(url: str) -> str:
                if not url: return ""
                url = str(url).strip()
                if "?" in url: url = url.split("?")[0]
                import re as _re
                url = _re.sub(r"-\d+-\d+(/)", r"-500-500", url)
                return url

            def _fmt_p(v) -> str:
                try:
                    f_val = float(v)
                    if f_val <= 0: return ""
                    cents = round(f_val * 100)
                    reais = cents // 100
                    centavos = cents % 100
                    return f"R$ {reais:,}".replace(",", ".") + f",{centavos:02d}"
                except Exception:
                    return str(v) if v else ""

            catalog_products = [
                {
                    "product_id": r.product_id,
                    "name": r.name or "",
                    "price": _fmt_p(r.price),
                    "category": r.category or "",
                    "image_url": _clean_img_url(r.image_url),
                    "url": r.product_url if r.product_url.startswith("http")
                           else f"https://www.aguadecoco.com.br{r.product_url}",
                }
                for r in rows
                if r.name and r.image_url and r.product_url
            ]
    except Exception as _e:
        pass

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
        """Garante URL de PDP válida no domínio aguadecoco.com.br com /p no final."""
        u = str(u or "").strip().rstrip("/")
        if not u: return ""
        # Reconstrói domínio correto
        if u.startswith("/"): u = "https://www.aguadecoco.com.br" + u
        elif not u.startswith("http"): u = "https://www.aguadecoco.com.br/" + u
        # Remove query string
        if "?" in u: u = u.split("?")[0]
        # Garante /p no final para PDP VTEX
        if not u.endswith("/p") and not u.endswith(".br") and "/Sistema/" not in u:
            u = u + "/p"
        return u

    def _fmt_price(p_dict):
        """Formata preço como 'R$ 299,00' a partir de float ou string."""
        v = p_dict.get("price") or p_dict.get("preco")
        if not v:
            return ""
        try:
            f_val = float(v)
            if f_val <= 0:
                return ""
            # Formata: 299.0 → "R$ 299,00"
            cents = round(f_val * 100)
            reais = cents // 100
            centavos = cents % 100
            return f"R$ {reais:,}".replace(",", ".") + f",{centavos:02d}"
        except Exception:
            return str(v)

    def _clean_img(url: str) -> str:
        """Limpa URL de imagem VTEX: remove query string, troca 728-1090 por 500-500."""
        if not url:
            return ""
        url = str(url).strip()
        # Remove query string (?v=...)
        if "?" in url:
            url = url.split("?")[0]
        # Substitui dimensão grande por 500x500
        import re
        url = re.sub(r"-\d+-\d+(/)", r"-500-500\1", url)
        return url

    catalog_lines = [
        f"- ID:{p['product_id']} | "
        f"NOME:{p['name']} | "
        f"PRECO:{p['price']} | "
        f"CAT:{p['category']} | "
        f"IMG:{p['image_url']} | "
        f"URL:{p['url']}"
        for p in catalog_products[:20]
    ]
    catalog_summary = ("Produtos disponíveis no catálogo:\n" + "\n".join(catalog_lines)) if catalog_lines else ""

    page_ctx = f"\nContexto da página: {payload.page_context}" if payload.page_context else ""

    # Pré-computa strings para usar no f-string sem conflito de aspas
    has_profile = bool(profile.get("top_items") or profile.get("colors"))
    client_size_hint = profile["sizes"][0] if profile.get("sizes") else ""
    size_mention = f"tamanho {client_size_hint}" if client_size_hint else "suas medidas habituais"

    system_prompt = f"""Você é uma personal shopper especialista da Água de Coco, marca brasileira de moda praia e resort wear de luxo.
Responda SEMPRE em português do Brasil, com tom caloroso e sofisticado, como uma vendedora de boutique de alto padrão.

PERFIL DA CLIENTE {client_name}:
{client_profile}
{page_ctx}

CATÁLOGO DISPONÍVEL PARA VENDA (produtos em estoque):
{catalog_summary}

ESTRATÉGIA DE CURADORIA — siga esta ordem de prioridade:
1. COMPLEMENTO DO GUARDA-ROUPA: se a cliente tem peças no closet, priorize produtos que completem looks já existentes.
   Exemplo: tem sutiã Bananas → sugira calcinha Bananas + saída Bananas.
2. LOOK COMPLETO: SEMPRE tente montar um look completo com 3-5 peças quando possível:
   - Praia/Resort: top/sutiã + calcinha + saída de praia/canga + sandália/rasteira + bolsa/chapéu
   - Casual/Passeio: blusa/vestido + calça/saia + sandália + acessório
   - Jantar/Festa: vestido/conjunto + sandália/scarpin + bolsa/acessório
3. PERSONALIZAÇÃO: priorize as cores favoritas e tamanho habitual da cliente.
4. NOVIDADES: inclua pelo menos 1 peça nova que ela ainda não tem.

MENSAGEM PERSONALIZADA — use este raciocínio na mensagem:
- Se tem histórico: "Separei peças de acordo com suas compras anteriores e {size_mention}..."
- Se complementa closet: "...e produtos que combinam perfeitamente com o que você já tem no guarda-roupa."
- Se é novidade: "...além de novidades que combinam com o seu estilo."
- Máximo 2 frases, caloroso e direto.

FORMATO DA RESPOSTA — retorne SOMENTE este JSON, sem nenhum texto antes ou depois:
{{
  "message": "mensagem personalizada seguindo o raciocínio acima",
  "products": [
    {{
      "id": "copie o valor após ID:",
      "name": "copie o valor após NOME:",
      "price": "copie o valor após PRECO:",
      "category": "copie o valor após CAT:",
      "image_url": "copie a URL completa após IMG:",
      "url": "copie a URL completa após URL:",
      "is_complement": true
    }}
  ]
}}

REGRAS TÉCNICAS OBRIGATÓRIAS:
- Use APENAS produtos do catálogo listado acima — NUNCA invente produtos.
- Copie ID, NOME, PRECO, CAT, IMG e URL EXATAMENTE como estão no catálogo.
- NUNCA invente preços, imagens ou URLs.
- NUNCA retorne texto fora do JSON.
- NUNCA use markdown ou blocos de código.
- is_complement = true se a peça complementa algo do closet, false se é novidade.
"""

    user_prompt = f"Cliente {client_name} disse: \"{message}\""

    # 4. Chama Claude Haiku via Anthropic API
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY", "")

    if not anthropic_key:
        # Fallback sem IA: retorna os primeiros produtos do catálogo
        fallback = catalog_products[:limit]
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

    # 5. Parse do JSON retornado pela IA — robusto contra texto extra
    result = None
    try:
        # Tenta extrair JSON mesmo se vier com texto antes/depois
        clean = text.strip()
        # Remove blocos markdown
        clean = clean.replace("```json", "").replace("```", "").strip()
        # Tenta parse direto
        result = json.loads(clean)
    except Exception:
        pass

    if result is None:
        # Tenta encontrar o JSON dentro do texto via busca de { }
        try:
            start = text.find("{")
            end = text.rfind("}") + 1
            if start >= 0 and end > start:
                result = json.loads(text[start:end])
        except Exception:
            pass

    if result is None:
        # Fallback: mensagem do texto + primeiros produtos do catálogo
        msg = text[:200] if text else "Separei algumas sugestões para você!"
        # Remove asteriscos de markdown da mensagem
        msg = msg.replace("**", "").replace("*", "").strip()
        result = {
            "message": msg,
            "products": catalog_products[:limit],
        }

    # Garante que products é lista e limpa markdown dos campos
    if not isinstance(result.get("products"), list):
        result["products"] = catalog_products[:limit]

    # Remove markdown da mensagem
    if result.get("message"):
        result["message"] = result["message"].replace("**", "").replace("*", "").strip()

    # Garante que cada produto tem os campos necessários — usa dados reais do catálogo como fallback
    catalog_by_id = {p["product_id"]: p for p in catalog_products}
    clean_products = []
    for p in result.get("products", [])[:limit]:
        pid = str(p.get("id") or p.get("product_id") or "")
        real = catalog_by_id.get(pid, {})
        clean_products.append({
            "id": pid or real.get("product_id", ""),
            "name": p.get("name") or real.get("name") or "",
            "price": p.get("price") or real.get("price") or "",
            "category": p.get("category") or real.get("category") or "",
            "image_url": (p.get("image_url") or real.get("image_url") or "").split("?")[0],
            "url": p.get("url") or real.get("url") or "",
        })
    result["products"] = clean_products

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
