from sqlalchemy import func, or_, select

from models.catalog_product import CatalogProduct
from models.customer_recommendation import CustomerRecommendation
from models.inventory_by_sku import InventoryBySku
from services.closet_db import AsyncSessionLocal

SITE_BASE = "https://www.aguadecoco.com.br"


def normalize(value) -> str:
    return str(value or "").strip().lower()


def clean_url(url) -> str:
    if not url:
        return SITE_BASE

    url = str(url).strip()

    if url.startswith("http"):
        return url

    if url.startswith("/"):
        return f"{SITE_BASE}{url}"

    return f"{SITE_BASE}/{url}"


def is_blocked_home_product(product: CatalogProduct) -> bool:
    text = normalize(
        " ".join(
            [
                str(product.name or ""),
                str(product.category or ""),
                str(product.department or ""),
                str(product.product_type or ""),
            ]
        )
    )

    blocked_terms = [
        "bandeja", "copo", "taça", "taca", "vaso", "porta", "guardanapo",
        "mesa", "prato", "casa", "decor", "home", "almofada", "toalha",
        "jogo americano", "infantil", "criança", "crianca", "kids", "baby",
        "bebê", "bebe", "juvenil",
    ]

    return any(term in text for term in blocked_terms)


def is_fashion_product(product: CatalogProduct) -> bool:
    if is_blocked_home_product(product):
        return False

    text = normalize(
        " ".join(
            [
                str(product.name or ""),
                str(product.category or ""),
                str(product.department or ""),
                str(product.product_type or ""),
            ]
        )
    )

    fashion_terms = [
        "biquini",
        "biquíni",
        "sutiã",
        "sutia",
        "calcinha",
        "maiô",
        "maio",
        "vestido",
        "short",
        "saia",
        "camisa",
        "blusa",
        "camiseta",
        "top",
        "cropped",
        "calça",
        "calca",
        "pantalona",
        "pareô",
        "pareo",
        "saída",
        "saida",
        "body",
    ]

    # Bloqueia infantil/kids independente de ter termos de moda
    if any(t in text for t in ["infantil", "criança", "crianca", "kids", "baby", "bebê", "bebe"]):
        return False
    return any(term in text for term in fashion_terms)


def _is_blocked_payload(name, category, department) -> bool:
    text = normalize(" ".join([str(name or ""), str(category or ""), str(department or "")]))

    blocked_terms = [
        "bandeja", "copo", "taça", "taca", "vaso", "porta", "guardanapo",
        "mesa", "prato", "casa", "decor", "home",
        "infantil", "criança", "crianca", "kids", "baby", "bebê", "bebe",
    ]

    return any(term in text for term in blocked_terms)


# Mapeamento Linha → ocasião
LINHA_TO_OCCASION = {
    "agua": "praia",
    "vida": "casual",
    "luz": "jantar",
    "underwear": "casual",
    "lifestyle": "casual",
    "casa": None,  # não é moda
}

# Harmonias de cor (cores que combinam entre si)
COLOR_HARMONY = {
    "preto": ["branco", "bege", "off white", "dourado", "prata", "colorido"],
    "branco": ["preto", "bege", "off white", "azul", "verde", "colorido"],
    "bege": ["branco", "preto", "marrom", "off white", "dourado"],
    "azul": ["branco", "bege", "off white", "prata"],
    "verde": ["branco", "bege", "off white", "amarelo"],
    "amarelo": ["branco", "verde", "laranja", "colorido"],
    "rosa": ["branco", "bege", "lilás", "off white"],
    "laranja": ["branco", "amarelo", "colorido"],
    "vermelho": ["preto", "branco", "bege"],
    "marrom": ["bege", "off white", "branco"],
    "off white": ["preto", "bege", "branco", "marrom"],
    "colorido": ["branco", "preto", "bege"],
    "prata": ["azul", "preto", "branco"],
    "dourado": ["preto", "bege", "marrom"],
}


def colors_harmonize(color1: str, color2: str) -> bool:
    """Verifica se duas cores combinam."""
    if not color1 or not color2:
        return True  # sem info de cor, permite
    c1 = normalize(color1)
    c2 = normalize(color2)
    if c1 == c2:
        return True  # monocromático sempre combina
    harmonics = COLOR_HARMONY.get(c1, [])
    return c2 in harmonics or c1 in COLOR_HARMONY.get(c2, [])


def prints_harmonize(print1: str, print2: str) -> bool:
    """Estampado + Liso combina. Dois estampados geralmente não."""
    if not print1 or not print2:
        return True
    p1 = normalize(print1)
    p2 = normalize(print2)
    if p1 == p2 and p1 == "liso":
        return True  # liso + liso OK
    if p1 == p2 and p1 == "estampado":
        return False  # dois estampados normalmente não
    return True  # estampado + liso = OK


def extract_name_suffix(name: str) -> str:
    """
    Extrai a 'terminação' do nome do produto — geralmente o nome da coleção/estampa.
    Ex: "Biquíni Sutiã Faixa Bananeira"  → "bananeira"
        "Maiô Engana Mamãe Amalfi"       → "amalfi"
        "Sandália Coqueiros"             → "coqueiros"
        "Vestido Longo Floresta Ilustrada Localizada" → "floresta ilustrada localizada"

    Estratégia: remove os termos de tipo de produto e pega o que sobra.
    """
    TYPE_WORDS = [
        "biquíni", "biquini", "sutiã", "sutia", "calcinha", "maiô", "maio",
        "vestido", "macacão", "macacao", "blusa", "camisa", "camiseta", "top",
        "cropped", "body", "saia", "short", "calça", "calca", "pantalona",
        "saída", "saida", "canga", "pareô", "pareo", "kimono",
        "sandália", "sandalia", "rasteira", "chinelo", "mule", "scarpin",
        "bolsa", "clutch", "chapéu", "chapeu", "viseira", "colar", "brinco",
        "pulseira", "anel", "necessaire", "nécessaire", "mochila",
        "faixa", "alça", "cortininha", "engana", "mamãe", "mama", "longo",
        "curto", "midi", "mini", "franzida", "franzido", "lacinho", "com",
        "de", "e", "a", "o", "ao", "da", "do", "na", "no", "para", "sem",
        "uma", "um", "as", "os",
    ]
    words = normalize(name).split()
    suffix_words = [w for w in words if w not in TYPE_WORDS and len(w) > 2]
    return " ".join(suffix_words[-3:]) if suffix_words else ""  # últimas 3 palavras relevantes


def suffixes_match(name1: str, name2: str) -> bool:
    """Retorna True se os dois produtos têm a mesma terminação (mesma coleção/estampa)."""
    s1 = extract_name_suffix(name1)
    s2 = extract_name_suffix(name2)
    if not s1 or not s2:
        return False
    # Match exato ou um contém o outro (ex: "coqueiros" em "biquini coqueiros")
    return s1 == s2 or s1 in s2 or s2 in s1


def score_product(
    product: CatalogProduct,
    occasion: str = "",
    goal: str = "",
    style: str = "",
    closet_color: str = "",
    closet_print: str = "",
) -> float:
    # Similaridade baseada em tipo, ocasião, coleção e estampa — NUNCA em department/category
    # Isso garante que quem comprou na SALE recebe sugestões pelo produto, não pela categoria
    text = normalize(" ".join([
        str(product.name or ""),
        str(product.product_type or ""),
        str(product.occasion or ""),
        str(product.collection or ""),
        str(product.print_name or ""),
        str(product.color or ""),
    ]))

    score = 1.0
    occasion_n = normalize(occasion)

    # Score por Linha (campo 0- Linha)
    linha = normalize(product.collection or "")
    if linha and linha in LINHA_TO_OCCASION:
        linha_occasion = LINHA_TO_OCCASION[linha]
        if linha_occasion == occasion_n:
            score += 6  # match exato de linha + ocasião
        elif linha is None:
            score -= 10  # produtos de casa, bloqueia

    # Score por campo Ocasião direto
    product_occasion = normalize(product.occasion or "")
    if occasion_n and product_occasion:
        if occasion_n == "praia" and product_occasion in ["praia", "agua", "saída de praia", "saida de praia"]:
            score += 8
        elif occasion_n == "jantar" and product_occasion in ["luz", "jantar", "festa"]:
            score += 8
        elif occasion_n in product_occasion or product_occasion in occasion_n:
            score += 5

    # Score por tipo de produto para cross_sell
    if occasion_n == "praia" and any(
        x in text for x in ["biquini", "biquíni", "maiô", "maio", "saida", "saída", "canga", "sunga"]
    ):
        score += 5

    if occasion_n == "resort" and any(x in text for x in ["vestido", "camisa", "pantalona", "saia"]):
        score += 4

    if occasion_n == "jantar" and any(x in text for x in ["vestido", "camisa", "alfaiataria"]):
        score += 4

    if goal == "cross_sell" and any(
        x in text for x in ["saida", "saída", "camisa", "short", "saia", "calça", "calca", "top", "blusa"]
    ):
        score += 4

    if goal == "up_sell" and any(
        x in text for x in ["vestido", "resort", "bordado", "alfaiataria", "camisa", "linho"]
    ):
        score += 5

    if style:
        if style in text:
            score += 3
        if style == "elegante" and any(x in text for x in ["vestido", "camisa", "alfaiataria"]):
            score += 3
        if style == "leve" and any(x in text for x in ["linho", "praia", "resort", "saida", "saída"]):
            score += 3
        if style == "casual" and any(x in text for x in ["short", "camiseta", "blusa", "top"]):
            score += 3

    # Harmonia de cor com o closet
    if closet_color and product.color:
        if colors_harmonize(closet_color, product.color):
            score += 3
        else:
            score -= 2  # cor não combina, penaliza

    # Harmonia de estampa com o closet
    if closet_print and product.print_name:
        if prints_harmonize(closet_print, product.print_name):
            score += 2
        else:
            score -= 3  # dois estampados, penaliza

    return score


def build_reason(
    product: CatalogProduct,
    occasion: str = "",
    goal: str = "",
    style: str = "",
    closet_pieces: list[str] | None = None,
) -> str:
    """Gera motivo personalizado mencionando peças do closet que combinam."""
    product_name = str(product.name or "")
    product_type = str(product.product_type or product.category or "").lower()
    parts = []

    # Detecta o tipo de produto para encontrar complemento no closet
    TYPE_COMPLEMENTS = {
        "sutiã": ["calcinha", "biquíni calcinha", "saída"],
        "sutia": ["calcinha", "saida"],
        "calcinha": ["sutiã", "biquíni sutiã", "saída"],
        "maiô": ["saída de praia", "canga", "sandália"],
        "maio": ["saida", "canga"],
        "saída": ["maiô", "biquíni", "maio"],
        "saida": ["maio", "biquini"],
        "vestido": ["sandália", "bolsa", "acessório"],
        "blusa": ["calça", "short", "saia"],
        "calca": ["blusa", "camisa", "top"],
        "short": ["blusa", "top", "camisa"],
    }

    # Tenta mencionar peça do closet que combina
    closet_match = None
    if closet_pieces:
        name_lower = product_name.lower()

        # Prioridade 1: match por terminação (mesma coleção/estampa)
        for piece in closet_pieces:
            if suffixes_match(product_name, piece):
                closet_match = " ".join(piece.split()[:4])
                break

        # Prioridade 2: match por tipo complementar
        if not closet_match:
            for piece in closet_pieces:
                piece_lower = piece.lower()
                for ptype, complements in TYPE_COMPLEMENTS.items():
                    if ptype in name_lower and any(c in piece_lower for c in complements):
                        closet_match = " ".join(piece.split()[:4])
                        break
                    if ptype in piece_lower and any(c in name_lower for c in complements):
                        closet_match = " ".join(piece.split()[:4])
                        break
                if closet_match:
                    break

    if goal == "cross_sell":
        if closet_match:
            parts.append(f"Combina com seu {closet_match} do closet.")
        else:
            parts.append("Complementa peças que você já tem no closet.")
    elif goal == "up_sell":
        parts.append("Proposta mais sofisticada para elevar o seu look.")
    elif goal == "novidades":
        parts.append("Novidade da coleção alinhada ao seu estilo.")
    else:
        if closet_match:
            parts.append(f"Combina com seu {closet_match}.")
        else:
            parts.append("Selecionado com base no seu histórico de compras.")

    if occasion:
        occ_label = occasion.replace("_", " ")
        parts.append(f"Ideal para {occ_label}.")

    if style and style != "casual":
        parts.append(f"Estilo {style}.")

    return " ".join(parts)


async def get_customer_recommendations(
    email: str,
    occasion: str = "",
    goal: str = "",
    style: str = "",
    limit: int = 12,
) -> list[dict]:
    """
    Recomendações de look completo baseadas nas seleções do Personal Stylist.

    Classificação por nome do produto (product_type é NULL no banco):
      PRAIA/RESORT : biquíni/sutiã/maiô + calcinha + saída/canga + sandália/rasteira + chapéu/bolsa
      JANTAR/FESTA : vestido/macacão OU blusa+saia/calça + sandália/scarpin + bolsa/clutch + acessório
      VIAGEM       : blusa/camisa + calça/short + sandália/tênis + bolsa/mochila
      CASUAL       : blusa/camiseta/top + calça/short/saia + sandália/chinelo + acessório
      SEM SELEÇÃO  : curadoria por terminação de nome (mesma coleção) + monocromático

    SALE é excluído das recomendações (department = 'Sale') —
    recomendamos pela coleção/tipo, não pela categoria de liquidação.
    """
    email  = normalize(email)
    limit  = max(1, min(int(limit or 12), 24))

    # ── Classificador de tipo por nome ────────────────────────────────────────
    def classify(name: str) -> str:
        n = normalize(name or "")
        if any(t in n for t in ["biquini","biquíni","sutia","sutiã","maio","maiô","cropped praia"]):
            return "top_praia"
        if "calcinha" in n:
            return "calcinha"
        if any(t in n for t in ["saida","saída","canga","pareo","pareô","kimono"]):
            return "saida"
        if any(t in n for t in ["vestido","macacao","macacão"]):
            return "vestido"
        if any(t in n for t in ["blusa","camisa","camiseta","top","cropped","body"]):
            return "blusa"
        if any(t in n for t in ["calca","calça","saia","short","bermuda","pantalona"]):
            return "bottom"
        if any(t in n for t in ["sandalia","sandália","rasteira","chinelo","mule","scarpin","tamanco","tenis","tênis"]):
            return "calcado"
        if any(t in n for t in ["bolsa","clutch","mochila","necessaire","nécessaire"]):
            return "bolsa"
        if any(t in n for t in ["chapeu","chapéu","viseira"]):
            return "chapeu"
        if any(t in n for t in ["colar","brinco","pulseira","anel","relogio","relógio"]):
            return "joia"
        return "outro"

    # ── Slots por ocasião ─────────────────────────────────────────────────────
    # Ordem = prioridade de exibição no look
    SLOTS = {
        "praia":   ["top_praia","calcinha","saida","calcado","chapeu","bolsa","joia"],
        "resort":  ["vestido","blusa","bottom","saida","calcado","bolsa","chapeu","joia"],
        "jantar":  ["vestido","blusa","bottom","calcado","bolsa","joia"],
        "viagem":  ["blusa","bottom","saida","calcado","bolsa","chapeu"],
        "dia_a_dia":["blusa","bottom","calcado","bolsa","joia"],
    }

    # ── Boost score pelas seleções ─────────────────────────────────────────────
    GOAL_TERMS = {
        "cross_sell": ["saida","saída","canga","bolsa","sandalia","sandália","chapeu","chapéu","acessorio"],
        "up_sell":    ["vestido","camisa","linho","alfaiataria","pantalona","resort","bordado"],
        "novidades":  [],
    }
    STYLE_TERMS = {
        "elegante": ["vestido","camisa","alfaiataria","linho","macacão","pantalona","saia"],
        "casual":   ["camiseta","short","blusa","top","cropped","bermuda"],
        "leve":     ["linho","saida","saída","resort","canga","pareo","vestido"],
    }

    async with AsyncSessionLocal() as session:
        profile = await _get_customer_profile(email, session)
        dominant_gender = profile.get("dominant_gender", "feminino")

    # ── Nomes e sufixos do closet para personalização ─────────────────────────
    closet_items  = await _get_closet_items(email)
    closet_sku_ids = [i.sku_id for i in closet_items if i.sku_id]
    closet_names: list[str] = []
    try:
        from models.customer_closet_item import CustomerClosetItem
        async with AsyncSessionLocal() as s2:
            r2 = await s2.execute(
                select(CustomerClosetItem.name)
                .where(CustomerClosetItem.email == email)
                .limit(30)
            )
            closet_names = [row[0] for row in r2.fetchall() if row[0]]
    except Exception:
        pass

    # Sufixos dominantes do closet (terminações de coleção)
    closet_suffixes = [extract_name_suffix(n) for n in closet_names if extract_name_suffix(n)]

    # Cor dominante do closet via catalog_products
    dominant_closet_color = ""
    if closet_sku_ids:
        try:
            async with AsyncSessionLocal() as sc:
                rc = await sc.execute(
                    select(CatalogProduct.color)
                    .where(CatalogProduct.sku_id.in_(closet_sku_ids[:20]))
                )
                colors = [normalize(r.color or "") for r in rc.fetchall() if r.color]
                dominant_closet_color = max(set(colors), key=colors.count) if colors else ""
        except Exception:
            pass

    # ── Busca produtos em estoque, excluindo SALE e Infantil/Casa ────────────
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(CatalogProduct)
            .join(InventoryBySku, InventoryBySku.sku_id == CatalogProduct.sku_id)
            .where(
                CatalogProduct.is_active == 1,
                CatalogProduct.sku_id.is_not(None),
                InventoryBySku.quantity > 0,
                InventoryBySku.is_available == 1,
                # Exclui SALE — recomenda pela coleção/tipo, não por liquidação
                ~func.lower(func.coalesce(CatalogProduct.department, "")).like("sale%"),
                # Exclui Casa e Infantil
                ~func.lower(func.coalesce(CatalogProduct.department, "")).in_(
                    ["casa", "infantil", "kit"]
                ),
            )
            .limit(600)
        )
        products = result.scalars().all()

    # ── Filtro de gênero ──────────────────────────────────────────────────────
    def gender_ok(name, dept):
        n = normalize(f"{name or ''} {(dept or '').replace('Sale','').replace('sale','')}")
        if any(t in n for t in ["infantil","kids","criança","baby","bebê"]):
            return False
        if dominant_gender == "feminino" and "masculino" in n and "feminino" not in n:
            return False
        if dominant_gender == "masculino" and "feminino" in n and "masculino" not in n:
            return False
        return True

    products = [p for p in products if not is_blocked_home_product(p) and gender_ok(p.name, p.department)]

    # ── Scoring ───────────────────────────────────────────────────────────────
    occasion_n = normalize(occasion)
    goal_n     = normalize(goal)
    style_n    = normalize(style)
    slots      = SLOTS.get(occasion_n, [])

    def score(p: CatalogProduct) -> float:
        n   = normalize(p.name or "")
        s   = 0.0
        typ = classify(p.name)

        # 1. Match de terminação com closet (+15 — sinal mais forte)
        sfx = extract_name_suffix(p.name or "")
        if sfx and any(sfx in cs or cs in sfx for cs in closet_suffixes):
            s += 15

        # 2. Slot certo para a ocasião (+10)
        if slots and typ in slots:
            s += 10

        # 3. Score base de harmonias (cor, estampa, ocasião)
        s += score_product(
            p, occasion=occasion, goal=goal, style=style,
            closet_color=dominant_closet_color, closet_print="",
        )

        # 4. Goal boost (+8)
        if goal_n in GOAL_TERMS:
            terms = GOAL_TERMS[goal_n]
            if not terms or any(t in n for t in terms):
                s += 8

        # 5. Style boost (+6)
        if style_n in STYLE_TERMS:
            if any(t in n for t in STYLE_TERMS[style_n]):
                s += 6

        # 6. Cor monocromática (+4)
        if dominant_closet_color and p.color and normalize(p.color) == dominant_closet_color:
            s += 4

        return s

    scored = sorted([(score(p), p) for p in products], key=lambda x: x[0], reverse=True)

    # ── Monta look por slots quando há seleção de ocasião ─────────────────────
    if slots and occasion_n:
        used: set[str] = set()
        look: list[dict] = []

        for slot_type in slots:
            for sc, p in scored:
                pid = p.product_id or p.sku_id or ""
                if pid in used:
                    continue
                if classify(p.name) == slot_type:
                    used.add(pid)
                    fmt = _format_product(p, sc, occasion, goal, style, closet_names)
                    fmt["slot"] = slot_type
                    fmt["slot_label"] = _slot_label(slot_type)
                    look.append(fmt)
                    break

        # Completa com melhores scores até o limit
        for sc, p in scored:
            if len(look) >= limit:
                break
            pid = p.product_id or p.sku_id or ""
            if pid not in used:
                used.add(pid)
                look.append(_format_product(p, sc, occasion, goal, style, closet_names))

        return look

    # ── Sem seleção: lista por terminação + harmonia ──────────────────────────
    return [
        _format_product(p, sc, occasion, goal, style, closet_names)
        for sc, p in scored[:limit]
    ]


def _slot_label(slot: str) -> str:
    return {
        "top_praia": "Top / Biquíni / Maiô",
        "calcinha":  "Calcinha",
        "saida":     "Saída de Praia",
        "vestido":   "Vestido / Macacão",
        "blusa":     "Blusa / Camisa",
        "bottom":    "Calça / Saia / Short",
        "calcado":   "Calçado",
        "bolsa":     "Bolsa",
        "chapeu":    "Chapéu / Viseira",
        "joia":      "Acessório",
    }.get(slot, slot)


async def _get_closet_items(email: str):
    """Retorna itens do closet para análise de cor/estampa."""
    try:
        from models.customer_closet_item import CustomerClosetItem
        async with AsyncSessionLocal() as s:
            result = await s.execute(
                select(CustomerClosetItem)
                .where(CustomerClosetItem.email == email)
                .limit(20)
            )
            return result.scalars().all()
    except Exception:
        return []


async def _get_customer_profile(email: str, session) -> dict:
    """
    Infere perfil do cliente a partir do histórico de compras.
    Retorna: gênero dominante, tipos de produto comprados, cores favoritas.
    """
    from models.order_item import OrderItem
    from models.order import Order

    result = await session.execute(
        select(OrderItem.name, OrderItem.category, OrderItem.department)
        .join(Order, Order.order_id == OrderItem.order_id)
        .where(OrderItem.email == email)
        .limit(50)
    )
    rows = result.fetchall()

    text_all = " ".join([
        f"{r.name or ''} {r.category or ''} {r.department or ''}"
        for r in rows
    ]).lower()

    # Detecta gênero dominante
    fem_score = text_all.count("feminino") + text_all.count("blusas femininas")
    masc_score = text_all.count("masculino")
    inf_score = text_all.count("infantil") + text_all.count("kids")

    if fem_score >= masc_score and fem_score >= inf_score:
        dominant_gender = "feminino"
    elif masc_score > fem_score:
        dominant_gender = "masculino"
    else:
        dominant_gender = None  # sem histórico suficiente

    # Tipos de produto mais comprados (para não repetir o mesmo tipo nas recs)
    product_types = []
    type_keywords = {
        "maio": ["maiô", "maio"], "biquini": ["biquíni", "biquini"],
        "vestido": ["vestido"], "blusa": ["blusa"], "camisa": ["camisa", "camiseta"],
        "short": ["short", "bermuda"], "saia": ["saia"], "calca": ["calça", "calca"],
        "saida": ["saída", "saida"], "top": ["top", "cropped"],
    }
    for ptype, keywords in type_keywords.items():
        if any(kw in text_all for kw in keywords):
            product_types.append(ptype)

    return {
        "dominant_gender": dominant_gender,
        "owned_types": product_types,
        "total_orders": len(rows),
    }


def _extract_price_from_raw(raw_json: dict | None) -> float | None:
    """Extrai o melhor preço disponível do raw_json VTEX."""
    if not raw_json:
        return None
    try:
        # sellers[0].commertialOffer.Price (formato SKU detail VTEX)
        sellers = raw_json.get("sellers") or []
        if sellers:
            offer = sellers[0].get("commertialOffer") or {}
            for key in ("Price", "bestPrice", "bestPriceWithTax"):
                val = offer.get(key)
                if val and float(val) > 0:
                    fval = float(val)
                    return fval / 100 if fval > 1000 else fval
        # Fallback: campos no nível raiz
        for key in ("bestPriceWithTax", "bestPrice", "Price", "price", "sellingPrice"):
            val = raw_json.get(key)
            if val and float(val) > 0:
                fval = float(val)
                return fval / 100 if fval > 1000 else fval
    except Exception:
        pass
    return None


def _format_saved(item: CustomerRecommendation) -> dict:
    url = clean_url(item.product_url)
    price = float(item.price) if getattr(item, "price", None) else None

    return {
        "sku_id": item.sku_id,
        "product_id": item.product_id,
        "ref_id": item.ref_id,
        "name": item.name,
        "nome": item.name,
        "category": item.category,
        "categoria": item.category,
        "department": item.department,
        "departamento": item.department,
        "price": price,
        "preco": price,
        "image_url": item.image_url or "",
        "imagem_url": item.image_url or "",
        "product_url": url,
        "link_produto": url,
        "url": url,
        "reason": item.reason or "Sugestão de moda disponível em estoque para combinar com seu closet.",
        "motivo": item.reason or "Sugestão de moda disponível em estoque para combinar com seu closet.",
        "recommendation_type": item.recommendation_type or "fashion_stock",
        "score": float(item.score or 0),
    }


def _format_product(
    product: CatalogProduct,
    score: float,
    occasion: str = "",
    goal: str = "",
    style: str = "",
    closet_pieces: list[str] | None = None,
) -> dict:
    url = clean_url(product.product_url)
    reason = build_reason(product, occasion=occasion, goal=goal, style=style, closet_pieces=closet_pieces)

    # Tenta price do campo dedicado, senão extrai do raw_json
    price = float(product.price) if getattr(product, "price", None) else _extract_price_from_raw(
        product.raw_json if hasattr(product, "raw_json") else None
    )

    return {
        "sku_id": product.sku_id,
        "product_id": product.product_id,
        "ref_id": product.ref_id,
        "name": product.name,
        "nome": product.name,
        "category": product.category,
        "categoria": product.category,
        "department": product.department,
        "departamento": product.department,
        "product_type": product.product_type,
        "tipo_produto": product.product_type,
        "occasion": product.occasion,
        "ocasiao": product.occasion,
        "estamparia": product.print_name,
        "color": product.color,
        "cor": product.color,
        "size": product.size,
        "tamanho": product.size,
        "collection": product.collection,
        "colecao": product.collection,
        "price": price,
        "preco": price,
        "image_url": product.image_url or "",
        "imagem_url": product.image_url or "",
        "product_url": url,
        "link_produto": url,
        "url": url,
        "reason": reason,
        "motivo": reason,
        "recommendation_type": goal or "fashion_stock",
        "score": float(score or 0),
    }