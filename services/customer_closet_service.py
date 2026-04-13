import os
from typing import Any

import requests

from services.cache_service import get_cache, set_cache


def normalize_text(value: Any) -> str:
    return str(value or "").strip().lower()


def normalize_email(email: str) -> str:
    return normalize_text(email)


def to_str(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def get_vtex_credentials():
    account = os.getenv("VTEX_ACCOUNT", "").strip()
    app_key = os.getenv("VTEX_APP_KEY", "").strip()
    app_token = os.getenv("VTEX_APP_TOKEN", "").strip()

    if not account or not app_key or not app_token:
        raise Exception("VTEX_ACCOUNT, VTEX_APP_KEY ou VTEX_APP_TOKEN não configurados")

    return account, app_key, app_token


def get_headers(app_key: str, app_token: str):
    return {
        "X-VTEX-API-AppKey": app_key,
        "X-VTEX-API-AppToken": app_token,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def get_order_detail(order_id: str) -> dict[str, Any]:
    account, app_key, app_token = get_vtex_credentials()
    headers = get_headers(app_key, app_token)

    url = f"https://{account}.vtexcommercestable.com.br/api/oms/pvt/orders/{order_id}"
    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()
    return response.json()


def search_orders_by_email(email: str) -> list[dict[str, Any]]:
    account, app_key, app_token = get_vtex_credentials()
    headers = get_headers(app_key, app_token)

    url = f"https://{account}.vtexcommercestable.com.br/api/oms/pvt/orders"

    email_normalized = normalize_email(email)
    matched_orders: list[dict[str, Any]] = []

    page = 1
    per_page = 50
    max_pages = 10

    while page <= max_pages:
        params = {
            "f_creationDate": "creationDate:[2024-01-01T00:00:00.000Z TO 2035-01-01T00:00:00.000Z]",
            "page": page,
            "per_page": per_page,
        }

        response = requests.get(url, headers=headers, params=params, timeout=30)
        response.raise_for_status()

        data = response.json()
        orders = data.get("list", []) or []

        if not orders:
            break

        for order in orders:
            order_id = order.get("orderId")
            if not order_id:
                continue

            try:
                detail = get_order_detail(order_id)
                client_profile = detail.get("clientProfileData") or {}
                order_email = normalize_email(client_profile.get("email"))

                if order_email == email_normalized:
                    matched_orders.append(detail)
            except Exception as e:
                print(f"Erro ao detalhar pedido {order_id}: {e}")

        if len(orders) < per_page:
            break

        page += 1

    return matched_orders


def get_catalog_by_product_id(product_id: str) -> dict[str, Any]:
    if not product_id:
        return {}

    account, app_key, app_token = get_vtex_credentials()
    headers = get_headers(app_key, app_token)

    url = f"https://{account}.vtexcommercestable.com.br/api/catalog_system/pvt/products/ProductGet/{product_id}"

    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        return response.json() or {}
    except Exception as e:
        print(f"Erro ao buscar catálogo por product_id {product_id}: {e}")
        return {}


def search_catalog_by_ref_id(ref_id: str) -> dict[str, Any]:
    if not ref_id:
        return {}

    account, app_key, app_token = get_vtex_credentials()
    headers = get_headers(app_key, app_token)

    url = f"https://{account}.vtexcommercestable.com.br/api/catalog_system/pvt/products/productgetbyrefid/{ref_id}"

    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        return response.json() or {}
    except Exception as e:
        print(f"Erro ao buscar catálogo por ref_id {ref_id}: {e}")
        return {}


def get_sku_detail(sku_id: str) -> dict[str, Any]:
    if not sku_id:
        return {}

    account, app_key, app_token = get_vtex_credentials()
    headers = get_headers(app_key, app_token)

    url = f"https://{account}.vtexcommercestable.com.br/api/catalog_system/pvt/sku/stockkeepingunitbyid/{sku_id}"

    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        return response.json() or {}
    except Exception as e:
        print(f"Erro ao buscar SKU {sku_id}: {e}")
        return {}


def get_images_by_product_id(product_id: str) -> list[dict[str, Any]]:
    if not product_id:
        return []

    account, app_key, app_token = get_vtex_credentials()
    headers = get_headers(app_key, app_token)

    url = f"https://{account}.vtexcommercestable.com.br/api/catalog/pvt/product/{product_id}/images"

    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()
        return data if isinstance(data, list) else []
    except Exception as e:
        print(f"Erro ao buscar imagens do produto {product_id}: {e}")
        return []


def get_product_link_by_slug_or_id(product_data: dict[str, Any], product_id: str) -> str:
    link_text = (
        product_data.get("LinkId")
        or product_data.get("linkId")
        or product_data.get("Name")
        or product_data.get("name")
        or ""
    )

    if isinstance(link_text, str) and link_text.strip():
        slug = (
            link_text.strip()
            .lower()
            .replace(" ", "-")
            .replace("/", "-")
        )
        return f"https://www.aguadecoco.com.br/{slug}/p"

    if product_id:
        return f"https://www.aguadecoco.com.br/product/{product_id}/p"

    return "https://www.aguadecoco.com.br/"


def pick_best_image(
    oms_item: dict[str, Any],
    sku_data: dict[str, Any],
    product_images: list[dict[str, Any]],
) -> str:
    image_url = oms_item.get("imageUrl") or ""
    if image_url:
        return image_url

    sku_image = (
        sku_data.get("ImageUrl")
        or sku_data.get("imageUrl")
        or ""
    )
    if sku_image:
        return sku_image

    for img in product_images:
        if not isinstance(img, dict):
            continue
        candidate = img.get("Path") or img.get("Url") or img.get("ArchiveId")
        if isinstance(candidate, str) and candidate.strip():
            if candidate.startswith("http"):
                return candidate
            if candidate.startswith("/"):
                return f"https://www.aguadecoco.com.br{candidate}"

    return ""


def get_category_from_product(product_data: dict[str, Any]) -> str:
    category_name = (
        product_data.get("CategoryName")
        or product_data.get("categoryName")
        or ""
    )
    if category_name:
        return str(category_name)

    categories = product_data.get("Categories") or product_data.get("categories") or []
    if isinstance(categories, list) and categories:
        last = categories[-1]
        if isinstance(last, dict):
            return str(last.get("Name") or last.get("name") or "")
        return str(last)

    return ""


def normalize_order_item(item: dict[str, Any]) -> dict[str, Any]:
    additional_info = item.get("additionalInfo") or {}
    categories = item.get("productCategories") or {}

    category = ""
    if isinstance(categories, dict) and categories:
        vals = [v for v in categories.values() if v]
        if vals:
            category = vals[-1]

    image_url = item.get("imageUrl") or ""
    name = item.get("name") or "Produto"
    ref_id = to_str(item.get("refId"))
    product_id = to_str(item.get("productId"))
    sku_id = to_str(item.get("id"))

    price_raw = item.get("price", 0) or 0
    quantity = item.get("quantity", 1) or 1

    price = price_raw / 100 if isinstance(price_raw, (int, float)) else price_raw
    total_spent = price * quantity if isinstance(price, (int, float)) else 0

    brand_name = additional_info.get("brandName") or ""
    product_ref = additional_info.get("productRefId") or ref_id

    return {
        "id": product_id,
        "product_id": product_id,
        "sku": sku_id,
        "sku_id": sku_id,
        "ref_id": product_ref,
        "nome": name,
        "name": name,
        "categoria": category,
        "category": category,
        "department": "",
        "gender": "",
        "cor": "",
        "colecao": "",
        "estilo": "",
        "brand": brand_name,
        "imagem_url": image_url,
        "image_url": image_url,
        "link_produto": "#",
        "url": "#",
        "price": price,
        "quantity": quantity,
        "total_spent": total_spent,
        "produto_info": item,
    }


def enrich_item_with_catalog(item: dict[str, Any]) -> dict[str, Any]:
    product_id = to_str(item.get("product_id"))
    ref_id = to_str(item.get("ref_id"))
    sku_id = to_str(item.get("sku_id"))

    product_data = {}
    if product_id:
        product_data = get_catalog_by_product_id(product_id)

    if not product_data and ref_id:
        product_data = search_catalog_by_ref_id(ref_id)

    sku_data = get_sku_detail(sku_id) if sku_id else {}
    product_images = get_images_by_product_id(product_id) if product_id else []

    image_url = pick_best_image(item.get("produto_info", {}), sku_data, product_images)
    category = item.get("category") or get_category_from_product(product_data)
    product_link = get_product_link_by_slug_or_id(product_data, product_id)

    if not item.get("ref_id"):
        item["ref_id"] = to_str(
            product_data.get("RefId")
            or product_data.get("refId")
            or sku_data.get("RefId")
            or sku_data.get("refId")
        )

    item["categoria"] = category or item.get("categoria", "")
    item["category"] = category or item.get("category", "")
    item["department"] = (
        product_data.get("DepartmentName")
        or product_data.get("departmentName")
        or item.get("department", "")
    )
    item["imagem_url"] = image_url or item.get("imagem_url", "")
    item["image_url"] = image_url or item.get("image_url", "")
    item["link_produto"] = product_link or item.get("link_produto", "#")
    item["url"] = product_link or item.get("url", "#")

    return item


def aggregate_items_from_real_orders(orders: list[dict[str, Any]]) -> list[dict[str, Any]]:
    aggregated: dict[str, dict[str, Any]] = {}

    for order in orders:
        items = order.get("items", []) or []

        for raw_item in items:
            normalized = normalize_order_item(raw_item)

            key = (
                normalized["sku_id"]
                or normalized["product_id"]
                or normalized["ref_id"]
                or normalized["name"]
            )

            if not key:
                continue

            if key not in aggregated:
                aggregated[key] = normalized
            else:
                aggregated[key]["quantity"] = (
                    aggregated[key].get("quantity", 0) + normalized.get("quantity", 0)
                )
                aggregated[key]["total_spent"] = (
                    aggregated[key].get("total_spent", 0) + normalized.get("total_spent", 0)
                )

    result = list(aggregated.values())
    enriched_result = []

    for item in result:
        try:
            enriched_result.append(enrich_item_with_catalog(item))
        except Exception as e:
            print(f"Erro ao enriquecer item {item.get('name')}: {e}")
            enriched_result.append(item)

    return enriched_result


def get_customer_closet(email: str) -> dict[str, Any]:
    email_normalized = normalize_email(email)

    if not email_normalized:
        return {
            "email": "",
            "total_pedidos": 0,
            "total_skus": 0,
            "closet_products": [],
        }

    print("LOOKUP EMAIL:", email_normalized)

    orders = search_orders_by_email(email_normalized)
    print("ORDERS FOUND:", len(orders))

    closet_products = aggregate_items_from_real_orders(orders)
    print("CLOSET PRODUCTS:", len(closet_products))

    return {
        "email": email_normalized,
        "total_pedidos": len(orders),
        "total_skus": len(closet_products),
        "closet_products": closet_products,
    }


def get_customer_closet_payload(email: str) -> dict[str, Any]:
    email_normalized = normalize_email(email)
    cache_key = f"closet_payload:{email_normalized}"

    cached = get_cache(cache_key)
    if cached:
        return cached

    closet_data = get_customer_closet(email_normalized)
    closet_products = closet_data.get("closet_products", []) or []

    payload = {
        "customer": {
            "name": email_normalized.split("@")[0] if email_normalized else "Cliente",
            "email": email_normalized,
            "style_preferences": {},
        },
        "closet": closet_products,
        "looks": [],
        "recommendations": [],
        "meta": {
            "total_orders": closet_data.get("total_pedidos", 0),
            "total_skus": closet_data.get("total_skus", 0),
            "recommendations_count": 0,
            "looks_count": 0,
        },
    }

    set_cache(cache_key, payload)
    return payload