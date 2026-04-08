from typing import Any


def normalize_text(value: Any) -> str:
    return str(value or "").strip().lower()


def get_field(item: dict[str, Any], *keys: str, default: Any = "") -> Any:
    for key in keys:
        if key in item and item.get(key) not in [None, ""]:
            return item.get(key)
    return default


def category_of(item: dict[str, Any]) -> str:
    return normalize_text(
        get_field(item, "category", "categoria", "product_type", "tipo_produto", default="")
    )


def build_looks(closet_items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    beachwear = [i for i in closet_items if category_of(i) in {"beachwear", "biquini", "bikini", "maio"}]
    saidas = [i for i in closet_items if category_of(i) in {"saida_praia", "saida", "saia"}]
    acessorios = [i for i in closet_items if category_of(i) in {"acessorio", "acessorio_praia"}]
    vestidos = [i for i in closet_items if category_of(i) in {"vestido", "vestido_praia"}]

    looks = []

    if beachwear:
        items = [beachwear[0]]
        if saidas:
            items.append(saidas[0])
        if acessorios:
            items.append(acessorios[0])

        looks.append(
            {
                "title": "Look Praia",
                "occasion": "praia",
                "items": items,
            }
        )

    if vestidos:
        items = [vestidos[0]]
        if acessorios:
            items.append(acessorios[0])

        looks.append(
            {
                "title": "Look Resort",
                "occasion": "resort",
                "items": items,
            }
        )

    return looks