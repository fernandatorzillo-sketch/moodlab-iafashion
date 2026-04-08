import math
from typing import Any


def normalize_text(value: Any) -> str:
    text = str(value or "").strip().lower()
    replacements = {
        "á": "a",
        "à": "a",
        "ã": "a",
        "â": "a",
        "é": "e",
        "ê": "e",
        "í": "i",
        "ó": "o",
        "ô": "o",
        "õ": "o",
        "ú": "u",
        "ç": "c",
        "/": " ",
        "-": " ",
        "_": " ",
        "|": " ",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return " ".join(text.split())


def normalize_id(value: Any) -> str:
    return str(value or "").strip()


def as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def get_field(item: dict[str, Any], *keys: str, default: Any = "") -> Any:
    for key in keys:
        if key in item and item.get(key) not in [None, ""]:
            return item.get(key)
    return default


def spec_values(item: dict[str, Any], candidate_names: list[str]) -> list[str]:
    specs = item.get("specifications") or {}
    if not isinstance(specs, dict):
        return []

    wanted = {normalize_text(name) for name in candidate_names}
    values: list[str] = []

    for key, raw_values in specs.items():
        if normalize_text(key) not in wanted:
            continue

        for value in as_list(raw_values):
            text = str(value or "").strip()
            if text and text not in values:
                values.append(text)

    return values


def product_name(item: dict[str, Any]) -> str:
    return str(
        get_field(item, "nome", "name", "product_name", "produto", default="Produto")
    )


def product_sku(item: dict[str, Any]) -> str:
    return normalize_id(get_field(item, "sku_id", "sku", default=""))


def product_id(item: dict[str, Any]) -> str:
    return normalize_id(get_field(item, "product_id", "id", default=""))


def product_ref(item: dict[str, Any]) -> str:
    return normalize_id(get_field(item, "ref_id", "RefId", default=""))


def product_link(item: dict[str, Any]) -> str:
    return str(get_field(item, "link_produto", "detailUrl", "link", default="#"))


def product_image(item: dict[str, Any]) -> str:
    direct = get_field(item, "imagem_url", "image_url", default="")
    if direct:
        return str(direct)

    images = item.get("images") or []
    if isinstance(images, list) and images:
        first = images[0]
        if isinstance(first, dict):
            return (
                first.get("ImageUrl")
                or first.get("imageUrl")
                or first.get("Url")
                or ""
            )
    return ""


def product_price(item: dict[str, Any]) -> float:
    raw = get_field(item, "price", "preco", default=0)
    try:
        return float(raw or 0)
    except Exception:
        return 0.0


def product_gender(item: dict[str, Any]) -> str:
    direct = normalize_text(get_field(item, "gender", "genero", "gênero", default=""))
    if direct:
        return direct

    spec = spec_values(item, ["gender", "genero", "gênero", "sexo"])
    return normalize_text(spec[0]) if spec else ""


def product_department(item: dict[str, Any]) -> str:
    direct = normalize_text(get_field(item, "department", "departamento", default=""))
    if direct:
        return direct

    spec = spec_values(item, ["department", "departamento"])
    return normalize_text(spec[0]) if spec else ""


def product_category(item: dict[str, Any]) -> str:
    direct = normalize_text(
        get_field(
            item,
            "categoria",
            "category",
            "product_type",
            "tipo_produto",
            "tipo",
            default="",
        )
    )
    if direct:
        return direct

    spec = spec_values(
        item,
        [
            "tipo",
            "tipo de produto",
            "product type",
            "categoria",
            "subcategoria",
        ],
    )
    if spec:
        return normalize_text(spec[0])

    name = normalize_text(product_name(item))
    if any(x in name for x in ["biquini", "biquíni", "sutia", "sutiã", "calcinha"]):
        return "beachwear"
    if any(x in name for x in ["maio", "maiô"]):
        return "maio"
    if any(x in name for x in ["saida", "saída", "canga", "pareo", "pareô", "kimono"]):
        return "saida_praia"
    if "vestido" in name:
        return "vestido"
    if "saia" in name:
        return "saia"
    if any(x in name for x in ["bone", "boné", "oculos", "óculos", "bolsa", "chapeu", "chapéu"]):
        return "acessorio"
    if any(x in name for x in ["vela", "almofada", "manta", "vaso", "casa", "decor"]):
        return "casa"
    return "outros"


def product_color(item: dict[str, Any]) -> str:
    direct = normalize_text(get_field(item, "cor", "color", default=""))
    if direct:
        return direct

    spec = spec_values(item, ["cor", "color"])
    return normalize_text(spec[0]) if spec else ""


def product_collection(item: dict[str, Any]) -> str:
    direct = normalize_text(get_field(item, "colecao", "coleção", "collection", default=""))
    if direct:
        return direct

    spec = spec_values(item, ["colecao", "coleção", "collection"])
    return normalize_text(spec[0]) if spec else ""


def product_style(item: dict[str, Any]) -> str:
    direct = normalize_text(get_field(item, "estilo", "style", default=""))
    if direct:
        return direct

    spec = spec_values(item, ["estilo", "style"])
    return normalize_text(spec[0]) if spec else ""


def infer_profile(closet_products: list[dict[str, Any]]) -> dict[str, Any]:
    def top_value(values: list[str]) -> str:
        clean = [v for v in values if v]
        if not clean:
            return ""
        return max(set(clean), key=clean.count)

    genders = [product_gender(p) for p in closet_products]
    departments = [product_department(p) for p in closet_products]
    categories = [product_category(p) for p in closet_products]
    colors = [product_color(p) for p in closet_products]
    collections = [product_collection(p) for p in closet_products]
    styles = [product_style(p) for p in closet_products]

    return {
        "dominant_gender": top_value(genders),
        "dominant_department": top_value(departments),
        "dominant_category": top_value(categories),
        "dominant_color": top_value(colors),
        "dominant_collection": top_value(collections),
        "dominant_style": top_value(styles),
        "owned_categories": sorted(list({c for c in categories if c})),
        "owned_departments": sorted(list({d for d in departments if d})),
        "owned_collections": sorted(list({c for c in collections if c})),
    }


def get_owned_sets(closet_products: list[dict[str, Any]]) -> dict[str, set[str]]:
    return {
        "sku_ids": {product_sku(p) for p in closet_products if product_sku(p)},
        "product_ids": {product_id(p) for p in closet_products if product_id(p)},
        "ref_ids": {product_ref(p) for p in closet_products if product_ref(p)},
        "names": {normalize_text(product_name(p)) for p in closet_products if product_name(p)},
    }


def is_already_owned(candidate: dict[str, Any], owned_sets: dict[str, set[str]]) -> bool:
    if product_sku(candidate) and product_sku(candidate) in owned_sets["sku_ids"]:
        return True
    if product_id(candidate) and product_id(candidate) in owned_sets["product_ids"]:
        return True
    if product_ref(candidate) and product_ref(candidate) in owned_sets["ref_ids"]:
        return True
    if normalize_text(product_name(candidate)) in owned_sets["names"]:
        return True
    return False


def look_rules_for_answers(answers: dict[str, Any], profile: dict[str, Any]) -> dict[str, Any]:
    ocasiao = normalize_text(answers.get("ocasiao", ""))
    objetivo = normalize_text(answers.get("objetivo", ""))
    estilo = normalize_text(answers.get("estilo", ""))
    dominant_category = profile.get("dominant_category", "")

    allowed_categories: set[str] = set()
    blocked_categories: set[str] = {"casa"}

    if dominant_category in {"beachwear", "maio", "saida_praia"}:
        allowed_categories.update(
            {
                "beachwear",
                "maio",
                "saida_praia",
                "saia",
                "acessorio",
                "acessorio_praia",
            }
        )

        if ocasiao in {"praia", "praia resort", "resort"}:
            allowed_categories.update(
                {
                    "beachwear",
                    "maio",
                    "saida_praia",
                    "saia",
                    "acessorio",
                    "acessorio_praia",
                }
            )

        if objetivo == "completar look" or objetivo == "completar_look":
            allowed_categories.update({"saida_praia", "saia", "acessorio", "acessorio_praia"})
            blocked_categories.update({"vestido"})

        if objetivo == "similares":
            allowed_categories.update({"beachwear", "maio"})

    else:
        allowed_categories.update(
            {
                "vestido",
                "saia",
                "acessorio",
                "outros",
                profile.get("dominant_category", ""),
            }
        )

    return {
        "ocasiao": ocasiao,
        "objetivo": objetivo,
        "estilo": estilo,
        "allowed_categories": {x for x in allowed_categories if x},
        "blocked_categories": blocked_categories,
    }


def candidate_blocked(
    candidate: dict[str, Any],
    profile: dict[str, Any],
    rules: dict[str, Any],
) -> bool:
    category = product_category(candidate)
    department = product_department(candidate)
    gender = product_gender(candidate)

    if category in rules["blocked_categories"]:
        return True

    if department == "casa" or category == "casa":
        return True

    dominant_gender = profile.get("dominant_gender", "")
    if dominant_gender == "feminino" and gender == "masculino":
        return True
    if dominant_gender == "masculino" and gender == "feminino":
        return True

    allowed_categories = rules["allowed_categories"]
    if allowed_categories and category not in allowed_categories:
        return True

    return False


def score_candidate(
    candidate: dict[str, Any],
    closet_products: list[dict[str, Any]],
    profile: dict[str, Any],
    rules: dict[str, Any],
) -> tuple[float, list[str]]:
    score = 0.0
    reasons: list[str] = []

    category = product_category(candidate)
    department = product_department(candidate)
    color = product_color(candidate)
    collection = product_collection(candidate)
    style = product_style(candidate)
    price = product_price(candidate)

    dominant_category = profile.get("dominant_category", "")
    dominant_department = profile.get("dominant_department", "")
    dominant_color = profile.get("dominant_color", "")
    dominant_collection = profile.get("dominant_collection", "")
    dominant_style = profile.get("dominant_style", "")

    if category == dominant_category:
        score += 40
        reasons.append("Parecido com o que ela já compra")

    if department and dominant_department and department == dominant_department:
        score += 25
        reasons.append("Mesmo departamento das compras anteriores")

    if color and dominant_color and color == dominant_color:
        score += 10
        reasons.append("Cor alinhada ao closet")

    if collection and dominant_collection and collection == dominant_collection:
        score += 10
        reasons.append("Coleção próxima do histórico")

    if style and dominant_style and style == dominant_style:
        score += 12
        reasons.append("Estilo compatível")

    objetivo = rules["objetivo"]
    ocasiao = rules["ocasiao"]
    estilo_quiz = rules["estilo"]

    if dominant_category in {"beachwear", "maio", "saida_praia"}:
        if category in {"saida_praia", "saia", "acessorio", "acessorio_praia"}:
            score += 35
            reasons.append("Complementa compras de praia")

        if ocasiao in {"praia", "praia resort", "resort"} and category in {
            "beachwear",
            "maio",
            "saida_praia",
            "saia",
            "acessorio",
            "acessorio_praia",
        }:
            score += 30
            reasons.append("Faz sentido para look praia")

        if category == "vestido":
            score -= 80

    if objetivo in {"completar_look", "completar look"}:
        if category in {"saida_praia", "saia", "acessorio", "acessorio_praia"}:
            score += 30
            reasons.append("Ajuda a completar o look")
        if category in {"beachwear", "maio"}:
            score += 8

    if objetivo == "similares":
        if category == dominant_category:
            score += 20
            reasons.append("Peça similar ao histórico")

    if objetivo == "novidades":
        score += 5

    if estilo_quiz and style and style == estilo_quiz:
        score += 18
        reasons.append("Combina com o estilo escolhido")

    if price > 0:
        avg_price = average_price(closet_products)
        if avg_price > 0:
            diff_ratio = abs(price - avg_price) / max(avg_price, 1)
            score += max(0, 12 - (diff_ratio * 10))

    reasons = dedupe_preserve_order(reasons)
    return score, reasons


def average_price(products: list[dict[str, Any]]) -> float:
    prices = [product_price(p) for p in products if product_price(p) > 0]
    if not prices:
        return 0.0
    return sum(prices) / len(prices)


def dedupe_preserve_order(items: list[str]) -> list[str]:
    seen = set()
    result = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


def build_recommendations(
    closet_products: list[dict[str, Any]],
    catalog: list[dict[str, Any]],
    answers: dict[str, Any],
    limit: int = 8,
) -> dict[str, Any]:
    profile = infer_profile(closet_products)
    owned_sets = get_owned_sets(closet_products)
    rules = look_rules_for_answers(answers, profile)

    ranked: list[dict[str, Any]] = []

    for candidate in catalog:
        if is_already_owned(candidate, owned_sets):
            continue

        if candidate_blocked(candidate, profile, rules):
            continue

        score, reasons = score_candidate(candidate, closet_products, profile, rules)

        if score <= 0:
            continue

        ranked.append(
            {
                "produto_id": product_id(candidate),
                "sku_id": product_sku(candidate),
                "ref_id": product_ref(candidate),
                "nome": product_name(candidate),
                "imagem_url": product_image(candidate),
                "categoria": product_category(candidate),
                "departamento": product_department(candidate),
                "genero": product_gender(candidate),
                "cor": product_color(candidate),
                "colecao": product_collection(candidate),
                "estilo": product_style(candidate),
                "price": product_price(candidate),
                "link_produto": product_link(candidate),
                "motivo": reasons[0] if reasons else "Selecionado para você",
                "score": round(score, 2),
                "reasons": reasons,
            }
        )

    ranked.sort(key=lambda item: item["score"], reverse=True)

    return {
        "profile": profile,
        "rules": {
            "ocasiao": rules["ocasiao"],
            "objetivo": rules["objetivo"],
            "estilo": rules["estilo"],
            "allowed_categories": sorted(list(rules["allowed_categories"])),
            "blocked_categories": sorted(list(rules["blocked_categories"])),
        },
        "recommendations": ranked[:limit],
        "meta": {
            "catalog_size": len(catalog),
            "closet_size": len(closet_products),
            "ranked_count": len(ranked),
        },
    }