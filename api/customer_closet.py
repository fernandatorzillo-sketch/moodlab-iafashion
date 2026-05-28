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

    # ── 1. Perfil da cliente — closet + pedidos reais + memória IA ─────────
    # Três fontes em paralelo para máxima personalização:
    # 1) customer_closet_items: peças que a cliente já tem
    # 2) order_items + catalog_products: histórico real de compras na VTEX
    # 3) client_memory: resumo acumulado de conversas anteriores
    try:
        from services.closet_db import AsyncSessionLocal
        from sqlalchemy import text as _txt
        from collections import Counter

        async with AsyncSessionLocal() as db:
            # Nome
            r = await db.execute(_txt(
                "SELECT name FROM customers WHERE email=:e LIMIT 1"
            ), {"e": email})
            row = r.fetchone()
            if row and row[0]:
                client_name = row[0].split()[0]

            # Fonte 1: closet virtual (peças que já tem)
            r2 = await db.execute(_txt("""
                SELECT cp.color, cp.size, cp.print_name, cp.collection,
                       cci.name, cp.category, cp.product_type
                FROM customer_closet_items cci
                LEFT JOIN catalog_products cp ON cp.sku_id = cci.sku_id
                WHERE cci.email = :e
                ORDER BY cci.purchase_count DESC LIMIT 30
            """), {"e": email})
            closet_rows = r2.fetchall()

            # Fonte 2: pedidos reais (histórico de compras na VTEX)
            order_rows = []
            try:
                ro = await db.execute(_txt("""
                    SELECT cp.color, cp.size, cp.product_type, cp.occasion,
                           oi.name, cp.category
                    FROM order_items oi
                    INNER JOIN orders o ON o.order_id = oi.order_id
                    LEFT JOIN catalog_products cp ON cp.product_id::text = oi.product_id::text
                    WHERE o.email = :e
                      AND o.status NOT IN ('canceled','canceling')
                    ORDER BY o.creation_date DESC LIMIT 40
                """), {"e": email})
                order_rows = ro.fetchall()
            except Exception:
                pass

            colors, sizes, cats, occasions_bought = Counter(), Counter(), Counter(), Counter()
            closet_tops = []

            # Processa closet
            for color, size, print_n, coll, name, cat, ptype in closet_rows:
                if color: colors[color.lower()] += 1
                if size:  sizes[size.upper()] += 1
                if cat:   cats[cat.lower()] += 1
                if name:
                    n, pt = name.lower(), (ptype or "").upper()
                    if pt in ("BIQUINI SUTIA","SUTIA") or any(
                        t in n for t in ["sutiã","sutia","bandeau","cortininha","frente única","faixa"]
                    ):
                        closet_tops.append({"name": name, "collection": coll or ""})

            # Processa pedidos reais
            for color, size, ptype, occ, name, cat in order_rows:
                if color: colors[color.lower()] += 1
                if size:  sizes[size.upper()] += 1
                if occ:   occasions_bought[occ.upper()] += 1
                if cat:   cats[cat.lower()] += 1

            parts = []
            if colors:   parts.append(f"Cores favoritas: {', '.join(c for c,_ in colors.most_common(4))}")
            if sizes:    parts.append(f"Tamanhos: {', '.join(s for s,_ in sizes.most_common(2))}")
            if cats:     parts.append(f"Categorias frequentes: {', '.join(c for c,_ in cats.most_common(3))}")
            if occasions_bought:
                top_occ = [o for o,_ in occasions_bought.most_common(3)]
                parts.append(f"Ocasiões que já comprou: {', '.join(top_occ)}")
            if closet_tops:
                parts.append(f"Sutiãs/tops no closet (sugerir calcinha do mesmo mix): "
                             + ", ".join(t["name"] for t in closet_tops[:2]))
            if order_rows and not closet_rows:
                parts.append(f"Histórico: {len(order_rows)} compras anteriores registradas")
            profile_text = "\n".join(parts)

            # Memória IA acumulada (conversas anteriores)
            mr = await db.execute(_txt(
                "SELECT resumo_ia, cores_favoritas, tamanhos, ocasioes_frequentes "
                "FROM client_memory WHERE email=:e LIMIT 1"
            ), {"e": email})
            mrow = mr.fetchone()
            if mrow and mrow[0]:
                mem_parts = [f"Memória de conversas anteriores: {mrow[0]}"]
                if mrow[1]: mem_parts.append(f"Cores que gosta: {mrow[1]}")
                if mrow[2] and not sizes: mem_parts.append(f"Tamanho habitual: {mrow[2]}")
                if mrow[3]: mem_parts.append(f"Ocasiões frequentes: {mrow[3]}")
                memory_text = " | ".join(mem_parts)
    except Exception:
        pass

    # ── 2. Catálogo — query por contexto da conversa ────────────────────────
    # Detecta contexto ANTES da query para carregar só o necessário
    # (evita pegar 120 produtos genéricos e filtrar depois)
    _msg_pre = (message + " " + " ".join(
        h.content for h in (payload.history or [])[-8:] if h.role == "user"
    )).lower()
    _is_beach_pre  = any(t in _msg_pre for t in ["praia","biquini","biquíni","maio","maiô","resort","piscina","mar","surf","sunga","saída","saida","canga","kimono"])
    _is_party_pre  = any(t in _msg_pre for t in ["festa","balada","jantar","evento","sofisticad","formatura","casamento","barco","iate","reveillon"])
    _is_sale_pre   = any(t in _msg_pre for t in ["promoção","promocao","promo","desconto","sale","oferta","mais barato","barato"])
    _is_cold_pre   = any(t in _msg_pre for t in ["frio","inverno","tricô","trico","casaco"])
    _is_casual_pre = any(t in _msg_pre for t in ["casual","dia a dia","passeio","shopping","trabalho"])

    # Tipos de produto relevantes por contexto
    # Sempre inclui calçados, bolsas e acessórios como complementos de look
    _COMPLEMENTS = ("SANDALIA","SANDÁLIAS","CALCADO","CALÇADOS","CHINELO","RASTEIRA",
                    "BOLSA","NECESSAIRE","BRINCO","COLAR","PULSEIRA","ANEL",
                    "CHAPEU/BONE/VISEIRA","CHAPÉU","OCULOS","ÓCULOS","CINTO","LENCO")
    _BEACH_TYPES  = ("BIQUINI SUTIA","SUTIA","BIQUINI CALCINHA","CALCINHA",
                     "MAIO","SAIDA DE PRAIA","SAIDA DE BANHO","CAPA/CAPA KIMONO",
                     "CAPA","CANGA","TUNICA","PAREO") + _COMPLEMENTS
    _PARTY_TYPES  = ("VESTIDO","MACACÃO","MACACAO","CHEMISE","BLUSA/TOP","BLUSA",
                     "TOP","CAMISETA","CAMISA","BODY","CROPPED","CALCA","SAIA") + _COMPLEMENTS
    _COLD_TYPES   = ("JAQUETA/BLAZER/PARKA","JAQUETA","BLAZER","MOLETOM","TRICO","TRICÔ",
                     "VESTIDO","CALCA","SAIA","BLUSA/TOP","BLUSA") + _COMPLEMENTS
    _CASUAL_TYPES = ("VESTIDO","MACACÃO","BLUSA/TOP","BLUSA","TOP","CAMISETA","CAMISA",
                     "BODY","CROPPED","CALCA","SAIA","SHORT","BERMUDA") + _COMPLEMENTS

    # Monta filtro de product_type para a query
    # SALE não zera o contexto — se estava pedindo jantar + sale, filtra vestidos em sale
    if _is_beach_pre and not _is_party_pre:
        _type_filter = _BEACH_TYPES
    elif _is_party_pre and not _is_beach_pre:
        _type_filter = _PARTY_TYPES
    elif _is_cold_pre:
        _type_filter = _COLD_TYPES
    elif _is_casual_pre:
        _type_filter = _CASUAL_TYPES
    else:
        _type_filter = None  # contexto ambíguo — sem filtro de tipo

    catalog_products: list[dict] = []
    try:
        from services.closet_db import AsyncSessionLocal
        from sqlalchemy import text as _txt2

        async with AsyncSessionLocal() as db:
            # Base: sempre exclui infantil, casa e gênero errado
            # Detecta gênero do cliente pelo closet ou email para filtrar
            _gender_clause = ""
            if profile_text:
                # Feminino é o default para Água de Coco — filtra masculino salvo se pediu
                _msg_has_masc = any(t in _msg_pre for t in ["masculino","marido","namorado","pai","irmão"])
                if not _msg_has_masc:
                    _gender_clause = "AND UPPER(COALESCE(cp.gender,'')) NOT IN ('MASCULINO')"

            _base_where = f"""
                cp.is_active = 1
                AND cp.image_url IS NOT NULL AND cp.image_url != ''
                AND cp.product_url IS NOT NULL AND cp.product_url != ''
                AND cp.price > 0
                AND inv.is_available = 1 AND inv.quantity > 0
                AND LOWER(COALESCE(cp.department,'')) NOT IN ('infantil','casa','kit','kids','bebe','bebê')
                AND LOWER(COALESCE(cp.category,'')) NOT LIKE '%infantil%'
                AND LOWER(COALESCE(cp.category,'')) NOT LIKE '%kids%'
                AND LOWER(COALESCE(cp.category,'')) NOT LIKE '%casa%'
                {_gender_clause}
            """

            if _type_filter:
                _placeholders = ", ".join(f":t{i}" for i in range(len(_type_filter)))
                _params = {f"t{i}": v for i, v in enumerate(_type_filter)}
                _type_clause = f"AND UPPER(cp.product_type) IN ({_placeholders})"
                _order = "ORDER BY RANDOM()"
                _limit = "LIMIT 80"
            else:
                _params = {}
                _type_clause = ""
                _order = "ORDER BY RANDOM()"
                _limit = "LIMIT 100"

            # SALE: filtra por desconto MAS sempre mantém o contexto de ocasião
            # Regra: list_price > price (desconto real) OU department sale
            # O _type_clause de ocasião (jantar/praia/festa) NUNCA é removido
            if _is_sale_pre:
                _base_where += (
                    " AND ("
                    "  (cp.list_price IS NOT NULL AND cp.list_price > cp.price)"
                    "  OR LOWER(COALESCE(cp.department,'')) LIKE 'sale%'"
                    ")"
                )
                # Mantém _type_clause intacto — contexto de ocasião prevalece
                # Se não há contexto de tipo, amplia para pegar mais opções de SALE
                if not _type_filter:
                    _type_clause = ""
                _order = "ORDER BY RANDOM()"
                _limit = "LIMIT 60"

            _sql = f"""
                SELECT cp.product_id, cp.name, cp.price, cp.list_price,
                       cp.category, cp.product_type, cp.image_url, cp.product_url,
                       cp.color, cp.collection, cp.occasion, cp.print_name,
                       cp.gender, cp.department
                FROM catalog_products cp
                INNER JOIN inventory_by_sku inv ON inv.sku_id = cp.sku_id
                WHERE {_base_where}
                {_type_clause}
                {_order}
                {_limit}
            """
            r3 = await db.execute(_txt2(_sql), _params)
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

                # ── Correção por ocasião VTEX — tem prioridade sobre product_type ──
                # Ex: product_type=VESTIDO + ocasiao=SAIDA DE PRAIA → tipo deve ser SAIDA
                # A ocasião cadastrada na VTEX é mais específica que o tipo genérico
                _OC_OVERRIDE = {
                    "SAIDA DE PRAIA":    "SAIDA",
                    "SAIDA DE BANHO":    "SAIDA",
                    "CAPA/CAPA KIMONO":  "SAIDA",
                    "CANGA":             "SAIDA",
                    "TUNICA":            "SAIDA",
                    "BIQUINI SUTIA":     "PRAIA_TOP",
                    "BIQUINI CALCINHA":  "PRAIA_BOTTOM",
                    "MAIO":              "MAIO",
                    "SUNGA":             "SUNGA",
                }
                if oc in _OC_OVERRIDE:
                    tipo = _OC_OVERRIDE[oc]

                # Linha: detecta pelo campo collection se vier AGUA/VIDA/LUZ
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
        h.content.lower() for h in (payload.history or [])[-8:] if h.role == "user"
    )
    ctx = msg_lower + " " + hist_user  # contexto acumulado para detectar ocasião

    is_beach  = any(t in ctx for t in ["praia","biquini","biquíni","maio","maiô","resort","piscina","mar","surf","sunga"])
    is_cold   = any(t in ctx for t in ["frio","inverno","tricô","trico","suéter","casaco"])
    is_party  = any(t in ctx for t in ["festa","balada","jantar","evento","chique","sofisticad","formatura","casamento","aniversario","barco","iate","reveillon"])
    is_casual = any(t in ctx for t in ["casual","dia a dia","passeio","shopping","trabalho","escritorio"])
    # SALE: só mensagem atual (cliente pode mudar de ideia)
    is_sale   = any(t in msg_lower for t in ["promoção","promocao","promo","desconto","sale","oferta","mais barato","barato","economizar"])
    is_saida  = any(t in ctx for t in ["saída","saida","capa","kimono","canga","túnica","tunica","pareo","kaftan"])

    # Detecta estampa/mix específico pedido (ex: "camuflado", "báltico", "floral")
    # Pré-boosting Python: garante que produtos do mix pedido chegam ao topo do catálogo
    _estampa_keywords = [
        "camuflado","báltico","baltico","copa","ipanema","java","floral","listrad",
        "animal print","onça","oncinha","tie dye","patchwork","xadrez","bolinhas",
        "radiante","kairos","atlântico","atlantico","tropical","coqueiro","geometr",
    ]
    requested_mix = ""
    for kw in _estampa_keywords:
        if kw in ctx:
            requested_mix = kw
            break

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

    # ── 6. Filtro SALE — usa list_price real + department='Sale' ──────────────
    # A query já pré-filtrou por list_price/sale quando is_sale_pre=True
    # Aqui só garantimos que os produtos têm desconto ou são do dept Sale
    if is_sale:
        sale_ctx = [p for p in filtered
                    if p.get("list_price")
                    or "sale" in (p.get("department") or "").lower()]
        if len(sale_ctx) >= 3:
            filtered = sale_ctx

    # ── 7. Boost por mix/estampa pedido — produtos com a estampa vão ao topo ──
    if requested_mix:
        def _mix_score(p):
            n = (p.get("name") or "").lower()
            return 2 if requested_mix in n else (1 if p.get("print_name","").upper() == "LISO" else 0)
        filtered.sort(key=_mix_score, reverse=True)

    # Balanceia por tipo para diversidade
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

    page_ctx  = f"Página atual: {payload.page_context}" if payload.page_context else ""
    mix_hint  = (
        f"ATENÇÃO MIX: cliente pediu '{requested_mix}'. "
        f"Priorize produtos cujo NOME contenha '{requested_mix}'. "
        f"Lisas neutras só como complemento — NUNCA outra estampa no lugar."
    ) if requested_mix else ""
    sale_hint = (
        "PROMOÇÃO SOLICITADA: use APENAS produtos com campo DE: preenchido ou do departamento SALE. "
        "Para cada produto com desconto: mencione De R$X por R$Y. "
        "MANTENHA O CONTEXTO DA CONVERSA: se falávamos de festa, mostre vestidos em promoção. "
        "Se falávamos de praia, mostre biquínis/saídas em promoção. "
        "NUNCA misture adulto feminino com infantil ou masculino no mesmo look. "
        "Monte um look coerente mesmo dentro das peças em promoção."
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
{mix_hint}

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

CAMPO MIX = palavra-chave no NOME do produto que identifica a coleção/estampa
  → Leia o NOME: "Biquíni Sutiã Faixa BÁLTICO Marrom" → mix = Báltico
  → Sutiã + calcinha DEVEM ter a MESMA palavra-chave no NOME
  → Ex: "Sutiã Faixa Báltico" + "Calcinha Báltico" = ✓ mesmo mix
  → Ex: "Sutiã Copa" + "Calcinha Báltico" = ✗ mix diferente, PROIBIDO

QUANDO CLIENTE MENCIONA UMA ESTAMPA/MIX (ex: "camuflado", "báltico", "java"):
  1. PROCURE nos NOMES do catálogo a palavra mencionada
  2. Sugira todas as peças desse mix disponíveis (saída, calcinha, sutiã...)
  3. Se não achar complemento do mesmo mix: lisas NEUTRAS que combinam — NUNCA outra estampa
  4. JAMAIS substitua "camuflado" por "estampado vermelho" ou qualquer outra estampa

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

4. ESTAMPA ESPECÍFICA PEDIDA (camuflado, floral, listrado, tie-dye, bolinhas...):
   → Filtre o catálogo pelos produtos cujo NOME contém essa palavra
   → Sugira PRIMEIRO todas as peças desse mix: saída camuflada, sutiã camuflado...
   → Se não houver saída com esse nome: peças LISAS neutras (verde, bege, off white)
   → NUNCA substitua a estampa pedida por outra estampa diferente

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

            # ── O que os clientes pedem no chat (mensagens reais) ──────────
            # Filtra apenas as mensagens de chat (product_id = 'stylist_chat')
            # excluindo os cliques em produtos (que têm product_id real)
            r2 = await s.execute(text("""
                SELECT occasion, COUNT(*) as cnt
                FROM recommendation_clicks
                WHERE source = 'widget_stylist_chat'
                  AND product_id = 'stylist_chat'
                  AND occasion IS NOT NULL
                  AND LENGTH(TRIM(occasion)) > 3
                GROUP BY occasion ORDER BY cnt DESC LIMIT 15
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
