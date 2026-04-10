import os
import requests
from typing import Any


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


def search_orders_by_email(email: str) -> list[dict[str, Any]]:
    account, app_key, app_token = get_vtex_credentials()
    headers = get_headers(app_key, app_token)

    url = f"https://{account}.vtexcommercestable.com.br/api/oms/pvt/orders"

    params = {
        "f_creationDate": "creationDate:[2024-01-01T00:00:00.000Z TO 2035-01-01T00:00:00.000Z]",
        "per_page": 50,
        "page": 1,
    }

    response = requests.get(url, headers=headers, params=params, timeout=30)
    response.raise_for_status()

    data = response.json()
    orders = data.get("list", []) or []

    matched = []
    email_normalized = normalize_email(email)

    for order in orders:
        client_name = normalize_email(order.get("clientName"))
        # OMS list nem sempre traz email, então pegamos detalhe depois
        order_id = order.get("orderId")
        if not order_id:
            continue

        try:
            detail = get_order_detail(order_id)
            client_profile = detail.get("clientProfileData") or {}
            order_email = normalize_email(client_profile.get("email"))
            if order_email == email_normalized:
                matched.append(detail)
        except Exception as e:
            print(f"Erro ao detalhar pedido {order_id}: {e}")

    return matched


def get_order_detail(order_id: str) -> dict[str, Any]:
    account, app_key, app_token = get_vtex_credentials()
    headers = get_headers(app_key, app_token)

    url = f"https://{account}.vtexcommercestable.com.br/api/oms/pvt/orders/{order_id}"
    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()
    return response.json()


def normalize_order_item(item: dict[str, Any]) -> dict[str, Any]:
    image_url = ""
    detail_url = "#"

    attachments = item.get("attachments") or []
    additional_info = item.get("additionalInfo") or {}

    if additional_info:
        image_url = additional_info.get("brandName", "")  # fallback temporário, substituído abaixo se existir imagem
        detail_url = additional_info.get("productRefId", "#")

    image_urls = item.get("imageUrl") or item.get("imageUrls") or ""
    if isinstance(image_urls, str) and image_urls:
        image_url = image_urls

    ref_id = to_str(item.get("refId"))
    product_id = to_str(item.get("productId"))
    sku_id = to_str(item.get("id"))
    name = item.get("name") or "Produto"

    category = ""
    categories = item.get("productCategories") or {}
    if isinstance(categories, dict) and categories:
        vals = [v for v in categories.values() if v]
        if vals:
            category = vals[-1]

    return {
        "id": product_id,
        "product_id": product_id,
        "sku": sku_id,
        "sku_id": sku_id,
        "ref_id": ref_id,
        "nome": name,
        "name": name,
        "categoria": category,
        "category": category,
        "department": "",
        "gender": "",
        "cor": "",
        "colecao": "",
        "estilo": "",
        "imagem_url": image_url,
        "image_url": image_url,
        "link_produto": "#",
        "url": "#",
        "price": item.get("price"),
        "quantity": item.get("quantity", 1),
        "total_spent": (item.get("price", 0) or 0) * (item.get("quantity", 1) or 1),
        "produto_info": item,
    }


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

    return list(aggregated.values())


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