import json
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_MODELS_DIR = BASE_DIR / "data_models"


def load_json(filename: str, default: Any = None) -> Any:
    path = DATA_MODELS_DIR / filename
    if not path.exists():
        return default if default is not None else []

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def normalize_text(value: Any) -> str:
    return str(value or "").strip().lower()


def normalize_email(email: str) -> str:
    return normalize_text(email)


def as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def to_str(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def safe_first(values: list[Any], default: Any = "") -> Any:
    return values[0] if values else default


def flatten_catalog(products_enriched: list[dict[str, Any]]) -> list[dict[str, Any]]:
    flattened: list[dict[str, Any]] = []

    for product in products_enriched or []:
        if not isinstance(product, dict):
            continue

        sku_details = product.get("sku_details") or []
        if sku_details and isinstance(sku_details, list):
            for sku in sku_details:
                if not isinstance(sku, dict):
                    continue
                merged = dict(product)
                merged.update(sku)
                flattened.append(merged)
        else:
            flattened.append(product)

    return flattened


def build_catalog_indexes(flat_catalog: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    by_sku: dict[str, dict[str, Any]] = {}
    by_product_id: dict[str, dict[str, Any]] = {}
    by_ref_id: dict[str, dict[str, Any]] = {}

    for item in flat_catalog:
        sku_id = to_str(item.get("sku_id") or item.get("sku"))
        product_id = to_str(item.get("product_id") or item.get("id"))
        ref_id = to_str(item.get("ref_id") or item.get("RefId"))

        if sku_id and sku_id not in by_sku:
            by_sku[sku_id] = item

        if product_id and product_id not in by_product_id:
            by_product_id[product_id] = item

        if ref_id and ref_id not in by_ref_id:
            by_ref_id[ref_id] = item

    return {
        "by_sku": by_sku,
        "by_product_id": by_product_id,
        "by_ref_id": by_ref_id,
    }


def find_image_url(item: dict[str, Any]) -> str:
    image = item.get("imagem_url") or item.get("image_url")
    if image:
        return str(image)

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


def spec_values(item: dict[str, Any], candidate_names: list[str]) -> list[str]:
    specs = item.get("specifications") or {}
    if not isinstance(specs, dict):
        return []

    normalized_candidates = {normalize_text(name) for name in candidate_names}
    values: list[str] = []

    for key, raw_values in specs.items():
        if normalize_text(key) not in normalized_candidates:
            continue

        for value in as_list(raw_values):
            text = to_str(value)
            if text and text not in values:
                values.append(text)

    return values


def get_gender(item: dict[str, Any]) -> str:
    value = normalize_text(safe_first(spec_values(item, ["gender", "genero", "gênero", "sexo"])))
    return value


def get_department(item: dict[str, Any]) -> str:
    value = normalize_text(safe_first(spec_values(item, ["department", "departamento"])))
    return value


def get_product_type(item: dict[str, Any]) -> str:
    value = normalize_text(safe_first(spec_values(item, ["tipo", "tipo de produto", "product type", "categoria", "subcategoria"])))
    if value:
        return value

    fallback_name = normalize_text(item.get("name") or item.get("product_name"))
    if any(x in fallback_name for x in ["biquini", "biquíni", "sutia", "sutiã", "calcinha"]):
        return "beachwear"
    if any(x in fallback_name for x in ["maio", "maiô"]):
        return "maio"
    if any(x in fallback_name for x in ["saida", "saída", "kimono", "pareo", "pareô"]):
        return "saida_praia"
    if "saia" in fallback_name:
        return "saia"
    if "vestido" in fallback_name:
        return "vestido"
    if any(x in fallback_name for x in ["vela", "manta", "almofada", "decor"]):
        return "casa"
    return "outros"


def get_color(item: dict[str, Any]) -> str:
    return safe_first(spec_values(item, ["cor", "color"]), "")


def get_collection(item: dict[str, Any]) -> str:
    return safe_first(spec_values(item, ["colecao", "coleção", "collection"]), "")


def get_style(item: dict[str, Any]) -> str:
    return safe_first(spec_values(item, ["estilo", "style"]), "")


def resolve_catalog_product(
    raw_item: dict[str, Any],
    catalog_indexes: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    sku_id = to_str(raw_item.get("sku_id") or raw_item.get("sku"))
    product_id = to_str(raw_item.get("product_id") or raw_item.get("id"))
    ref_id = to_str(raw_item.get("ref_id") or raw_item.get("RefId"))

    if sku_id and sku_id in catalog_indexes["by_sku"]:
        return catalog_indexes["by_sku"][sku_id]

    if product_id and product_id in catalog_indexes["by_product_id"]:
        return catalog_indexes["by_product_id"][product_id]

    if ref_id and ref_id in catalog_indexes["by_ref_id"]:
        return catalog_indexes["by_ref_id"][ref_id]

    return {}


def normalize_closet_product(
    raw_item: dict[str, Any],
    catalog_product: dict[str, Any] | None = None,
) -> dict[str, Any]:
    catalog_product = catalog_product or {}

    source = dict(catalog_product)
    source.update(raw_item or {})

    sku_id = to_str(source.get("sku") or source.get("sku_id"))
    product_id = to_str(source.get("product_id") or source.get("id"))
    ref_id = to_str(source.get("ref_id") or source.get("RefId"))

    name = (
        source.get("name")
        or source.get("produto")
        or source.get("product_name")
        or "Produto"
    )

    image_url = find_image_url(source)

    return {
        "id": product_id,
        "product_id": product_id,
        "sku": sku_id,
        "sku_id": sku_id,
        "ref_id": ref_id,
        "nome": name,
        "name": name,
        "categoria": get_product_type(source),
        "department": get_department(source),
        "gender": get_gender(source),
        "cor": get_color(source),
        "colecao": get_collection(source),
        "estilo": get_style(source),
        "imagem_url": image_url,
        "image_url": image_url,
        "link_produto": source.get("detailUrl") or source.get("link") or "#",
        "price": source.get("price") or source.get("preco"),
        "quantity": source.get("quantity") or source.get("total_quantity") or 1,
        "total_spent": source.get("total_spent") or source.get("valor_total"),
        "specifications": source.get("specifications") or {},
        "produto_info": source,
    }


def find_orders_for_email(orders: list[Any], email_normalized: str) -> list[dict[str, Any]]:
    matched: list[dict[str, Any]] = []

    for order in orders or []:
        if not isinstance(order, dict):
            continue

        possible_emails = [
            order.get("email"),
            order.get("client_email"),
            order.get("customer_email"),
            order.get("Email"),
            order.get("ClientEmail"),
        ]

        if any(normalize_email(e) == email_normalized for e in possible_emails if e):
            matched.append(order)

    return matched


def extract_order_items(order: dict[str, Any]) -> list[dict[str, Any]]:
    for key in ["items", "Items", "products", "Products", "closet_products"]:
        items = order.get(key)
        if isinstance(items, list):
            return [item for item in items if isinstance(item, dict)]
    return []


def aggregate_items_from_orders(
    matched_orders: list[dict[str, Any]],
    catalog_indexes: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    aggregated: dict[str, dict[str, Any]] = {}

    for order in matched_orders:
        for raw_item in extract_order_items(order):
            catalog_product = resolve_catalog_product(raw_item, catalog_indexes)
            normalized = normalize_closet_product(raw_item, catalog_product)

            key = normalized["sku_id"] or normalized["product_id"] or normalized["ref_id"] or normalized["name"]
            if not key:
                continue

            if key not in aggregated:
                aggregated[key] = normalized
            else:
                aggregated[key]["quantity"] = (aggregated[key].get("quantity") or 0) + (normalized.get("quantity") or 0)

    return list(aggregated.values())


def find_prebuilt_closet(email_normalized: str) -> list[dict[str, Any]]:
    candidate_files = [
        "customer_closets.json",
        "closets.json",
        "closet.json",
    ]

    for filename in candidate_files:
        data = load_json(filename, default=None)
        if data is None:
            continue

        if isinstance(data, dict):
            for key, value in data.items():
                if normalize_email(key) == email_normalized and isinstance(value, list):
                    return [item for item in value if isinstance(item, dict)]

        if isinstance(data, list):
            for row in data:
                if not isinstance(row, dict):
                    continue
                row_email = normalize_email(
                    row.get("email")
                    or row.get("client_email")
                    or row.get("customer_email")
                )
                if row_email != email_normalized:
                    continue

                items = row.get("closet_products") or row.get("items") or row.get("products")
                if isinstance(items, list):
                    return [item for item in items if isinstance(item, dict)]

    return []


def build_closet_from_prebuilt(
    prebuilt_items: list[dict[str, Any]],
    catalog_indexes: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []

    for raw_item in prebuilt_items:
        catalog_product = resolve_catalog_product(raw_item, catalog_indexes)
        normalized = normalize_closet_product(raw_item, catalog_product)
        result.append(normalized)

    return result


def get_customer_closet(email: str) -> dict[str, Any]:
    email_normalized = normalize_email(email)

    if not email_normalized:
        return {
            "email": "",
            "total_pedidos": 0,
            "total_skus": 0,
            "closet_products": [],
        }

    products_enriched = load_json("products_enriched.json", default=[])
    flat_catalog = flatten_catalog(products_enriched)
    catalog_indexes = build_catalog_indexes(flat_catalog)

    prebuilt_items = find_prebuilt_closet(email_normalized)
    if prebuilt_items:
        closet_products = build_closet_from_prebuilt(prebuilt_items, catalog_indexes)
        return {
            "email": email_normalized,
            "total_pedidos": 1,
            "total_skus": len(closet_products),
            "closet_products": closet_products,
        }

    orders = load_json("orders.json", default=[])
    matched_orders = find_orders_for_email(orders, email_normalized)
    if matched_orders:
        closet_products = aggregate_items_from_orders(matched_orders, catalog_indexes)
        return {
            "email": email_normalized,
            "total_pedidos": len(matched_orders),
            "total_skus": len(closet_products),
            "closet_products": closet_products,
        }

    mock_orders = load_json("pedidos.json", default=[])
    matched_mock_orders = find_orders_for_email(mock_orders, email_normalized)
    if matched_mock_orders:
        closet_products = aggregate_items_from_orders(matched_mock_orders, catalog_indexes)
        return {
            "email": email_normalized,
            "total_pedidos": len(matched_mock_orders),
            "total_skus": len(closet_products),
            "closet_products": closet_products,
        }

    return {
        "email": email_normalized,
        "total_pedidos": 0,
        "total_skus": 0,
        "closet_products": [],
    }