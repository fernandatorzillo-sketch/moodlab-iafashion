from typing import Any


def normalize_text(value: Any) -> str:
    return str(value or "").strip().lower()


def get_field(item: dict[str, Any], *keys: str, default: Any = "") -> Any:
    for key in keys:
        value = item.get(key)
        if value not in [None, ""]:
            return value
    return default


def infer_type(item: dict[str, Any]) -> str:
    text = normalize_text(
        " ".join(
            [
                str(get_field(item, "name", "nome")),
                str(get_field(item, "category", "categoria")),
                str(get_field(item, "department", "departamento")),
                str(get_field(item, "product_type", "tipo_produto")),
            ]
        )
    )

    if any(x in text for x in ["biquini", "biquíni", "calcinha", "sutia", "sutiã"]):
        return "biquini"
    if any(x in text for x in ["maio", "maiô"]):
        return "maio"
    if "vestido" in text:
        return "vestido"
    if any(x in text for x in ["saia", "pareo", "pareô", "saida", "saída"]):
        return "saida"
    if any(x in text for x in ["short", "calca", "calça", "pantalona"]):
        return "bottom"
    if any(x in text for x in ["camisa", "blusa", "cropped", "top", "camiseta"]):
        return "top"
    if any(x in text for x in ["bolsa", "chapeu", "chapéu", "sandalia", "sandália"]):
        return "acessorio"

    return "outro"


def build_looks(closet_items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    beachwear = [i for i in closet_items if infer_type(i) in {"biquini", "maio"}]
    tops = [i for i in closet_items if infer_type(i) == "top"]
    bottoms = [i for i in closet_items if infer_type(i) == "bottom"]
    saidas = [i for i in closet_items if infer_type(i) == "saida"]
    vestidos = [i for i in closet_items if infer_type(i) == "vestido"]
    acessorios = [i for i in closet_items if infer_type(i) == "acessorio"]

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

    if tops and bottoms:
        items = [tops[0], bottoms[0]]
        if acessorios:
            items.append(acessorios[0])

        looks.append(
            {
                "title": "Look Casual Chic",
                "occasion": "dia_a_dia",
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