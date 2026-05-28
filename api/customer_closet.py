import json
import os
from collections import defaultdict
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from services.customer_closet_service import get_customer_closet_payload
from services.recommendation_service import get_customer_recommendations


# ── Tabela de match de cores 2026 ─────────────────────────────────────────
# Usada tanto no filtro de catálogo quanto no system_prompt
COLOR_MATCH_2026 = {
    # Verde
    "verde oliva":   ["bege","areia","off white","marrom","chocolate","azul petróleo","vinho"],
    "verde bandeira":["rosa","branco","cinza","azul marinho","caramelo"],
    "verde sálvia":  ["lavanda","creme","cinza","azul bebê","prata"],
    "verde":         ["bege","off white","branco","caramelo","areia"],
    # Azul
    "azul marinho":  ["branco","bege","vermelho","mostarda","verde oliva"],
    "azul bebê":     ["marrom","chocolate","mocha","cinza","rosa","branco","prata"],
    "azul petróleo": ["ferrugem","nude","preto","verde","dourado"],
    "azul":          ["branco","bege","caramelo","off white","areia"],
    # Rosa
    "rosa blush":    ["marrom","chocolate","cinza","branco","verde oliva","azul"],
    "rosa":          ["vermelho","preto","off white","roxo","marrom"],
    # Marrom
    "marrom":        ["azul bebê","rosa","verde sálvia","creme","off white","bege"],
    "chocolate":     ["azul bebê","rosa","verde","creme","vinho"],
    "caramelo":      ["branco","azul marinho","verde","preto","dourado"],
    "mocha":         ["off white","bege","caramelo","verde","rosa blush"],
    # Vermelho/Vinho
    "vermelho":      ["rosa","azul","cinza","preto","bege"],
    "vinho":         ["verde oliva","creme","azul petróleo","marrom","rosé"],
    # Roxo
    "lavanda":       ["cinza","verde menta","branco","azul bebê","prata"],
    "roxo":          ["bege","preto","rosa","verde","dourado"],
    # Neutros (combinam com tudo)
    "preto":         ["branco","off white","bege","dourado","vermelho","caramelo"],
    "branco":        ["qualquer"],
    "off white":     ["qualquer"],
    "bege":          ["qualquer"],
    "areia":         ["qualquer"],
    "creme":         ["qualquer"],
    "cinza":         ["azul","rosa","vermelho","branco","preto"],
    "dourado":       ["preto","marrom","azul petróleo","vinho","caramelo"],
    "prata":         ["azul bebê","lavanda","cinza","preto","branco"],
}

# Cores neutras 2026 — combinam com qualquer outra
NEUTROS_2026 = {"branco","off white","bege","areia","creme","mocha","cinza névoa","preto suave","preto"}

def _color_matches(cor1: str, cor2: str) -> bool:
    """Verifica se duas cores combinam pela tabela 2026."""
    c1 = cor1.lower().strip()
    c2 = cor2.lower().strip()
    if not c1 or not c2: return True  # sem cor = não filtra
    if c1 in NEUTROS_2026 or c2 in NEUTROS_2026: return True
    # Busca match parcial nas chaves
    for key, combos in COLOR_MATCH_2026.items():
        if key in c1:
            if "qualquer" in combos: return True
            return any(m in c2 for m in combos)
    return True  # sem regra definida = permite

router = APIRouter(prefix="/api/v1/customer-closet", tags=["customer-closet"])


class LookupRequest(BaseModel):
    email: str


class RecommendationRequest(BaseModel):
    email: str
    answers: dict[str, Any] = {}
    limit: int = 8


class ChatMessage(BaseModel):
    role: str  # "user" | "assistant"
    content: str

class StylistChatRequest(BaseModel):
    email: str
    message: str
    page_context: str = ""
    limit: int = 6
    history: list[ChatMessage] = []  # histórico das últimas mensagens


@router.post("/stylist-chat")
async def stylist_chat(payload: StylistChatRequest):
    """Personal shopper público com IA — v4 (cadastro-first)."""
    import os as _os

    email   = str(payload.email or "").strip().lower()
    message = str(payload.message or "").strip()
    limit   = max(2, min(int(payload.limit or 6), 8))

    if not email:
        raise HTTPException(status_code=400, detail="E-mail é obrigatório")
    if not message:
        raise HTTPException(status_code=400, detail="Mensagem é obrigatória")

    client_name  = email.split("@")[0]
    profile_text = ""
    memory_text  = ""

    # ── 1. Perfil da cliente (leve) ──────────────────────────────────────────
    try:
        from services.closet_db import AsyncSessionLocal
        from sqlalchemy import text as _txt
        from collections import Counter

        async with AsyncSessionLocal() as db:
            r = await db.execute(_txt(
                "SELECT name FROM customers WHERE email=:e LIMIT 1"
            ), {"e": email})
            row = r.fetchone()
            if row and row[0]:
                client_name = row[0].split()[0]

            r2 = await db.execute(_txt("""
                SELECT cp.color, cp.size, cp.print_name, cp.collection,
                       cci.name, cp.category, cp.product_type
                FROM customer_closet_items cci
                LEFT JOIN catalog_products cp ON cp.sku_id = cci.sku_id
                WHERE cci.email = :e
                ORDER BY cci.purchase_count DESC LIMIT 30
            """), {"e": email})
            rows = r2.fetchall()

            colors, sizes, cats = Counter(), Counter(), Counter()
            closet_tops = []
            for color, size, print_n, coll, name, cat, ptype in rows:
                if color: colors[color.lower()] += 1
                if size:  sizes[size.upper()] += 1
                if cat:   cats[cat.lower()] += 1
                if name:
                    n, pt = name.lower(), (ptype or "").upper()
                    if pt in ("BIQUINI SUTIA","SUTIA") or any(
                        t in n for t in ["sutiã","sutia","bandeau","cortininha","frente única","faixa"]
                    ):
                        closet_tops.append({"name": name, "collection": coll or ""})

            parts = []
            if colors: parts.append(f"Cores favoritas: {', '.join(c for c,_ in colors.most_common(4))}")
            if sizes:  parts.append(f"Tamanhos: {', '.join(s for s,_ in sizes.most_common(2))}")
            if cats:   parts.append(f"Categorias frequentes: {', '.join(c for c,_ in cats.most_common(3))}")
            if closet_tops:
                parts.append(f"Sutiãs/tops no closet (sugerir calcinha do mesmo mix): "
                             + ", ".join(t["name"] for t in closet_tops[:2]))
            profile_text = "\n".join(parts)

            # Memória
            mr = await db.execute(_txt(
                "SELECT resumo_ia FROM client_memory WHERE email=:e LIMIT 1"
            ), {"e": email})
            mrow = mr.fetchone()
            if mrow and mrow[0]:
                memory_text = f"Memória prévia: {mrow[0]}"
    except Exception:
        pass

    # ── 2. Catálogo ──────────────────────────────────────────────────────────
    # Carrega TODOS os campos relevantes do cadastro VTEX
    catalog_products: list[dict] = []
    try:
        from services.closet_db import AsyncSessionLocal
        from sqlalchemy import text as _txt2

        async with AsyncSessionLocal() as db:
            r3 = await db.execute(_txt2("""
                SELECT cp.product_id, cp.name, cp.price, cp.list_price,
                       cp.category, cp.product_type, cp.image_url, cp.product_url,
                       cp.color, cp.collection, cp.occasion, cp.print_name,
                       cp.gender, cp.department
                FROM catalog_products cp
                INNER JOIN inventory_by_sku inv ON inv.sku_id = cp.sku_id
                WHERE cp.is_active = 1
                  AND cp.image_url IS NOT NULL AND cp.image_url != ''
                  AND cp.product_url IS NOT NULL AND cp.product_url != ''
                  AND cp.price > 0
                  AND inv.is_available = 1 AND inv.quantity > 0
                ORDER BY cp.updated_at DESC
                LIMIT 120
            """))
            for (pid, name, price, list_p, cat, ptype, img, url,
                 color, coll, occ, print_n, gender, dept) in r3.fetchall():
                if not name or not img or not url:
                    continue
                # Normaliza URL de imagem — garante https absoluto
                img_raw = (img or "").strip().split("?")[0]
                if img_raw.startswith("//"):
                    img_clean = "https:" + img_raw
                elif img_raw.startswith("/"):
                    img_clean = "https://lojaaguadecoco.vteximg.com.br" + img_raw
                else:
                    img_clean = img_raw

                # Formata preços
                def _fmt(v):
                    try:
                        c = round(float(v) * 100)
                        return f"R$ {c//100:,}".replace(",",".") + f",{c%100:02d}"
                    except Exception:
                        return str(v) if v else ""

                price_fmt    = _fmt(price)
                list_p_fmt   = _fmt(list_p) if list_p and float(list_p or 0) > float(price or 0) else ""
                url_clean    = url if url.startswith("http") else f"https://www.aguadecoco.com.br{url}"

                # ── Classificação baseada exclusivamente nos campos do cadastro ──
                # Prioridade: product_type > occasion > category
                # NÃO usa heurística de nome — usa o que a marca cadastrou
                pt  = (ptype or "").strip().upper()
                oc  = (occ   or "").strip().upper()
                cat_u = (cat  or "").strip().upper()
                pn  = (print_n or "").strip().upper()

                # Tipo de peça (product_type é o campo mais preciso — Tipo de Produto no VTEX)
                PTYPE_MAP = {
                    "BIQUINI SUTIA":           "PRAIA_TOP",
                    "SUTIA":                   "PRAIA_TOP",
                    "BIQUINI CALCINHA":        "PRAIA_BOTTOM",
                    "CALCINHA":                "PRAIA_BOTTOM",
                    "MAIO":                    "MAIO",
                    "SUNGA":                   "SUNGA",
                    "VESTIDO":                 "VESTIDO",
                    "MACACÃO":                 "VESTIDO",
                    "MACACAO":                 "VESTIDO",
                    "CHEMISE":                 "VESTIDO",
                    "CALCA":                   "BOTTOM",
                    "SAIA":                    "BOTTOM",
                    "SHORT":                   "BOTTOM",
                    "BERMUDA":                 "BOTTOM",
                    "BOARDSHORT":              "BOTTOM",
                    "BLUSA/TOP":               "TOP",
                    "BLUSA":                   "TOP",
                    "TOP":                     "TOP",
                    "CAMISETA":                "TOP",
                    "CAMISA":                  "TOP",
                    "BODY":                    "TOP",
                    "CROPPED":                 "TOP",
                    "SAIDA DE PRAIA":          "SAIDA",
                    "SAIDA DE BANHO":          "SAIDA",
                    "CAPA/CAPA KIMONO":        "SAIDA",
                    "CAPA":                    "SAIDA",
                    "CANGA":                   "SAIDA",
                    "TUNICA":                  "SAIDA",
                    "PAREO":                   "SAIDA",
                    "SANDALIA":                "CALCADO",
                    "SANDÁLIAS":               "CALCADO",
                    "CALCADO":                 "CALCADO",
                    "CALÇADOS":                "CALCADO",
                    "CHINELO":                 "CALCADO",
                    "RASTEIRA":                "CALCADO",
                    "BOLSA":                   "BOLSA",
                    "NECESSAIRE":              "BOLSA",
                    "BRINCO":                  "ACESSORIO",
                    "COLAR":                   "ACESSORIO",
                    "PULSEIRA":                "ACESSORIO",
                    "ANEL":                    "ACESSORIO",
                    "CHAPEU/BONE/VISEIRA":     "ACESSORIO",
                    "CHAPÉU":                  "ACESSORIO",
                    "OCULOS":                  "ACESSORIO",
                    "ÓCULOS":                  "ACESSORIO",
                    "CINTO":                   "ACESSORIO",
                    "LENCO":                   "ACESSORIO",
                    "JAQUETA/BLAZER/PARKA":    "FRIO",
                    "JAQUETA":                 "FRIO",
                    "BLAZER":                  "FRIO",
                    "MOLETOM":                 "FRIO",
                    "TRICO":                   "FRIO",
                    "TRICÔ":                   "FRIO",
                }
                tipo = PTYPE_MAP.get(pt)

                # Fallback: occasion do VTEX
                if not tipo:
                    OCC_MAP = {
                        "BIQUINI SUTIA":     "PRAIA_TOP",
                        "BIQUINI CALCINHA":  "PRAIA_BOTTOM",
                        "MAIO":              "MAIO",
                        "SUNGA":             "SUNGA",
                        "SAIDA DE PRAIA":    "SAIDA",
                        "SAIDA DE BANHO":    "SAIDA",
                        "CAPA/CAPA KIMONO":  "SAIDA",
                        "CANGA":             "SAIDA",
                        "TUNICA":            "SAIDA",
                        "VESTIDO":           "VESTIDO",
                        "CALCA":             "BOTTOM",
                        "SHORT":             "BOTTOM",
                        "BERMUDA":           "BOTTOM",
                        "SAIA":              "BOTTOM",
                        "BOARDSHORT":        "BOTTOM",
                        "BLUSA/TOP":         "TOP",
                        "CAMISETA":          "TOP",
                        "CAMISA":            "TOP",
                        "BODY":              "TOP",
                        "ACESSORIOS":        "ACESSORIO",
                        "JAQUETA/BLAZER/PARKA": "FRIO",
                    }
                    tipo = OCC_MAP.get(oc)

                    # Ocasião "PRAIA" genérica — desambigua por category
                    if not tipo and oc == "PRAIA":
                        for k, v in {
                            "SUTIA": "PRAIA_TOP", "BIQUÍNI": "PRAIA_TOP",
                            "CALCINHA": "PRAIA_BOTTOM", "MAIÔ": "MAIO",
                            "SAÍDA": "SAIDA", "SAIDA": "SAIDA", "CANGA": "SAIDA",
                            "SUNGA": "SUNGA",
                        }.items():
                            if k in cat_u:
                                tipo = v
                                break
                        if not tipo:
                            tipo = "PRAIA_TOP"  # default praia

                # Fallback: category de navegação
                if not tipo:
                    for k, v in {
                        "BIQUÍNIS": "PRAIA_TOP", "SUTIA": "PRAIA_TOP",
                        "CALCINHA": "PRAIA_BOTTOM",
                        "MAIÔS": "MAIO", "BODIES": "MAIO",
                        "SUNGAS": "SUNGA",
                        "SAÍDAS": "SAIDA", "CANGAS": "SAIDA",
                        "VESTIDOS": "VESTIDO", "MACACÕES": "VESTIDO",
                        "SAIAS": "BOTTOM", "CALÇAS": "BOTTOM",
                        "SHORTS": "BOTTOM", "BERMUDAS": "BOTTOM",
                        "BLUSAS": "TOP", "CAMISAS": "TOP", "CAMISETAS": "TOP",
                        "CALÇADOS": "CALCADO",
                        "BOLSAS": "BOLSA", "NECESSAIRES": "BOLSA",
                        "BRINCOS": "ACESSORIO", "COLARES": "ACESSORIO",
                        "CHAPÉUS": "ACESSORIO", "ÓCULOS": "ACESSORIO",
                        "CINTOS": "ACESSORIO", "LENÇOS": "ACESSORIO",
                    }.items():
                        if k in cat_u:
                            tipo = v
                            break

                if not tipo:
                    tipo = "OUTRO"

                # ── Detecta se é peça de frio pelo cadastro — SEM heurística de nome ──
                # product_type já trata TRICO/TRICÔ/JAQUETA etc.
                # Única exceção: Linha VIDA (roupa casual, não praia) não é frio mas também
                # não deve aparecer em contexto de praia — marcamos como ROUPA
                # Linha: detecta pelo campo collection se vier AGUA/VIDA/LUZ
                # (sem migration — usa o que já existe no banco)
                coll_upper = (coll or "").strip().upper()
                linha = coll_upper if coll_upper in ("AGUA","VIDA","LUZ","UNDERWEAR") else ""

                # Mix: sempre extraído do nome do produto — fonte mais confiável
                # Ex: "Biquíni Sutiã Faixa Báltico Marrom" → mix = "Báltico"
                _stopwords = {
                    "biquíni","biquini","sutiã","sutia","calcinha","maio","maiô",
                    "saída","saida","capa","canga","faixa","cortininha","frente",
                    "única","bandeau","vestido","blusa","camisa","calça","short",
                    "saia","marrom","preto","branco","azul","verde","rosa","pink",
                    "vermelho","bege","nude","off","white","caramelo","dourado",
                    "prata","cinza","areia","creme","vinho","coral","roxo","liso",
                    "estampado","trabalhado","de","da","do","e","com","para","em",
                    pt.lower(), oc.lower(), pn.lower(),
                }
                mix = ""
                if name:
                    words = name.split()
                    mix_words = [w for w in words
                                 if w[0:1].isupper()
                                 and w.lower().rstrip("s") not in _stopwords
                                 and len(w) > 3]
                    if mix_words:
                        mix = " ".join(mix_words[:2])

                # Linha VIDA = roupa lifestyle, não aparece em contexto praia
                if linha == "VIDA" and tipo not in ("FRIO","CALCADO","BOLSA","ACESSORIO"):
                    tipo = "ROUPA"

                catalog_products.append({
                    "product_id":   str(pid),
                    "name":         name,
                    "price":        price_fmt,
                    "list_price":   list_p_fmt,
                    "category":     cat or "",
                    "product_type": pt,
                    "occasion_vtex":oc,
                    "print_name":   pn,     # LISO / ESTAMPADO / LISO TRABALHADO
                    "color":        (color or "").strip(),
                    "mix":          mix,    # nome do mix extraído do nome: Báltico, Copa...
                    "linha":        linha,  # AGUA / VIDA / LUZ (se vier no collection)
                    "gender":       (gender or "").strip().upper(),
                    "department":   (dept or "").strip().upper(),
                    "image_url":    img_clean,
                    "url":          url_clean,
                    "_tipo":        tipo,
                })
    except Exception:
        pass

    # ── 3. Fallback sem IA ───────────────────────────────────────────────────
    anthropic_key = _os.environ.get("ANTHROPIC_API_KEY", "")
    if not anthropic_key or not catalog_products:
        return {
            "message": f"Olá, {client_name}! Separei algumas peças para você.",
            "products": catalog_products[:limit],
        }

    # ── 4. Detecta contexto — mensagem atual + histórico do usuário ──────────
    msg_lower = message.lower()
    hist_user = " ".join(
        h.content.lower() for h in (payload.history or [])[-6:] if h.role == "user"
    )
    ctx = msg_lower + " " + hist_user  # contexto acumulado para detectar ocasião

    is_beach  = any(t in ctx for t in ["praia","biquini","biquíni","maio","maiô","resort","piscina","mar","surf","sunga"])
    is_cold   = any(t in ctx for t in ["frio","inverno","tricô","trico","suéter","casaco"])
    is_party  = any(t in ctx for t in ["festa","balada","jantar","evento","chique","sofisticad","formatura","casamento","aniversario","barco","iate","reveillon"])
    is_casual = any(t in ctx for t in ["casual","dia a dia","passeio","shopping","trabalho","escritorio"])
    # SALE: só mensagem atual (cliente pode mudar de ideia)
    is_sale   = any(t in msg_lower for t in ["promoção","promocao","promo","desconto","sale","oferta","mais barato","barato","economizar"])
    is_saida  = any(t in ctx for t in ["saída","saida","capa","kimono","canga","túnica","tunica","pareo","kaftan"])

    # ── 5. Filtra catálogo por contexto de ocasião ───────────────────────────
    # Usa APENAS campos do cadastro — zero heurística de nome de produto
    filtered: list[dict] = []
    for p in catalog_products:
        tipo  = p["_tipo"]
        linha = p["linha"]

        # Contexto praia: só mostra peças de praia e neutros (não FRIO, não ROUPA)
        if is_beach and not is_party:
            if tipo in ("FRIO",):
                continue
            # Roupa de lifestyle (Linha VIDA) não é saída de praia
            if tipo == "ROUPA":
                continue

        # Contexto frio: não mostra biquíni/maiô
        if is_cold and not is_beach:
            if tipo in ("PRAIA_TOP", "PRAIA_BOTTOM", "MAIO", "SUNGA"):
                continue

        # Contexto festa: não mostra biquíni/maiô/sunga em look de evento
        if is_party and not is_beach:
            if tipo in ("PRAIA_TOP", "PRAIA_BOTTOM", "MAIO", "SUNGA"):
                continue
            if tipo == "FRIO":
                continue

        filtered.append(p)

    # ── 6. Filtro SALE — aplica em cima do filtro de ocasião (não substitui) ─
    if is_sale:
        sale_ctx = [p for p in filtered if p.get("list_price")]
        if len(sale_ctx) < 3:
            # Fallback: categoria sale dentro do contexto
            sale_ctx = [p for p in filtered
                       if "sale" in (p.get("category") or "").lower() or p.get("list_price")]
        if len(sale_ctx) >= 3:
            filtered = sale_ctx

    # ── 7. Balanceia por tipo para diversidade ───────────────────────────────
    from collections import defaultdict as _dd
    by_type = _dd(list)
    for p in filtered:
        by_type[p["_tipo"]].append(p)

    priority = ["MAIO","SUNGA","PRAIA_TOP","PRAIA_BOTTOM","SAIDA",
                "VESTIDO","TOP","ROUPA","BOTTOM","CALCADO","BOLSA","ACESSORIO","OUTRO","FRIO"]
    slots = {
        "SAIDA":       15 if is_saida else 8,
        "VESTIDO":     8  if is_saida else 6,
        "BOTTOM":      4  if is_saida else 2,
        "TOP":         3  if is_saida else 2,
        "ROUPA":       4,
        "MAIO":        5, "PRAIA_TOP": 5, "PRAIA_BOTTOM": 5,
        "SUNGA":       4, "CALCADO": 3, "BOLSA": 3, "ACESSORIO": 2,
    }
    balanced: list[dict] = []
    seen_ids: set = set()
    for t in priority:
        for p in by_type[t][:slots.get(t, 2)]:
            balanced.append(p)
            seen_ids.add(p["product_id"])
    # Preenche até 30
    for p in filtered:
        if len(balanced) >= 30:
            break
        if p["product_id"] not in seen_ids:
            balanced.append(p)
            seen_ids.add(p["product_id"])

    # ── 8. Monta catálogo para o prompt (campos do cadastro VTEX) ────────────
    # Cada linha expõe os dados estruturados que a IA usa para decidir
    # PRINT_NAME é o campo real do cadastro: LISO / ESTAMPADO / LISO TRABALHADO
    catalog_lines = "\n".join(
        (
            f"ID:{p['product_id']}|TIPO:{p['_tipo']}|NOME:{p['name']}"
            f"|COR:{p['color']}|ESTAMPARIA:{p['print_name']}"
            f"|MIX:{p['mix']}|LINHA:{p['linha']}"
            f"|GENERO:{p['gender']}|PRECO:{p['price']}"
            + (f"|DE:{p['list_price']}" if p.get("list_price") else "")
            + f"|IMG:{p['image_url']}|URL:{p['url']}"
        )
        for p in balanced[:35]
    )

    page_ctx   = f"Página atual: {payload.page_context}" if payload.page_context else ""
    sale_hint  = (
        "PROMOÇÃO: priorize produtos com campo DE: preenchido. "
        "Cite o preço original e o desconto. Se não houver desconto, mencione 'seleção especial SALE'."
    ) if is_sale else ""

    # ── 9. System prompt — baseado em regras de negócio reais ───────────────
    system_prompt = f"""Você é a personal shopper da Água de Coco — marca brasileira de moda praia e resort de luxo.
Tom: sofisticado, caloroso, SEMPRE orientado à venda. Responda SEMPRE em português do Brasil.
NUNCA use "querida", "amada", "linda" — chame sempre pelo NOME: {client_name}.
{sale_hint}

CLIENTE: {client_name}
{memory_text}
{profile_text}
{page_ctx}

IMPORTANTE: O catálogo abaixo = produtos DISPONÍVEIS. O perfil acima = peças que ela JÁ TEM.
Se ela menciona peça que já tem ("meu biquini X"), NÃO diga que não temos — sugira complementos.

CATÁLOGO DISPONÍVEL:
{catalog_lines}

═══════════════════════════════════════════
GUIA DE USO DO CADASTRO VTEX
═══════════════════════════════════════════

CAMPO ESTAMPARIA (exatamente como cadastrado):
  • LISO         = peça lisa, sem textura ou detalhe → combina com LISO ou ESTAMPADO
  • ESTAMPADO    = peça com estampa (floral, geométrica, animal print…)
  • LISO TRABALHADO = peça lisa MAS com textura/detalhe no tecido (lurex, jacquard, textura casca, franja, crochê, tricô)
    ⚠️ LISO TRABALHADO em saída de praia pode ser peça de malha/crochê — NÃO é saída de praia de lycra.
    Use a LINHA para confirmar: LINHA:AGUA = praia, LINHA:VIDA = roupa/lifestyle.

CAMPO LINHA (qual universo da marca):
  • AGUA      = linha praia/resort — biquínis, maiôs, saídas de praia, cangas
  • VIDA      = lifestyle/roupa casual — vestidos, calças, blusas para o dia a dia
  • LUZ       = festa/eventos — vestidos sofisticados, looks de noite
  • (vazio)   = verificar TIPO e COLECAO

CAMPO MIX = nome do mix/coleção do produto (ex: "Báltico", "Ipanema", "Copa")
  → Sutiã + calcinha DEVEM ter o MESMO valor em COLECAO (ou mesmo nome na COLECAO)
  → Biquíni Sutiã Faixa Báltico + Biquíni Calcinha Báltico = par correto ✓
  → Biquíni Sutiã Copa + Biquíni Calcinha Báltico = ERRADO ✗

CAMPO TIPO:
  • PRAIA_TOP    = sutiã de biquíni — precisa de PRAIA_BOTTOM da mesma COLECAO
  • PRAIA_BOTTOM = calcinha de biquíni — precisa de PRAIA_TOP da mesma COLECAO
  • SAIDA        = saída de praia (kimono, canga, túnica, pareo) — complemento de biquíni/maiô
  • MAIO         = maiô inteiro — não precisa de calcinha separada; combina com SAIDA
  • VESTIDO      = vestido ou macacão — look completo sozinho + acessório
  • TOP/ROUPA/BOTTOM = peças de roupa casual (Linha VIDA)

═══════════════════════════════════════════
REGRAS DE PAREAMENTO (obrigatórias)
═══════════════════════════════════════════

1. BIQUÍNI = PRAIA_TOP + PRAIA_BOTTOM com MIX IDÊNTICO. Sempre.
   Nunca sugira PRAIA_TOP sem o PRAIA_BOTTOM correspondente (e vice-versa).

2. ESTAMPARIA:
   • ESTAMPADO + LISO = look certo ✓
   • ESTAMPADO + LISO TRABALHADO = verificar se cores combinam ✓
   • ESTAMPADO + ESTAMPADO (estampas diferentes) = ERRADO ✗
   • LISO + LISO = sempre ok ✓
   • LISO TRABALHADO + LISO = ok (mas atenção à LINHA — não misturar praia com lifestyle)

3. QUANDO CLIENTE PEDE COMPLEMENTO (tem X, quer Y):
   "Tenho o biquíni Báltico Marrom, quero saída"
   → Primeiro: saídas MIX:Báltico (mesma coleção)
   → Depois: saídas LISO com COR que combina com marrom (off white, bege, caramelo, areia)
   → NUNCA: saídas de coleção diferente com estampa diferente

4. MIX COMPLETO DE ESTAMPA:
   Se cliente pede "look camuflado" → TODAS as peças devem ser camuflado (mesma COLECAO ou estampa igual)
   Se cliente pede "look floral" → base floral + LISO que combina com as cores do floral

5. SAÍDA DE PRAIA:
   Verifique LINHA:AGUA — saídas com LINHA:VIDA são peças de lifestyle, não saída de praia
   LISO TRABALHADO + LINHA:VIDA = crochê/malha de roupa, não saída de praia
   LISO TRABALHADO + LINHA:AGUA = saída em tecido especial (ok para praia)

═══════════════════════════════════════════
MATCH DE CORES 2026
═══════════════════════════════════════════
Marrom/Báltico → off white, bege, caramelo, areia, azul bebê, rosa (TENDÊNCIA FORTE)
Azul bebê → marrom, chocolate, cinza, rosa blush, branco, prata
Verde oliva → bege, areia, off white, marrom, azul petróleo, vinho
Vermelho → rosa, azul, cinza, preto, bege
Neutros (combinam com TUDO): Off White · Bege · Areia · Creme · Branco

═══════════════════════════════════════════
ESTRUTURA DO LOOK POR OCASIÃO
═══════════════════════════════════════════
PRAIA/RESORT:
  Opção A: MAIO (LINHA:AGUA) + SAIDA (MIX igual OU LISO neutro) + sandália + acessório
  Opção B: PRAIA_TOP + PRAIA_BOTTOM (MIX idêntico) + SAIDA + sandália
  → Inclua SEMPRE a saída de praia — é a peça-chave para praia

FESTA/JANTAR/EVENTO: VESTIDO (LINHA:LUZ) + sandália elegante + bolsa + acessório
  → ZERO biquíni, ZERO saída de praia

CASUAL/DIA A DIA: TOP + BOTTOM (LINHA:VIDA) + sandália + acessório

MENSAGEM: 2 frases diretas, persuasivas, começando com "{client_name}," (nunca "querida")
Se promoção: destaque o quanto economiza.
Se complemento: "Já que você tem [X], essa [Y] é perfeita para completar o look."

RETORNE APENAS JSON (sem markdown, sem texto antes/depois):
{{"message":"frase calorosa máx 2 linhas","products":[{{"id":"ID exato","name":"NOME exato","price":"PRECO exato","list_price":"DE: se existir, senão vazio","image_url":"IMG exata","url":"URL exata"}}]}}"""

    # ── 10. Monta histórico de conversa para a IA ────────────────────────────
    ai_messages = []
    for h in (payload.history or [])[-6:]:
        role = "user" if h.role == "user" else "assistant"
        content = h.content
        if role == "assistant" and content.startswith("{"):
            try:
                import json as _j
                content = _j.loads(content).get("message", content)
            except Exception:
                pass
        ai_messages.append({"role": role, "content": content[:400]})
    ai_messages.append({"role": "user", "content": f"Pedido de {client_name}: {message}"})

    # ── 11. Chama Claude Haiku ───────────────────────────────────────────────
    try:
        async with httpx.AsyncClient(timeout=25) as http:
            resp = await http.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key":          anthropic_key,
                    "anthropic-version":  "2023-06-01",
                    "content-type":       "application/json",
                },
                json={
                    "model":    "claude-haiku-4-5-20251001",
                    "max_tokens": 1024,
                    "system":   system_prompt,
                    "messages": ai_messages,
                },
            )
        if resp.status_code != 200:
            raise ValueError(f"API error {resp.status_code}")
        ai_text = resp.json().get("content", [{}])[0].get("text", "")
    except Exception:
        return {
            "message": f"Olá, {client_name}! Separei algumas peças para você.",
            "products": catalog_products[:limit],
        }

    # ── 12. Parse JSON robusto ───────────────────────────────────────────────
    result = None
    for attempt in [ai_text, ai_text[ai_text.find("{"):ai_text.rfind("}")+1]]:
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

    # ── 13. Resolve image_url e url pelos dados reais do catálogo ────────────
    catalog_by_id = {p["product_id"]: p for p in catalog_products}
    clean_products = []
    for p in result.get("products", [])[:limit]:
        pid  = str(p.get("id") or p.get("product_id") or "")
        real = catalog_by_id.get(pid, {})
        clean_products.append({
            "id":           pid,
            "name":         p.get("name")       or real.get("name")       or "",
            "price":        p.get("price")       or real.get("price")      or "",
            "list_price":   p.get("list_price")  or real.get("list_price") or "",
            "category":     p.get("category")    or real.get("category")   or "",
            "image_url":    real.get("image_url") or (p.get("image_url") or "").split("?")[0],
            "url":          real.get("url")       or p.get("url")          or "",
            "is_complement": bool(p.get("is_complement")),
        })
    result["products"] = clean_products

    # ── 14. Tracking + memória (background, não bloqueia resposta) ───────────
    try:
        from services.closet_db import AsyncSessionLocal
        from sqlalchemy import text as _txt3
        async with AsyncSessionLocal() as db:
            await db.execute(_txt3(
                "INSERT INTO recommendation_clicks (email, product_id, occasion, source, clicked_at) "
                "VALUES (:e, 'stylist_chat', :occ, 'widget_stylist_chat', NOW())"
            ), {"e": email, "occ": message[:100]})
            novo_resumo = (profile_text + f"\nÚltimo pedido: {message[:80]}")[:500]
            await db.execute(_txt3("""
                INSERT INTO client_memory
                  (email, ocasioes_frequentes, pedidos_frequentes, resumo_ia,
                   total_conversas, ultima_conversa)
                VALUES (:email, :ocasioes, :pedidos, :resumo, 1, NOW())
                ON CONFLICT (email) DO UPDATE SET
                  ocasioes_frequentes = COALESCE(NULLIF(:ocasioes,''), client_memory.ocasioes_frequentes),
                  pedidos_frequentes = CASE
                    WHEN client_memory.pedidos_frequentes IS NULL THEN :pedidos
                    WHEN :pedidos != '' THEN client_memory.pedidos_frequentes || ', ' || :pedidos
                    ELSE client_memory.pedidos_frequentes
                  END,
                  resumo_ia = :resumo,
                  total_conversas = client_memory.total_conversas + 1,
                  ultima_conversa = NOW()
            """), {
                "email":    email,
                "ocasioes": "praia" if is_beach else ("festa" if is_party else ""),
                "pedidos":  message[:80],
                "resumo":   novo_resumo,
            })
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
    """Métricas ricas de conversão para o dashboard."""
    from services.closet_db import AsyncSessionLocal
    from sqlalchemy import text

    try:
        async with AsyncSessionLocal() as s:

            # ── Totais gerais ────────────────────────────────────────────
            r = await s.execute(text("""
                SELECT
                  COUNT(*) as total,
                  COUNT(DISTINCT email) as unique_users,
                  COUNT(CASE WHEN source = 'widget_stylist_chat' THEN 1 END) as chat_sessions,
                  COUNT(CASE WHEN source = 'widget_pdp' THEN 1 END) as pdp_clicks,
                  COUNT(CASE WHEN clicked_at >= NOW() - INTERVAL '7 days' THEN 1 END) as last_7d,
                  COUNT(CASE WHEN clicked_at >= NOW() - INTERVAL '1 day' THEN 1 END) as last_24h
                FROM recommendation_clicks
            """))
            totals = r.fetchone()

            # ── Taxa de conversão: clientes que usaram widget E compraram depois ──
            r_conv = await s.execute(text("""
                SELECT
                  COUNT(DISTINCT rc.email) as widget_users,
                  COUNT(DISTINCT o.email) as converted,
                  COALESCE(SUM(o.total_value), 0) as revenue_after_chat,
                  COUNT(DISTINCT o.order_id) as orders_after_chat
                FROM recommendation_clicks rc
                LEFT JOIN orders o ON (
                  o.email = rc.email
                  AND o.creation_date >= rc.clicked_at
                  AND o.creation_date <= rc.clicked_at + INTERVAL '72 hours'
                  AND o.status NOT IN ('canceled', 'canceling')
                )
                WHERE rc.source = 'widget_stylist_chat'
            """))
            conv = r_conv.fetchone()
            widget_users = conv[0] or 0
            converted = conv[1] or 0
            revenue_after = float(conv[2] or 0)
            orders_after = conv[3] or 0
            conversion_rate = round((converted / widget_users * 100), 1) if widget_users > 0 else 0

            # ── Ranking de clientes: uso do widget + compras ─────────────
            r_ranking = await s.execute(text("""
                SELECT
                  rc.email,
                  COUNT(DISTINCT DATE(rc.clicked_at)) as dias_de_uso,
                  COUNT(rc.id) as total_interacoes,
                  MAX(rc.clicked_at) as ultima_interacao,
                  COUNT(DISTINCT o.order_id) as total_pedidos,
                  COALESCE(SUM(o.total_value), 0) as total_gasto
                FROM recommendation_clicks rc
                LEFT JOIN orders o ON (
                  o.email = rc.email
                  AND o.status NOT IN ('canceled', 'canceling')
                )
                WHERE rc.source = 'widget_stylist_chat'
                GROUP BY rc.email
                ORDER BY total_interacoes DESC, total_gasto DESC
                LIMIT 20
            """))
            ranking = []
            for row in r_ranking.fetchall():
                email = row[0] or ""
                at_idx = email.find("@")
                masked = (email[:3] + "***" + email[at_idx:]) if at_idx > 0 else email[:6] + "***"
                ranking.append({
                    "email": masked,
                    "dias_de_uso": row[1],
                    "interacoes": row[2],
                    "ultima_interacao": str(row[3])[:10] if row[3] else "",
                    "pedidos": row[4],
                    "total_gasto": float(row[5] or 0),
                })

            # ── Por fonte ────────────────────────────────────────────────
            r1 = await s.execute(text("""
                SELECT source, COUNT(*) as clicks, COUNT(DISTINCT email) as unique_users
                FROM recommendation_clicks
                GROUP BY source ORDER BY clicks DESC
            """))
            by_source = [{"source": r.source, "clicks": r.clicks, "unique_users": r.unique_users}
                        for r in r1.fetchall()]

            # ── O que pedem no chat ──────────────────────────────────────
            r2 = await s.execute(text("""
                SELECT occasion, COUNT(*) as cnt
                FROM recommendation_clicks
                WHERE source = 'widget_stylist_chat'
                  AND occasion IS NOT NULL AND occasion != '' AND occasion != 'stylist_chat'
                GROUP BY occasion ORDER BY cnt DESC LIMIT 10
            """))
            top_requests = [{"request": r.occasion, "count": r.cnt} for r in r2.fetchall()]

            # ── Top produtos clicados ────────────────────────────────────
            r3 = await s.execute(text("""
                SELECT rc.product_id, COALESCE(cp.name, rc.product_id) as name,
                       cp.category, COUNT(*) as clicks
                FROM recommendation_clicks rc
                LEFT JOIN catalog_products cp ON cp.product_id = rc.product_id
                WHERE rc.product_id != 'stylist_chat'
                  AND rc.source != 'widget_stylist_chat'
                GROUP BY rc.product_id, cp.name, cp.category
                ORDER BY clicks DESC LIMIT 10
            """))
            top_products = [{"product_id": r.product_id, "name": r.name,
                           "category": r.category, "clicks": r.clicks}
                           for r in r3.fetchall()]

            # ── Horários de pico ─────────────────────────────────────────
            r4 = await s.execute(text("""
                SELECT EXTRACT(HOUR FROM clicked_at AT TIME ZONE 'America/Sao_Paulo') as hora,
                       COUNT(*) as clicks
                FROM recommendation_clicks GROUP BY hora ORDER BY hora
            """))
            by_hour = [{"hour": int(r.hora), "clicks": r.clicks} for r in r4.fetchall()]

            # ── Por dia últimos 30d ──────────────────────────────────────
            r5 = await s.execute(text("""
                SELECT DATE(clicked_at AT TIME ZONE 'America/Sao_Paulo') as day,
                       COUNT(*) as clicks, COUNT(DISTINCT email) as users
                FROM recommendation_clicks
                WHERE clicked_at >= NOW() - INTERVAL '30 days'
                GROUP BY day ORDER BY day DESC
            """))
            by_day = [{"day": str(r.day), "clicks": r.clicks, "users": r.users}
                      for r in r5.fetchall()]

        return {
            "total_clicks": totals[0] or 0,
            "unique_users": totals[1] or 0,
            "chat_sessions": totals[2] or 0,
            "pdp_clicks": totals[3] or 0,
            "last_7d": totals[4] or 0,
            "last_24h": totals[5] or 0,
            "conversion_rate": conversion_rate,
            "converted_users": converted,
            "revenue_after_chat": revenue_after,
            "orders_after_chat": orders_after,
            "widget_users": widget_users,
            "ranking": ranking,
            "by_source": by_source,
            "top_requests": top_requests,
            "top_products": top_products,
            "by_hour": by_hour,
            "by_day": by_day,
        }
    except Exception as e:
        return {"total_clicks": 0, "unique_users": 0, "chat_sessions": 0,
                "pdp_clicks": 0, "last_7d": 0, "last_24h": 0,
                "conversion_rate": 0, "converted_users": 0,
                "revenue_after_chat": 0, "orders_after_chat": 0,
                "widget_users": 0, "ranking": [],
                "by_source": [], "top_requests": [], "top_products": [],
                "by_hour": [], "by_day": [], "error": str(e)}



# ─── Atributos de Produtos (base para a IA) ────────────────────────────────

class ProductAttributeRequest(BaseModel):
    product_id: str
    ocasiao_ideal: str = ""
    estilo: str = ""
    combina_com: str = ""        # IDs separados por vírgula
    nao_combina_com: str = ""
    colecao_mix: str = ""
    tipo_peca: str = ""
    clima: str = ""
    corpo: str = ""
    tags: str = ""
    notas_ia: str = ""


@router.post("/product-attributes")
async def upsert_product_attributes(payload: ProductAttributeRequest):
    """
    Cadastra ou atualiza atributos de produto para a IA.
    Use para enriquecer o catálogo com informações de ocasião,
    combinações, estilo e notas para a IA.
    """
    from services.closet_db import AsyncSessionLocal
    from sqlalchemy import text

    try:
        async with AsyncSessionLocal() as db:
            await db.execute(text("""
                INSERT INTO product_attributes
                  (product_id, ocasiao_ideal, estilo, combina_com, nao_combina_com,
                   colecao_mix, tipo_peca, clima, corpo, tags, notas_ia, updated_at)
                VALUES
                  (:product_id, :ocasiao_ideal, :estilo, :combina_com, :nao_combina_com,
                   :colecao_mix, :tipo_peca, :clima, :corpo, :tags, :notas_ia, NOW())
                ON CONFLICT (product_id) DO UPDATE SET
                  ocasiao_ideal = COALESCE(NULLIF(:ocasiao_ideal,''), product_attributes.ocasiao_ideal),
                  estilo = COALESCE(NULLIF(:estilo,''), product_attributes.estilo),
                  combina_com = COALESCE(NULLIF(:combina_com,''), product_attributes.combina_com),
                  nao_combina_com = COALESCE(NULLIF(:nao_combina_com,''), product_attributes.nao_combina_com),
                  colecao_mix = COALESCE(NULLIF(:colecao_mix,''), product_attributes.colecao_mix),
                  tipo_peca = COALESCE(NULLIF(:tipo_peca,''), product_attributes.tipo_peca),
                  clima = COALESCE(NULLIF(:clima,''), product_attributes.clima),
                  corpo = COALESCE(NULLIF(:corpo,''), product_attributes.corpo),
                  tags = COALESCE(NULLIF(:tags,''), product_attributes.tags),
                  notas_ia = COALESCE(NULLIF(:notas_ia,''), product_attributes.notas_ia),
                  updated_at = NOW()
            """), payload.model_dump())
            await db.commit()
        return {"ok": True, "product_id": payload.product_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/product-attributes/{product_id}")
async def get_product_attributes(product_id: str):
    """Retorna os atributos enriquecidos de um produto."""
    from services.closet_db import AsyncSessionLocal
    from sqlalchemy import text
    try:
        async with AsyncSessionLocal() as db:
            r = await db.execute(text(
                "SELECT * FROM product_attributes WHERE product_id=:pid"
            ), {"pid": product_id})
            row = r.mappings().fetchone()
            return dict(row) if row else {"product_id": product_id, "found": False}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/client-memory/{email_param}")
async def get_client_memory(email_param: str):
    """Retorna a memória acumulada de um cliente."""
    from services.closet_db import AsyncSessionLocal
    from sqlalchemy import text
    email_clean = normalize_email(email_param)
    try:
        async with AsyncSessionLocal() as db:
            r = await db.execute(text(
                "SELECT * FROM client_memory WHERE email=:e"
            ), {"e": email_clean})
            row = r.mappings().fetchone()
            return dict(row) if row else {"email": email_clean, "found": False}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/client-memory/{email_param}")
async def update_client_memory(email_param: str, data: dict):
    """
    Atualiza manualmente a memória de um cliente.
    Útil para corrigir preferências ou adicionar contexto.
    """
    from services.closet_db import AsyncSessionLocal
    from sqlalchemy import text
    email_clean = normalize_email(email_param)
    allowed = {"cores_favoritas","tamanhos","estilos","ocasioes_frequentes",
               "pedidos_frequentes","categorias_favoritas","colecoes_favoritas",
               "preferencias_confirmadas","resumo_ia"}
    updates = {k: v for k, v in data.items() if k in allowed}
    if not updates:
        raise HTTPException(status_code=400, detail="Nenhum campo válido para atualizar")
    try:
        async with AsyncSessionLocal() as db:
            set_clause = ", ".join(f"{k}=:{k}" for k in updates)
            updates["email"] = email_clean
            await db.execute(text(
                f"UPDATE client_memory SET {set_clause} WHERE email=:email"
            ), updates)
            await db.commit()
        return {"ok": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/debug")
async def debug_customer_closet(email: str):
    email = normalize_email(email)
    if not email:
        raise HTTPException(status_code=400, detail="E-mail é obrigatório")

    return await get_customer_closet_payload(email)
