from typing import Any


def normalize_text(value: Any) -> str:
    return str(value or "").strip().lower()


def as_list(value: Any) -> list:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def split_csv(value: Any) -> list[str]:
    if not value:
        return []

    if isinstance(value, list):
        result = []
        for v in value:
            norm = normalize_text(v)
            if norm:
                result.append(norm)
        return result

    result = []
    for v in str(value).split(","):
        norm = normalize_text(v)
        if norm:
            result.append(norm)
    return result


def get_item_value(item: dict, *keys, default=""):
    for key in keys:
        if key in item and item[key] not in [None, ""]:
            return item[key]
    return default


def get_item_colors(item: dict) -> list[str]:
    colors = get_item_value(
        item,
        "colors",
        "cor",
        "cores",
        default=[],
    )
    return split_csv(colors)


def get_item_size(item: dict) -> str:
    return normalize_text(
        get_item_value(
            item,
            "size",
            "tamanho",
            default="",
        )
    )


def get_item_type(item: dict) -> str:
    return normalize_text(
        get_item_value(
            item,
            "product_type",
            "tipo_produto",
            "tipo de produto",
            "tipo_produto_pa",
            "tipo",
            default="",
        )
    )


def get_item_department(item: dict) -> str:
    return normalize_text(
        get_item_value(
            item,
            "department",
            "departamento",
            "department_name",
            "grupo",
            default="",
        )
    )


def get_item_occasion(item: dict) -> str:
    return normalize_text(
        get_item_value(
            item,
            "occasion",
            "ocasiao",
            "ocasião",
            default="",
        )
    )


def get_item_estamparia(item: dict) -> str:
    return normalize_text(
        get_item_value(
            item,
            "estamparia",
            "print_name",
            "estampa",
            default="",
        )
    )


def get_item_stock(item: dict) -> int:
    stock = get_item_value(
        item,
        "stock_quantity",
        "estoque",
        "quantity",
        default=0,
    )
    try:
        return int(stock)
    except Exception:
        return 0


def is_in_stock(item: dict) -> bool:
    in_stock = item.get("in_stock")
    if isinstance(in_stock, bool):
        return in_stock and get_item_stock(item) > 0
    return get_item_stock(item) > 0


def get_item_identity(item: dict) -> str:
    return str(
        get_item_value(
            item,
            "sku_id",
            "sku",
            "product_id",
            "ref_id",
            "id",
            "name",
            default="",
        )
    ).strip()


def get_complementary_types(product_type: str, department: str) -> list[str]:
    """
    Complementaridade real sem fallback:
    só pontua se houver relação coerente entre os tipos.
    """
    product_type = normalize_text(product_type)
    department = normalize_text(department)

    # Praia
    if any(x in product_type for x in ["sutia", "sutiã", "top", "cortininha"]):
        return ["calcinha", "bottom", "saida", "saída"]

    if any(x in product_type for x in ["calcinha", "bottom"]):
        return ["sutia", "sutiã", "top", "cortininha", "saida", "saída"]

    if any(x in product_type for x in ["maiô", "maio"]):
        return ["saida", "saída", "acessorio", "acessório"]

    if any(x in product_type for x in ["saida", "saída"]):
        return ["sutia", "sutiã", "top", "calcinha", "maiô", "maio"]

    # Feminino / resort / roupa
    if "vestido" in product_type:
        return ["sandalia", "sandália", "bolsa", "acessorio", "acessório"]

    if "camisa" in product_type:
        return ["calca", "calça", "short", "saia"]

    if any(x in product_type for x in ["blusa", "top"]):
        return ["calca", "calça", "short", "saia"]

    if any(x in product_type for x in ["calca", "calça", "short", "saia"]):
        return ["camisa", "blusa", "top"]

    # Se não souber complementar, não inventa
    return []


def build_profile(
    closet_products: list[dict],
    answers: dict,
    style_preferences: dict | None = None,
) -> dict:
    style_preferences = style_preferences or {}

    closet_departments = []
    closet_types = []
    closet_colors = []
    closet_occasions = []
    closet_estampas = []
    complementary_targets = []

    for item in closet_products:
        dept = get_item_department(item)
        ptype = get_item_type(item)
        occ = get_item_occasion(item)
        est = get_item_estamparia(item)
        colors = get_item_colors(item)

        if dept:
            closet_departments.append(dept)
        if ptype:
            closet_types.append(ptype)
            complementary_targets.extend(get_complementary_types(ptype, dept))
        if occ:
            closet_occasions.append(occ)
        if est:
            closet_estampas.append(est)
        closet_colors.extend(colors)

    preferred_colors = split_csv(style_preferences.get("preferred_colors"))
    preferred_styles = split_csv(style_preferences.get("preferred_styles"))
    preferred_occasions = split_csv(style_preferences.get("preferred_occasions"))

    answer_occasion = normalize_text(answers.get("occasion"))
    answer_goal = normalize_text(answers.get("goal"))
    answer_style = normalize_text(answers.get("style"))

    return {
        "answer_occasion": answer_occasion,
        "answer_goal": answer_goal,
        "answer_style": answer_style,
        "closet_departments": list(set(closet_departments)),
        "closet_types": list(set(closet_types)),
        "closet_colors": list(set(closet_colors)),
        "closet_occasions": list(set(closet_occasions)),
        "closet_estampas": list(set(closet_estampas)),
        "complementary_targets": list(set(complementary_targets)),
        "preferred_colors": preferred_colors,
        "preferred_styles": preferred_styles,
        "preferred_occasions": preferred_occasions,
    }


def score_candidate(candidate: dict, profile: dict) -> tuple[int, list[str]]:
    score = 0
    reasons = []

    if not is_in_stock(candidate):
        return -999, ["sem estoque"]

    candidate_department = get_item_department(candidate)
    candidate_type = get_item_type(candidate)
    candidate_occasion = get_item_occasion(candidate)
    candidate_estamparia = get_item_estamparia(candidate)
    candidate_colors = get_item_colors(candidate)
    candidate_name = normalize_text(candidate.get("name", ""))

    closet_departments = profile["closet_departments"]
    closet_types = profile["closet_types"]
    closet_colors = profile["closet_colors"]
    closet_occasions = profile["closet_occasions"]
    closet_estampas = profile["closet_estampas"]
    complementary_targets = profile["complementary_targets"]

    answer_goal = profile["answer_goal"]
    answer_occasion = profile["answer_occasion"]
    answer_style = profile["answer_style"]

    preferred_colors = profile["preferred_colors"]
    preferred_occasions = profile["preferred_occasions"]

    # 1. Departamento
    if candidate_department and candidate_department in closet_departments:
        score += 4
        reasons.append("conversa com o departamento já presente no closet")

    # 2. Ocasião do closet
    if candidate_occasion and candidate_occasion in closet_occasions:
        score += 4
        reasons.append("mantém coerência com ocasiões já compradas")

    # 3. Ocasião escolhida na jornada atual
    if answer_occasion and candidate_occasion and candidate_occasion == answer_occasion:
        score += 7
        reasons.append("combina com a ocasião escolhida")

    # 4. Ocasiões preferidas históricas
    if candidate_occasion and candidate_occasion in preferred_occasions:
        score += 4
        reasons.append("alinha com ocasiões preferidas")

    # 5. Estamparia
    if candidate_estamparia and candidate_estamparia in closet_estampas:
        score += 3
        reasons.append("mantém linguagem de estamparia coerente")

    # 6. Cores
    if any(color in closet_colors for color in candidate_colors):
        score += 2
        reasons.append("combina com as cores do closet")

    if any(color in preferred_colors for color in candidate_colors):
        score += 3
        reasons.append("segue cores preferidas")

    # 7. Goal
    if answer_goal == "cross_sell":
        if candidate_type and candidate_type in complementary_targets:
            score += 8
            reasons.append("é uma peça complementar ao que já existe no closet")

    elif answer_goal == "up_sell":
        if candidate_department and candidate_department in closet_departments:
            score += 3
            reasons.append("mantém o universo de compra da cliente")

        # upsell real: não repetir exatamente o mesmo tipo
        if candidate_type and candidate_type not in closet_types:
            score += 5
            reasons.append("expande o closet com um tipo de peça novo")

    elif answer_goal == "novidades":
        if candidate_type and candidate_type not in closet_types:
            score += 4
            reasons.append("traz novidade dentro do universo da cliente")

    # 8. Estilo (peso leve, sem inventar)
    if answer_style:
        searchable_text = " ".join(
            [
                candidate_name,
                candidate_department,
                candidate_type,
                candidate_occasion,
                candidate_estamparia,
            ]
        )

        if answer_style in searchable_text:
            score += 2
            reasons.append("reforça a linguagem visual buscada")

    return score, reasons


def build_virtual_seller_message(profile: dict, top_reasons: list[str]) -> str:
    occasion = profile.get("answer_occasion") or "o momento que você escolheu"
    goal = profile.get("answer_goal") or "completar seu closet"

    intro = f"Separei peças pensando em {occasion} e no seu objetivo de {goal.replace('_', ' ')}."
    if top_reasons:
        detail = " Considerei principalmente " + ", ".join(top_reasons[:3]) + "."
    else:
        detail = " Considerei o histórico do seu closet e suas preferências."
    return intro + detail


def build_recommendations(
    closet_products: list[dict],
    catalog: list[dict],
    answers: dict,
    style_preferences: dict | None = None,
    limit: int = 8,
) -> dict:
    profile = build_profile(closet_products, answers, style_preferences)

    owned_ids = {
        get_item_identity(item)
        for item in closet_products
        if get_item_identity(item)
    }

    scored = []

    for candidate in catalog:
        candidate_id = get_item_identity(candidate)
        if not candidate_id or candidate_id in owned_ids:
            continue

        score, reasons = score_candidate(candidate, profile)

        # sem fallback
        if score <= 0:
            continue

        enriched = dict(candidate)
        enriched["reason"] = "; ".join(reasons[:2]) if reasons else "Selecionado pelo seu perfil"
        enriched["score"] = score
        scored.append(enriched)

    scored.sort(key=lambda x: x.get("score", 0), reverse=True)
    selected = scored[:limit]

    all_reasons = []
    for item in selected:
        if item.get("reason"):
            all_reasons.extend(item["reason"].split("; "))

    human_message = build_virtual_seller_message(profile, all_reasons)

    return {
        "profile": profile,
        "human_message": human_message,
        "recommendations": selected,
        "meta": {
            "catalog_analyzed": len(catalog),
            "closet_count": len(closet_products),
            "returned_count": len(selected),
        },
    }