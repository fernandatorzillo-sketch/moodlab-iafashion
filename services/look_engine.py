from typing import Any


def normalize_text(value: Any) -> str:
    return str(value or "").strip().lower()


def get_field(item: dict[str, Any], *keys: str, default: Any = "") -> Any:
    for key in keys:
        if key in item and item.get(key) not in [None, ""]:
            return item.get(key)
    return default


def item_text(item: dict[str, Any]) -> str:
    return normalize_text(
        " ".join(
            [
                str(get_field(item, "name", "nome", default="")),
                str(get_field(item, "category", "categoria", default="")),
                str(get_field(item, "department", "departamento", default="")),
                str(get_field(item, "product_type", "tipo_produto", default="")),
                str(get_field(item, "occasion", "ocasiao", default="")),
                str(get_field(item, "collection", "colecao", default="")),
            ]
        )
    )


def product_type_of(item: dict[str, Any]) -> str:
    text = item_text(item)

    if any(x in text for x in ["biquini", "biquíni", "sutiã", "sutia", "calcinha"]):
        return "biquini"

    if any(x in text for x in ["maiô", "maio"]):
        return "maio"

    if any(x in text for x in ["saída", "saida", "pareô", "pareo"]):
        return "saida"

    if "vestido" in text:
        return "vestido"

    if any(x in text for x in ["short", "calça", "calca", "pantalona", "saia"]):
        return "bottom"

    if any(x in text for x in ["camisa", "camiseta", "blusa", "top", "cropped", "body"]):
        return "top"

    if any(x in text for x in ["bolsa", "sandália", "sandalia", "chapéu", "chapeu"]):
        return "acessorio"

    return "outro"


def is_home_item(item: dict[str, Any]) -> bool:
    text = item_text(item)
    blocked = [
        "bandeja",
        "copo",
        "taça",
        "taca",
        "vaso",
        "porta",
        "guardanapo",
        "mesa",
        "prato",
        "casa",
        "decor",
        "home",
        "almofada",
        "toalha",
        "jogo americano",
    ]
    return any(term in text for term in blocked)


def is_fashion_item(item: dict[str, Any]) -> bool:
    return not is_home_item(item) and product_type_of(item) != "outro"


def dedupe_by_sku(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen = set()
    result = []

    for item in items:
        key = str(
            get_field(item, "sku_id", "sku", "product_id", "produto_id", "id", default="")
        ).strip()

        if not key:
            key = str(get_field(item, "name", "nome", default="")).strip()

        if key and key not in seen:
            seen.add(key)
            result.append(item)

    return result


def make_look(title: str, occasion: str, items: list[dict[str, Any]], reason: str) -> dict[str, Any]:
    return {
        "title": title,
        "titulo": title,
        "occasion": occasion,
        "ocasiao": occasion,
        "items": items,
        "produtos": items,
        "reason": reason,
        "motivo": reason,
        "count": len(items),
    }


def build_looks(closet_items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    items = dedupe_by_sku([item for item in closet_items if is_fashion_item(item)])

    beachwear = [i for i in items if product_type_of(i) in {"biquini", "maio"}]
    saidas = [i for i in items if product_type_of(i) == "saida"]
    tops = [i for i in items if product_type_of(i) == "top"]
    bottoms = [i for i in items if product_type_of(i) == "bottom"]
    vestidos = [i for i in items if product_type_of(i) == "vestido"]
    acessorios = [i for i in items if product_type_of(i) == "acessorio"]

    looks = []

    if beachwear:
        look_items = [beachwear[0]]

        if saidas:
            look_items.append(saidas[0])

        if acessorios:
            look_items.append(acessorios[0])

        if len(look_items) >= 1:
            looks.append(
                make_look(
                    title="Look Praia",
                    occasion="praia",
                    items=look_items,
                    reason="Combinação criada com peças de moda praia do seu histórico.",
                )
            )

    if tops and bottoms:
        look_items = [tops[0], bottoms[0]]

        if acessorios:
            look_items.append(acessorios[0])

        looks.append(
            make_look(
                title="Look Casual",
                occasion="dia_a_dia",
                items=look_items,
                reason="Combinação criada com parte de cima e parte de baixo do seu closet.",
            )
        )

    if vestidos:
        look_items = [vestidos[0]]

        if acessorios:
            look_items.append(acessorios[0])

        looks.append(
            make_look(
                title="Look Resort",
                occasion="resort",
                items=look_items,
                reason="Combinação criada a partir de vestido ou peça única do seu closet.",
            )
        )

    if saidas and beachwear:
        look_items = [beachwear[0], saidas[0]]

        looks.append(
            make_look(
                title="Look Pós-Praia",
                occasion="resort",
                items=look_items,
                reason="Combinação pensada para saída de praia ou momentos de resort.",
            )
        )

    return looks[:6]