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
        return [normalize_text(v) for v in value if v]
    return [normalize_text(v) for v in str(value).split(",") if str(v).strip()]


def get_item_value(item: dict, *keys, default=""):
    for key in keys:
        if key in item and item[key] not in [None, ""]:
            return item[key]
    return default


def get_item_colors(item: dict) -> list[str]:
    colors = get_item_value(item, "colors", "cor", default=[])
    return split_csv(colors)


def get_item_size(item: dict) -> str:
    return normalize_text(get_item_value(item, "size", "tamanho", default=""))


def get_item_type(item: dict) -> str:
    return normalize_text(
        get_item_value(item, "product_type", "tipo_produto", "tipo de produto", "category", "categoria", default="")
    )


def get_item_department(item: dict) -> str:
    return normalize_text(get_item_value(item, "department", "departamento", default=""))


def get_item_occasion(item: dict) -> str:
    return normalize_text(get_item_value(item, "occasion", "ocasiao", "ocasião", default=""))


def get_item_estamparia(item: dict) -> str:
    return normalize_text(get_item_value(item, "estamparia", default=""))


def get_item_stock(item: dict) -> int:
    stock = get_item_value(item, "stock_quantity", "estoque", default=0)
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
        get_item_value(item, "sku_id", "sku", "product_id", "ref_id", "id", "name", default="")
    ).strip()


def build_profile(closet_products: list[dict], answers: dict, style_preferences: dict | None = None) -> dict:
    style_preferences = style_preferences or {}

    closet_departments = []
    closet_types = []
    closet_colors = []
    closet_occasions = []
    closet_estampas = []

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
        if occ:
            closet_occasions.append(occ)
        if est:
            closet_estampas.append(est)
        closet_colors.extend(colors)

    preferred_colors = split_csv(style_preferences.get("preferred_colors"))
    preferred_styles = split_csv(style_preferences.get("preferred_styles"))
    preferred_occasions = split_csv(style_preferences.get("preferred_occasions"))

    return {
        "answer_occasion": normalize_text(answers.get("occasion")),
        "answer_goal": normalize_text(answers.get("goal")),
        "answer_style": normalize_text(answers.get("style")),
        "closet_departments": list(set(closet_departments)),
        "closet_types": list(set(closet_types)),
        "closet_colors": list(set(closet_colors)),
        "closet_occasions": list(set(closet_occasions)),
        "closet_estampas": list(set(closet_estampas)),
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

    if candidate_department and candidate_department in profile["closet_departments"]:
        score += 3
        reasons.append("conversa com categorias já compradas")

    if candidate_type and candidate_type in profile["closet_types"]:
        score += 4
        reasons.append("mantém coerência com o tipo de peça do closet")

    if candidate_occasion and candidate_occasion in profile["preferred_occasions"]:
        score += 5
        reasons.append("alinha com ocasiões preferidas")

    if candidate_occasion and candidate_occasion == profile["answer_occasion"]:
        score += 6
        reasons.append("combina com a ocasião escolhida")

    if candidate_estamparia and candidate_estamparia in profile["closet_estampas"]:
        score += 2
        reasons.append("mantém linguagem de estamparia parecida")

    if any(color in profile["preferred_colors"] for color in candidate_colors):
        score += 4
        reasons.append("segue paleta de cor preferida")

    if any(color in profile["closet_colors"] for color in candidate_colors):
        score += 3
        reasons.append("combina com as cores do closet")

    goal = profile["answer_goal"]
    if goal == "cross_sell":
        if candidate_type in ["acessorio", "acessório", "saida", "saída", "sandalia", "bolsa"]:
            score += 4
            reasons.append("bom item de complemento para cross sell")

    if goal == "up_sell":
        if candidate_department in ["vestidos", "feminino", "resort", "alfaiataria"]:
            score += 4
            reasons.append("tem potencial de upgrade de look")

    style = profile["answer_style"]
    if style and style in normalize_text(candidate.get("name", "")):
        score += 2
        reasons.append("reforça o estilo buscado")

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

    owned_ids = {get_item_identity(item) for item in closet_products if get_item_identity(item)}
    scored = []

    for candidate in catalog:
        candidate_id = get_item_identity(candidate)
        if not candidate_id or candidate_id in owned_ids:
            continue

        score, reasons = score_candidate(candidate, profile)
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