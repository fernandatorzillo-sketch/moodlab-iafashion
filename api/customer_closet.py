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

    email = str(payload.email or "").strip().lower()
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

    # ── Carrega memória prévia do cliente ────────────────────────────────
    memory_text = ""
    try:
        from services.closet_db import AsyncSessionLocal as _ASL_mem
        from sqlalchemy import text as _mtxt
        async with _ASL_mem() as _mdb:
            _mr = await _mdb.execute(_mtxt(
                "SELECT resumo_ia FROM client_memory WHERE email=:e LIMIT 1"
            ), {"e": email})
            _mrow = _mr.fetchone()
            if _mrow and _mrow[0]:
                memory_text = f"Memória prévia: {_mrow[0]}"
    except Exception:
        pass

    # ── 2. Catálogo (query simples, sem JOIN pesado) ───────────────────────
    catalog_products = []
    try:
        from services.closet_db import AsyncSessionLocal
        from sqlalchemy import text as _txt2

        async with AsyncSessionLocal() as db:
            r3 = await db.execute(_txt2("""
                SELECT cp.product_id, cp.name, cp.price, cp.list_price,
                       cp.category, cp.product_type, cp.image_url, cp.product_url,
                       cp.color, cp.collection, cp.occasion, cp.print_name, cp.gender
                FROM catalog_products cp
                INNER JOIN inventory_by_sku inv ON inv.sku_id = cp.sku_id
                WHERE cp.is_active = 1
                  AND cp.image_url IS NOT NULL AND cp.image_url != ''
                  AND cp.product_url IS NOT NULL AND cp.product_url != ''
                  AND cp.price > 0
                  AND inv.is_available = 1 AND inv.quantity > 0
                ORDER BY cp.updated_at DESC
                LIMIT 80
            """))
            for pid, name, price, list_p, cat, ptype, img, url, color, coll, occ, print_n, gender in r3.fetchall():
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

                # Preço DE (list_price) formatado
                try:
                    lp_cents = round(float(list_p) * 100) if list_p and float(list_p) > float(price or 0) else 0
                    list_price_fmt = (f"R$ {lp_cents//100:,}".replace(",",".") + f",{lp_cents%100:02d}") if lp_cents else ""
                except Exception:
                    list_price_fmt = ""

                catalog_products.append({
                    "product_id": str(pid),
                    "name": name,
                    "price": price_fmt,
                    "list_price": list_price_fmt,
                    "category": cat or "",
                    "product_type": (ptype or "").strip().upper(),
                    "image_url": img_clean,
                    "url": url_clean,
                    "color": color or "",
                    "collection": coll or "",
                    "occasion_vtex": (occ or "").strip().upper(),
                    "print_name": (print_n or "").strip(),
                    "gender": (gender or "").strip().upper(),
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

    # Classifica produtos usando o campo occasion do VTEX (fonte oficial)
    def _classify(name, cat, occasion_vtex="", product_type=""):
        """
        Classificação usando 3 camadas em ordem de prioridade:
        1. product_type (Tipo de Produto VTEX) — mais específico
        2. occasion (Ocasião VTEX) — fonte oficial
        3. category (categoria de navegação) + nome — fallback
        """
        occ  = (occasion_vtex or "").upper().strip()
        ptype = (product_type or "").upper().strip()
        n    = (name + " " + (cat or "")).lower()

        # ── CAMADA 1: product_type (mais preciso) ──────────────────────
        _PT_MAP = {
            "BIQUINI SUTIA":      "PRAIA_TOP",
            "SUTIA":              "PRAIA_TOP",
            "BIQUINI CALCINHA":   "PRAIA_BOTTOM",
            "CALCINHA":           "PRAIA_BOTTOM",
            "MAIO":               "MAIO",
            "SUNGA":              "SUNGA",
            "VESTIDO":            "VESTIDO",
            "MACACÃO":            "VESTIDO",
            "MACACAO":            "VESTIDO",
            "CHEMISE":            "VESTIDO",
            "CALCA":              "BOTTOM",
            "SAIA":               "BOTTOM",
            "SHORT":              "BOTTOM",
            "BERMUDA":            "BOTTOM",
            "BOARDSHORT":         "BOTTOM",
            "BLUSA/TOP":          "TOP",
            "BLUSA":              "TOP",
            "TOP":                "TOP",
            "CAMISETA":           "TOP",
            "CAMISA":             "TOP",
            "BODY":               "TOP",
            "CROPPED":            "TOP",
            "SAIDA DE PRAIA":     "SAIDA",
            "SAIDA DE BANHO":     "SAIDA",
            "CAPA/CAPA KIMONO":   "SAIDA",
            "CAPA":               "SAIDA",
            "CANGA":              "SAIDA",
            "TUNICA":             "SAIDA",
            "PAREO":              "SAIDA",
            "SANDALIA":           "CALCADO",
            "SANDÁLIAS":          "CALCADO",
            "CALCADO":            "CALCADO",
            "CALÇADOS":           "CALCADO",
            "CHINELO":            "CALCADO",
            "RASTEIRA":           "CALCADO",
            "BOLSA":              "BOLSA",
            "NECESSAIRE":         "BOLSA",
            "BRINCO":             "ACESSORIO",
            "COLAR":              "ACESSORIO",
            "PULSEIRA":           "ACESSORIO",
            "ANEL":               "ACESSORIO",
            "CHAPEU/BONE/VISEIRA":"ACESSORIO",
            "CHAPÉU":             "ACESSORIO",
            "OCULOS":             "ACESSORIO",
            "ÓCULOS":             "ACESSORIO",
            "CINTO":              "ACESSORIO",
            "LENCO":              "ACESSORIO",
            "JAQUETA/BLAZER/PARKA": "FRIO",
            "JAQUETA":            "FRIO",
            "BLAZER":             "FRIO",
            "MOLETOM":            "FRIO",
        }
        if ptype in _PT_MAP:
            return _PT_MAP[ptype]

        # ── CAMADA 2: occasion VTEX ────────────────────────────────────
        _OCC_MAP = {
            "BIQUINI SUTIA":      "PRAIA_TOP",
            "BIQUINI CALCINHA":   "PRAIA_BOTTOM",
            "MAIO":               "MAIO",
            "SUNGA":              "SUNGA",
            "SAIDA DE PRAIA":     "SAIDA",
            "SAIDA DE BANHO":     "SAIDA",
            "CAPA/CAPA KIMONO":   "SAIDA",
            "CANGA":              "SAIDA",
            "TUNICA":             "SAIDA",
            "VESTIDO":            "VESTIDO",
            "CALCA":              "BOTTOM",
            "SHORT":              "BOTTOM",
            "BERMUDA":            "BOTTOM",
            "SAIA":               "BOTTOM",
            "BOARDSHORT":         "BOTTOM",
            "BLUSA/TOP":          "TOP",
            "CAMISETA":           "TOP",
            "CAMISA":             "TOP",
            "BODY":               "TOP",
            "ACESSORIOS":         "ACESSORIO",
            "JAQUETA/BLAZER/PARKA": "FRIO",
        }
        if occ in _OCC_MAP:
            return _OCC_MAP[occ]

        # PRAIA genérico — usa category e nome para desambiguar
        if occ == "PRAIA":
            cat_u = (cat or "").upper()
            if "SUTIA" in cat_u or "BIQUÍNI" in cat_u or "BIKINI" in cat_u:
                return "PRAIA_TOP" if "SUTIA" in cat_u else "PRAIA_BOTTOM"
            if "CALCINHA" in cat_u:  return "PRAIA_BOTTOM"
            if "MAIÔ" in cat_u or "MAIO" in cat_u: return "MAIO"
            if "SUNGA" in cat_u:     return "SUNGA"
            if "SAÍDA" in cat_u or "SAIDA" in cat_u or "CANGA" in cat_u: return "SAIDA"
            # Fallback pelo nome
            if any(t in n for t in ["sutiã","sutia","bandeau","cortininha","frente única"]):
                return "PRAIA_TOP"
            if any(t in n for t in ["calcinha"]):
                return "PRAIA_BOTTOM"
            return "PRAIA_TOP"

        # ── CAMADA 3: category de navegação ───────────────────────────
        cat_u = (cat or "").upper()
        _CAT_MAP = {
            "BIQUÍNIS":                   "PRAIA_TOP",
            "SUTIA":                      "PRAIA_TOP",
            "CALCINHA":                   "PRAIA_BOTTOM",
            "MAIÔS & BODIES":             "MAIO",
            "SUNGAS":                     "SUNGA",
            "SUNGAS INFANTIS":            "SUNGA",
            "SAÍDAS DE PRAIA E CANGAS":   "SAIDA",
            "VESTIDOS":                   "VESTIDO",
            "MACACÕES FEMININOS":         "VESTIDO",
            "SAIAS":                      "BOTTOM",
            "CALÇAS FEMININAS":           "BOTTOM",
            "SHORTS FEMININOS":           "BOTTOM",
            "SHORTS & BERMUDAS MASCULINAS": "BOTTOM",
            "SHORTS & BERMUDAS INFANTIS": "BOTTOM",
            "BLUSAS FEMININAS":           "TOP",
            "BLUSAS INFANTIS":            "TOP",
            "TOP":                        "TOP",
            "CAMISAS MASCULINAS":         "TOP",
            "CAMISETAS MASCULINAS":       "TOP",
            "CALÇADOS":                   "CALCADO",
            "CALÇADOS/ ACESSÓRIOS":       "CALCADO",
            "BOLSAS & NECESSAIRES":       "BOLSA",
            "BRINCOS, PULSEIRAS & COLARES": "ACESSORIO",
            "CHAPÉUS, VISEIRAS E BONÉS":  "ACESSORIO",
            "ÓCULOS DE SOL":              "ACESSORIO",
            "CINTOS":                     "ACESSORIO",
            "LENÇOS":                     "ACESSORIO",
        }
        for key, tipo in _CAT_MAP.items():
            if key in cat_u:
                return tipo

        # Fallback por nome
        if any(t in n for t in ["sandália","sandalia","rasteira","scarpin","chinelo"]):
            return "CALCADO"
        if any(t in n for t in ["bolsa","clutch","tote"]):
            return "BOLSA"
        if any(t in n for t in ["suéter","sueter","tricô","trico","moletom","casaco"]):
            return "FRIO"
        if occ == "ROUPA":
            return "TOP"
        return "OUTRO"

    # Detecta contexto da mensagem para filtrar produtos incoerentes
    msg_lower = message.lower()
    is_beach = any(t in msg_lower for t in ["praia","biquini","biquíni","maio","maiô","resort","piscina","mar","surf","sunga"])
    is_cold = any(t in msg_lower for t in ["frio","inverno","tricô","trico","suéter","casaco","blusa fria"])
    is_party = any(t in msg_lower for t in ["festa","balada","jantar","evento","chique","sofisticad","formatura","casamento","aniversario","aniversário","barco","iate","reveillon"])
    is_casual = any(t in msg_lower for t in ["casual","dia a dia","passeio","shopping","trabalho","escritorio"])

    # Filtra produtos incoerentes com o contexto
    filtered_catalog = []
    for p in catalog_products:
        tipo = _classify(p["name"], p["category"], p.get("occasion_vtex",""), p.get("product_type",""))
        # Detecta se pediu especificamente maiô
        is_maio = any(t in msg_lower for t in ["maiô","maio","body"])

        # FESTA: remove biquíni/sutiã/calcinha praia e itens de frio
        if is_party and not is_beach:
            if tipo in ("PRAIA_TOP", "PRAIA_BOTTOM", "MAIO", "SUNGA"):
                continue
            if tipo == "FRIO":
                continue
        # PRAIA com pedido de maiô: prioriza MAIO, mantém saídas
        if is_maio:
            if tipo in ("PRAIA_TOP", "PRAIA_BOTTOM") and not is_beach:
                continue  # remove biquíni se pediu especificamente maiô
        # PRAIA: remove itens de frio
        if is_beach and not is_party:
            if tipo == "FRIO":
                continue
        # FRIO: remove biquínis e maiôs
        if is_cold:
            if tipo in ("PRAIA_TOP","PRAIA_BOTTOM","MAIO"):
                continue
        p["_tipo"] = tipo
        filtered_catalog.append(p)

    # Monta catálogo balanceado: tops + bottoms + complementos
    balanced = []
    priority_order = ["MAIO","SUNGA","PRAIA_TOP","PRAIA_BOTTOM","SAIDA","VESTIDO","TOP","TOP_MASC","BOTTOM","CALCADO","BOLSA","ACESSORIO","OUTRO"]
    # Detecta cor pedida na mensagem para boosting
    _color_keywords = {
        "branco": "branco", "white": "branco",
        "preto": "preto", "black": "preto",
        "azul": "azul", "blue": "azul",
        "azul bebê": "azul bebê", "baby blue": "azul bebê",
        "verde": "verde", "green": "verde",
        "rosa": "rosa", "pink": "rosa",
        "marrom": "marrom", "brown": "marrom",
        "bege": "bege", "beige": "bege",
        "off white": "off white",
        "caramelo": "caramelo",
        "vinho": "vinho",
        "vermelho": "vermelho", "red": "vermelho",
        "roxo": "roxo", "lilas": "lavanda",
        "dourado": "dourado", "gold": "dourado",
        "prata": "prata", "silver": "prata",
    }
    requested_color = ""
    for kw, cor in _color_keywords.items():
        if kw in msg_lower:
            requested_color = cor
            break

    # Se pediu cor específica, boost produtos que combinam
    if requested_color:
        def _color_boost(p):
            p_color = (p.get("color") or "").lower()
            if not p_color: return 0
            if requested_color in p_color: return 3      # cor exata
            if _color_matches(requested_color, p_color): return 1  # combina
            return -1  # não combina (penaliza mas não remove)

        filtered_catalog.sort(key=_color_boost, reverse=True)
        # Remove produtos que não combinam (score -1) se há suficientes que combinam
        good = [p for p in filtered_catalog if _color_boost(p) >= 0]
        if len(good) >= 10:
            filtered_catalog = good

    # Reconstrói by_type após boost
    by_type = defaultdict(list)
    for p in filtered_catalog:
        by_type[p["_tipo"]].append(p)

    # SAIDA e complementos recebem mais slots para dar variedade
    per_type_default = max(2, 20 // max(len([t for t in priority_order if by_type[t]]), 1))
    per_type_map = {
        "SAIDA": 8,      # muitas opções de saída
        "VESTIDO": 6,    # vestidos também
        "MAIO": 5,
        "PRAIA_TOP": 4,
        "PRAIA_BOTTOM": 4,
        "SUNGA": 4,
        "CALCADO": 3,
        "BOLSA": 3,
        "ACESSORIO": 2,
    }
    for tipo in priority_order:
        limit_t = per_type_map.get(tipo, per_type_default)
        balanced.extend(by_type[tipo][:limit_t])
    # Preenche até 25
    seen_ids = {p["product_id"] for p in balanced}
    for p in filtered_catalog:
        if len(balanced) >= 25: break
        if p["product_id"] not in seen_ids:
            balanced.append(p)
            seen_ids.add(p["product_id"])

    catalog_lines = "\n".join(
        (
            f"TIPO:{p['_tipo']}|ID:{p['product_id']}|NOME:{p['name']}"
            f"|COR:{p.get('color','') or ''}|ESTAMPA:{p.get('print_name','') or ''}"
            f"|COLECAO:{p.get('collection','') or ''}|GENERO:{p.get('gender','') or ''}"
            f"|PRECO:{p['price']}"
            + (f"|DE:{p['list_price']}" if p.get('list_price') else "")
            + f"|IMG:{p['image_url']}|URL:{p['url']}"
        )
        for p in balanced[:35]
        if p.get("image_url")
    )

    system_prompt = f"""Você é personal shopper da Água de Coco. Responda em português, tom sofisticado e caloroso.

CLIENTE: {client_name}
{memory_text}
{profile_text}
{page_ctx}

CATÁLOGO EM ESTOQUE:
{catalog_lines}

MISSÃO: Monte um look COERENTE COM A OCASIÃO pedida (mín. 3, máx. {limit} peças).

CLASSIFICAÇÃO DA OCASIÃO → ESTRUTURA DO LOOK:

FESTA / JANTAR / EVENTO / BARCO / IATE / FORMATURA:
  Opção A (peça única): VESTIDO ou MACACÃO + CALCADO elegante + BOLSA + ACESSÓRIO
  Opção B (combinado): BLUSA ou TOP sofisticado + CALÇA ou SAIA MIDI + CALCADO + BOLSA
  → Sempre inclua 1 opção com SAIA quando disponível no catálogo
  → ZERO biquíni, ZERO sutiã praia, ZERO calcinha praia

PRAIA / RESORT / PISCINA / MAR:
  Opção A (peça inteira): MAIO + SAIDA (mesma coleção OU lisa neutra) + SANDÁLIA + ACESSÓRIO
  Opção B (conjunto): PRAIA_TOP + PRAIA_BOTTOM (MESMA COLEÇÃO) + SAIDA + SANDÁLIA
  → SAÍDA DE PRAIA: inclua MÚLTIPLAS opções (kimono, canga, túnica, vestido, saia) — mín. 2 saídas
  → Se cliente pediu saída para biquíni camuflado: priorize saídas camufladas, depois lisas neutras
  → Pareamento: mesma coleção primeiro, depois cor neutra compatível
  → NUNCA sugira apenas 1 produto quando há mais opções disponíveis no catálogo

CASUAL / PASSEIO:
  TOP ou BLUSA + CALÇA ou SAIA ou SHORT + SANDÁLIA + ACESSÓRIO

REGRAS ABSOLUTAS DE PAREAMENTO:
1. Maiô + saída: MESMA coleção/estampa OU saída lisa neutra. NUNCA estampas diferentes.
2. Sutiã + calcinha: MESMO nome no campo NOME (ex: "Báltico" com "Báltico"). OBRIGATÓRIO.
3. NUNCA misture estampas diferentes em peças pareadas (ex: Copa + Báltico = ERRADO).
4. Verifique COLECAO: e NOME: — devem ser iguais entre peças pareadas.
5. Peça lisa + peça estampada: OK se forem mesma cor principal.

VARIEDADE: Quando possível, inclua 1 peça única (vestido/maiô/macacão) + 1 combinação (top+saia ou blusa+calça).

COR: Se pediu cor específica, priorize COR: correspondente. Se não encontrar, ofereça cor próxima e explique.

MATCH DE CORES 2026 — use ao montar looks:
· Verde oliva → bege, off white, marrom, azul petróleo, vinho
· Verde bandeira → rosa, branco, cinza, azul marinho, caramelo
· Verde sálvia → lavanda, creme, cinza, azul bebê, prata
· Azul marinho → branco, bege, vermelho, mostarda, verde oliva
· Azul bebê → marrom/chocolate, cinza, rosa blush, branco, prata (TENDÊNCIA FORTE 2026)
· Azul petróleo → ferrugem, nude, preto, verde, dourado
· Rosa blush → marrom, cinza, branco, verde oliva, azul
· Marrom/Chocolate → azul bebê, rosa, verde sálvia, creme (FORTÍSSIMO 2026)
· Caramelo → branco, azul marinho, verde, preto, dourado
· Vermelho/Vinho → rosa, azul, cinza, preto, bege / verde oliva, creme, azul petróleo
· Lavanda → cinza, verde menta, branco, azul bebê, prata
· Neutros 2026 (combinam com TUDO): Off White, Bege, Areia, Mocha, Creme, Preto

TENDÊNCIAS 2026: Marrom + Azul Bebê | Vermelho + Rosa | Verde Sálvia + Areia | Bege + Branco + Marrom
REGRA UNIVERSAL: cor forte + neutro elegante = look sempre certo.

ESTAMPA: Peça ESTAMPADA → complemento DEVE ser LISO. NUNCA duas estampas diferentes.
Se ESTAMPA: vazio = peça lisa → pode combinar com liso ou estampado na mesma cartela de cor.

PAREAMENTO: Sutiã + calcinha DEVEM ter mesma COLECAO: ou mesmo ESTAMPA:. Verificar obrigatório.

GÊNERO: GENERO:MASCULINO → só peças masculinas ou unissex. Não misturar.

PREÇO: Se campo DE: existir no produto, usar como "list_price" no JSON (preço original com desconto).

MENSAGEM: 2 frases. Mencione histórico, guarda-roupa e tendência de cor quando relevante.

RETORNE APENAS este JSON (sem texto antes/depois, sem markdown):
{{"message":"frase calorosa máx 2 linhas","products":[{{"id":"ID exato","name":"NOME exato","price":"PRECO exato","list_price":"DE: se existir, senão vazio","image_url":"IMG exata","url":"URL exata"}}]}}"""

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
            "list_price": p.get("list_price") or real.get("list_price") or "",
            "category": p.get("category") or real.get("category") or "",
            "image_url": real.get("image_url") or (p.get("image_url") or "").split("?")[0],
            "url": real.get("url") or p.get("url") or "",
            "is_complement": bool(p.get("is_complement")),
        })
    result["products"] = clean_products

    # Track + salva memória do cliente
    try:
        from services.closet_db import AsyncSessionLocal
        from sqlalchemy import text as _txt3
        async with AsyncSessionLocal() as db:
            await db.execute(_txt3(
                "INSERT INTO recommendation_clicks (email, product_id, occasion, source, clicked_at) "
                "VALUES (:e, 'stylist_chat', :occ, 'widget_stylist_chat', NOW())"
            ), {"e": email, "occ": message[:100]})

            # Atualiza resumo de memória do cliente
            novo_resumo = profile_text if profile_text else ""
            if message:
                novo_resumo += f"\nÚltimo pedido: {message[:80]}"
            if result.get("message"):
                pass  # não salva a resposta, só o perfil

            await db.execute(_txt3("""
                INSERT INTO client_memory
                  (email, cores_favoritas, tamanhos, ocasioes_frequentes,
                   pedidos_frequentes, categorias_favoritas, resumo_ia,
                   total_conversas, ultima_conversa)
                VALUES
                  (:email, :cores, :tamanhos, :ocasioes,
                   :pedidos, :categorias, :resumo, 1, NOW())
                ON CONFLICT (email) DO UPDATE SET
                  cores_favoritas = COALESCE(NULLIF(:cores,''), client_memory.cores_favoritas),
                  tamanhos = COALESCE(NULLIF(:tamanhos,''), client_memory.tamanhos),
                  ocasioes_frequentes = COALESCE(NULLIF(:ocasioes,''), client_memory.ocasioes_frequentes),
                  pedidos_frequentes = CASE
                    WHEN client_memory.pedidos_frequentes IS NULL THEN :pedidos
                    WHEN :pedidos != '' THEN client_memory.pedidos_frequentes || ', ' || :pedidos
                    ELSE client_memory.pedidos_frequentes
                  END,
                  categorias_favoritas = COALESCE(NULLIF(:categorias,''), client_memory.categorias_favoritas),
                  resumo_ia = :resumo,
                  total_conversas = client_memory.total_conversas + 1,
                  ultima_conversa = NOW()
            """), {
                "email": email,
                "cores": "",
                "tamanhos": "",
                "ocasioes": message[:80] if is_party else ("praia" if is_beach else ""),
                "pedidos": message[:80],
                "categorias": ", ".join(profile.get("categories", [])),
                "resumo": novo_resumo[:500],
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
