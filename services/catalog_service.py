import json
import os
from typing import Any


BASE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data_models")


def load_json(filename: str, default: Any = None):
    path = os.path.join(BASE_DIR, filename)

    if not os.path.exists(path):
        return default if default is not None else []

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def normalize_text(value: Any) -> str:
    return str(value or "").strip().lower()


def as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def first_non_empty(*values, default=""):
    for value in values:
        if value not in [None, "", []]:
            return value
    return default


def get_spec_value(item: dict[str, Any], keys: list[str], default=""):
    specs = item.get("specifications") or {}
    if not isinstance(specs, dict):
        specs = {}

    normalized_keys = [normalize_text(k) for k in keys]

    for key, value in specs.items():
        if normalize_text(key) in normalized_keys:
            if isinstance(value, list):
                return value[0] if value else default
            return value or default

    return default


def get_spec_list(item: dict[str, Any], keys: list[str]) -> list[str]:
    specs = item.get("specifications") or {}
    if not isinstance(specs, dict):
        specs = {}

    normalized_keys = [normalize_text(k) for k in keys]

    for key, value in specs.items():
        if normalize_text(key) in normalized_keys:
            if isinstance(value, list):
                return [str(v).strip() for v in value if str(v).strip()]
            if value:
                return [str(value).strip()]

    return []


def normalize_product(raw: dict[str, Any]) -> dict[str, Any]:
    sku_details = raw.get("sku_details") or []

    stock_quantity = 0
    sku_id = ""
    size = ""

    if isinstance(sku_details, list) and sku_details:
        first_sku = sku_details[0] if isinstance(sku_details[0], dict) else {}
        sku_id = str(
            first_non_empty(
                first_sku.get("sku_id"),
                first_sku.get("id"),
                raw.get("sku_id"),
                raw.get("sku"),
                default="",
            )
        ).strip()

        try:
            stock_quantity = int(
                first_non_empty(
                    first_sku.get("stock_quantity"),
                    first_sku.get("available_quantity"),
                    first_sku.get("estoque"),
                    raw.get("stock_quantity"),
                    raw.get("available_quantity"),
                    raw.get("estoque"),
                    default=0,
                ) or 0
            )
        except Exception:
            stock_quantity = 0

        size = str(
            first_non_empty(
                first_sku.get("size"),
                first_sku.get("tamanho"),
                default="",
            )
        ).strip()

    image_url = first_non_empty(
        raw.get("image_url"),
        raw.get("imagem_url"),
        raw.get("ImageUrl"),
        default="",
    )

    if not image_url:
        images = raw.get("images") or []
        if isinstance(images, list) and images:
            first = images[0]
            if isinstance(first, dict):
                image_url = first_non_empty(
                    first.get("imageUrl"),
                    first.get("ImageUrl"),
                    first.get("Url"),
                    default="",
                )

    product_url = first_non_empty(
        raw.get("product_url"),
        raw.get("url"),
        raw.get("link_produto"),
        raw.get("detailUrl"),
        default="#",
    )

    colors = first_non_empty(
        raw.get("colors"),
        raw.get("cores"),
        get_spec_list(raw, ["cor", "cores", "color", "colors"]),
        default=[],
    )

    if isinstance(colors, str):
        colors = [c.strip() for c in colors.split(",") if c.strip()]

    department = first_non_empty(
        raw.get("department"),
        raw.get("departamento"),
        get_spec_value(raw, ["departamento", "department"]),
        default="",
    )

    category = first_non_empty(
        raw.get("category"),
        raw.get("categoria"),
        raw.get("product_type"),
        raw.get("tipo_produto"),
        get_spec_value(raw, ["tipo de produto", "product type", "tipo", "categoria"]),
        default="",
    )

    occasion = first_non_empty(
        raw.get("occasion"),
        raw.get("ocasiao"),
        raw.get("ocasião"),
        get_spec_value(raw, ["ocasião", "occasion"]),
        default="",
    )

    estamparia = first_non_empty(
        raw.get("estamparia"),
        get_spec_value(raw, ["estamparia"]),
        default="",
    )

    gender = first_non_empty(
        raw.get("gender"),
        raw.get("genero"),
        raw.get("gênero"),
        get_spec_value(raw, ["gender", "genero", "gênero"]),
        default="",
    )

    in_stock = stock_quantity > 0

    return {
        "product_id": str(first_non_empty(raw.get("product_id"), raw.get("id"), default="")).strip(),
        "sku_id": sku_id,
        "ref_id": str(first_non_empty(raw.get("ref_id"), raw.get("RefId"), default="")).strip(),
        "name": first_non_empty(raw.get("name"), raw.get("nome"), raw.get("product_name"), default="Produto"),
        "department": str(department).strip(),
        "category": str(category).strip(),
        "product_type": str(category).strip(),
        "occasion": str(occasion).strip(),
        "colors": colors,
        "estamparia": str(estamparia).strip(),
        "size": size,
        "gender": str(gender).strip(),
        "image_url": image_url,
        "url": product_url,
        "brand": first_non_empty(raw.get("brand"), raw.get("brand_name"), default=""),
        "in_stock": in_stock,
        "stock_quantity": stock_quantity,
    }


async def get_catalog_products():
    raw_products = load_json("products_enriched.json", default=[])

    if not isinstance(raw_products, list):
        return []

    normalized = []
    for raw in raw_products:
        if not isinstance(raw, dict):
            continue

        product = normalize_product(raw)

        if product["in_stock"] and product["stock_quantity"] > 0:
            normalized.append(product)

    return normalized