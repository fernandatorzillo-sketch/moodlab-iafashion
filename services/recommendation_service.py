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
    Retorna recomendações de look completo baseadas nas seleções do Personal Stylist.

    Slots de look por ocasião:
      praia/resort : top (biquíni/sutiã/maiô) + bottom (calcinha) + saída + calçado + acessório
      jantar/festa : vestido OU blusa+saia/calça + calçado + bolsa + acessório
      viagem       : camisa/blusa + calça/short + sandália + acessório
      casual       : blusa/camiseta + calça/short/saia + calçado + acessório
      (sem seleção): curadoria por harmonia de cor/estampa com o closet
    """
    email     = normalize(email)
    email_like = email if "%" in email else f"{email}%"
    limit     = max(1, min(int(limit or 12), 24))

    # ── Mapa de slots por ocasião ─────────────────────────────────────────────
    OCCASION_SLOTS = {
        "praia": [
            {"slot": "top_praia",   "terms": ["biquíni", "biquini", "sutiã", "sutia", "maiô", "maio", "cropped"], "weight": 10},
            {"slot": "bottom_praia","terms": ["calcinha"], "weight": 10},
            {"slot": "saida_praia", "terms": ["saída", "saida", "canga", "pareô", "pareo"], "weight": 9},
            {"slot": "calcado",     "terms": ["sandália", "sandalia", "rasteira", "chinelo"], "weight": 7},
            {"slot": "acessorio",   "terms": ["chapéu", "chapeu", "viseira", "bolsa", "nécessaire", "necessaire", "colar", "brinco"], "weight": 6},
        ],
        "resort": [
            {"slot": "vestido_resort",  "terms": ["vestido", "macacão", "macacao"], "weight": 10},
            {"slot": "blusa_resort",    "terms": ["blusa", "camisa", "top", "cropped"], "weight": 8},
            {"slot": "bottom_resort",   "terms": ["calça", "calca", "saia", "short", "pantalona"], "weight": 8},
            {"slot": "saida_resort",    "terms": ["saída", "saida", "kimono", "canga"], "weight": 7},
            {"slot": "calcado",         "terms": ["sandália", "sandalia", "mule", "rasteira"], "weight": 7},
            {"slot": "acessorio",       "terms": ["bolsa", "chapéu", "chapeu", "colar", "brinco", "pulseira"], "weight": 6},
        ],
        "jantar": [
            {"slot": "vestido_jantar",  "terms": ["vestido", "macacão", "macacao"], "weight": 10},
            {"slot": "blusa_jantar",    "terms": ["blusa", "camisa", "top", "body"], "weight": 8},
            {"slot": "bottom_jantar",   "terms": ["saia", "calça", "calca", "pantalona"], "weight": 8},
            {"slot": "calcado",         "terms": ["sandália", "sandalia", "scarpin", "mule", "tamanco"], "weight": 7},
            {"slot": "acessorio",       "terms": ["bolsa", "clutch", "colar", "brinco", "pulseira", "anel"], "weight": 6},
        ],
        "viagem": [
            {"slot": "blusa_viagem",    "terms": ["blusa", "camisa", "camiseta", "top"], "weight": 9},
            {"slot": "bottom_viagem",   "terms": ["calça", "calca", "short", "saia", "bermuda", "pantalona"], "weight": 9},
            {"slot": "saida_viagem",    "terms": ["saída", "saida", "kimono", "vestido"], "weight": 7},
            {"slot": "calcado",         "terms": ["sandália", "sandalia", "tênis", "tenis", "rasteira"], "weight": 7},
            {"slot": "acessorio",       "terms": ["bolsa", "mochila", "chapéu", "chapeu", "colar", "brinco"], "weight": 6},
        ],
        "dia_a_dia": [
            {"slot": "blusa_casual",    "terms": ["blusa", "camiseta", "top", "cropped", "camisa"], "weight": 9},
            {"slot": "bottom_casual",   "terms": ["calça", "calca", "short", "saia", "bermuda"], "weight": 9},
            {"slot": "calcado",         "terms": ["sandália", "sandalia", "tênis", "tenis", "rasteira", "chinelo"], "weight": 7},
            {"slot": "acessorio",       "terms": ["bolsa", "colar", "brinco", "pulseira", "anel"], "weight": 5},
        ],
    }

    # ── Score adicional por seleção do Personal Stylist ───────────────────────
    GOAL_BOOST = {
        "cross_sell": {
            "terms": ["saída", "saida", "canga", "bolsa", "sandália", "sandalia", "acessório", "chapéu"],
            "boost": 8,
            "reason": "Complementa peças que você já tem no closet.",
        },
        "up_sell": {
            "terms": ["vestido", "camisa", "alfaiataria", "linho", "bordado", "resort", "pantalona"],
            "boost": 8,
            "reason": "Proposta mais sofisticada para elevar o seu look.",
        },
        "novidades": {
            "terms": [],   # qualquer produto novo vale
            "boost": 3,
            "reason": "Novidade da coleção alinhada ao seu estilo.",
        },
    }

    STYLE_BOOST = {
        "elegante": {
            "terms": ["vestido", "camisa", "alfaiataria", "linho", "macacão", "pantalona"],
            "boost": 6,
        },
        "casual": {
            "terms": ["camiseta", "short", "blusa", "top", "cropped", "bermuda"],
            "boost": 6,
        },
        "leve": {
            "terms": ["linho", "saída", "saida", "resort", "canga", "pareô", "pareo", "vestido"],
            "boost": 6,
        },
    }

    async with AsyncSessionLocal() as session:
        profile = await _get_customer_profile(email, session)
        dominant_gender = profile.get("dominant_gender")

        # ── Busca produtos em estoque ─────────────────────────────────────────
        # Expande termos de busca incluindo acessórios e calçados
        ALL_TERMS = [
            "biquini", "biquíni", "sutia", "sutiã", "calcinha", "maiô", "maio",
            "vestido", "macacão", "macacao", "short", "saia", "camisa", "blusa",
            "camiseta", "top", "cropped", "calça", "calca", "pantalona", "pareô", "pareo",
            "saída", "saida", "body", "kimono",
            # acessórios e calçados
            "sandália", "sandalia", "rasteira", "chinelo", "mule", "scarpin", "tamanco",
            "bolsa", "clutch", "chapéu", "chapeu", "viseira", "nécessaire", "necessaire",
            "colar", "brinco", "pulseira", "anel", "mochila",
        ]

        product_query = (
            select(CatalogProduct)
            .join(InventoryBySku, InventoryBySku.sku_id == CatalogProduct.sku_id)
            .where(
                CatalogProduct.is_active == 1,
                CatalogProduct.sku_id.is_not(None),
                InventoryBySku.quantity > 0,
                InventoryBySku.is_available == 1,
                or_(*[
                    func.lower(func.coalesce(CatalogProduct.name, "")).like(f"%{t}%")
                    for t in ALL_TERMS
                ]),
            )
            .limit(limit * 8)
        )

        result = await session.execute(product_query)
        products = result.scalars().all()

    # ── Filtro de gênero ──────────────────────────────────────────────────────
    def is_gender_match(name, cat, dept):
        name_text  = normalize(str(name or ""))
        dept_clean = normalize(str(dept or "")).replace("sale", "").strip()
        full_text  = f"{name_text} {dept_clean}"
        if any(t in full_text for t in ["infantil", "kids", "criança", "crianca", "baby", "bebê", "bebe"]):
            return False
        if dominant_gender == "feminino" and "masculino" in full_text and "feminino" not in full_text:
            return False
        if dominant_gender == "masculino" and "feminino" in full_text and "masculino" not in full_text:
            return False
        return True

    products = [
        p for p in products
        if not is_blocked_home_product(p) and is_gender_match(p.name, p.category, p.department)
    ]

    # ── Cor e estampa dominante do closet ─────────────────────────────────────
    closet_items  = await _get_closet_items(email)
    closet_sku_ids = [i.sku_id for i in closet_items if i.sku_id]
    dominant_closet_color = ""
    dominant_closet_print = ""
    if closet_sku_ids:
        try:
            async with AsyncSessionLocal() as s_color:
                cp_result = await s_color.execute(
                    select(CatalogProduct.color, CatalogProduct.print_name)
                    .where(CatalogProduct.sku_id.in_(closet_sku_ids[:20]))
                )
                cp_rows = cp_result.fetchall()
                closet_colors = [normalize(r.color or "") for r in cp_rows if r.color]
                closet_prints = [normalize(r.print_name or "") for r in cp_rows if r.print_name]
                dominant_closet_color = max(set(closet_colors), key=closet_colors.count) if closet_colors else ""
                dominant_closet_print = max(set(closet_prints), key=closet_prints.count) if closet_prints else ""
        except Exception:
            pass

    # ── Nomes do closet para personalizar motivos ─────────────────────────────
    closet_names: list[str] = []
    try:
        from models.customer_closet_item import CustomerClosetItem
        async with AsyncSessionLocal() as s2:
            r2 = await s2.execute(
                select(CustomerClosetItem.name)
                .where(CustomerClosetItem.email == email)
                .limit(20)
            )
            closet_names = [row[0] for row in r2.fetchall() if row[0]]
    except Exception:
        pass

    # ── Scoring ───────────────────────────────────────────────────────────────
    def score_for_stylist(product: CatalogProduct) -> float:
        """Pontua o produto pelas seleções do Personal Stylist + harmonia de cor/estampa."""
        name_text = normalize(" ".join([
            str(product.name or ""),
            str(product.product_type or ""),
            str(product.occasion or ""),
            str(product.collection or ""),
            str(product.print_name or ""),
            str(product.color or ""),
        ]))
        score = score_product(
            product,
            occasion=occasion,
            goal=goal,
            style=style,
            closet_color=dominant_closet_color,
            closet_print=dominant_closet_print,
        )

        # ── Boost por terminação: monocromático ou mesma coleção ──────────────
        # Prioriza produtos que compartilham a terminação do nome com peças do closet
        # Ex: se o closet tem "Biquíni Sutiã Coqueiros", recomenda "Sandália Coqueiros"
        if closet_names:
            for closet_name in closet_names[:10]:
                if suffixes_match(product.name or "", closet_name):
                    score += 12  # match de coleção é o sinal mais forte de look completo
                    break

        # Boost monocromático: mesma cor que o closet dominante
        if dominant_closet_color and product.color:
            if normalize(product.color) == dominant_closet_color:
                score += 5  # monocromático = look coeso

        # Boost pelas seleções do Personal Stylist
        occasion_n = normalize(occasion)
        slots = OCCASION_SLOTS.get(occasion_n, [])
        for slot_def in slots:
            if any(t in name_text for t in slot_def["terms"]):
                score += slot_def["weight"]
                break  # cada produto pega o boost do primeiro slot que bate

        if goal and goal in GOAL_BOOST:
            gdef = GOAL_BOOST[goal]
            if not gdef["terms"] or any(t in name_text for t in gdef["terms"]):
                score += gdef["boost"]

        if style and style in STYLE_BOOST:
            sdef = STYLE_BOOST[style]
            if any(t in name_text for t in sdef["terms"]):
                score += sdef["boost"]

        return score

    scored = sorted(
        [(score_for_stylist(p), p) for p in products],
        key=lambda x: x[0],
        reverse=True,
    )

    # ── Monta look completo com slots ─────────────────────────────────────────
    occasion_n = normalize(occasion)
    slots_def  = OCCASION_SLOTS.get(occasion_n, [])

    if slots_def and (occasion or goal or style):
        # Monta look preenchendo cada slot com o melhor produto disponível
        used_product_ids: set[str] = set()
        look_items: list[dict] = []

        for slot_def in slots_def:
            # Encontra o melhor produto para este slot que ainda não foi usado
            for score, product in scored:
                pid = product.product_id or product.sku_id or ""
                if pid in used_product_ids:
                    continue
                name_text = normalize(product.name or "")
                if any(t in name_text for t in slot_def["terms"]):
                    used_product_ids.add(pid)
                    formatted = _format_product(
                        product=product,
                        score=score,
                        occasion=occasion,
                        goal=goal,
                        style=style,
                        closet_pieces=closet_names,
                    )
                    formatted["slot"] = slot_def["slot"]
                    formatted["slot_label"] = _slot_label(slot_def["slot"])
                    look_items.append(formatted)
                    break  # um produto por slot

        # Complementa com produtos de alto score até atingir o limit
        for score, product in scored:
            if len(look_items) >= limit:
                break
            pid = product.product_id or product.sku_id or ""
            if pid in used_product_ids:
                continue
            used_product_ids.add(pid)
            look_items.append(_format_product(
                product=product,
                score=score,
                occasion=occasion,
                goal=goal,
                style=style,
                closet_pieces=closet_names,
            ))

        return look_items

    # ── Sem seleção: lista plana por harmonia de cor/estampa ──────────────────
    return [
        _format_product(
            product=product,
            score=score,
            occasion=occasion,
            goal=goal,
            style=style,
            closet_pieces=closet_names,
        )
        for score, product in scored[:limit]
    ]


def _slot_label(slot: str) -> str:
    """Rótulo legível para o slot do look."""
    labels = {
        "top_praia":    "Top / Biquíni",
        "bottom_praia": "Calcinha",
        "saida_praia":  "Saída de Praia",
        "vestido_resort": "Vestido / Macacão",
        "blusa_resort": "Blusa / Camisa",
        "bottom_resort":"Calça / Saia",
        "saida_resort": "Saída / Kimono",
        "vestido_jantar":"Vestido / Macacão",
        "blusa_jantar":  "Blusa / Top",
        "bottom_jantar": "Saia / Calça",
        "blusa_viagem":  "Blusa / Camisa",
        "bottom_viagem": "Calça / Short",
        "saida_viagem":  "Saída / Vestido",
        "blusa_casual":  "Blusa / Camiseta",
        "bottom_casual": "Calça / Short / Saia",
        "calcado":       "Calçado",
        "acessorio":     "Acessório",
    }
    return labels.get(slot, slot.replace("_", " ").title())


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