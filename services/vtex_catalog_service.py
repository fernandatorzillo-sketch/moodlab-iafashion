import os
import unicodedata
from typing import Any

import requests


def normalize_text(value: Any) -> str:
    value = str(value or "").strip().lower()
    value = unicodedata.normalize("NFD", value)
    return "".join(ch for ch in value if unicodedata.category(ch) != "Mn")


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


def vtex_get(path: str, params: dict | None = None, timeout: int = 60):
    account, app_key, app_token = get_vtex_credentials()
    url = f"https://{account}.vtexcommercestable.com.br{path}"

    response = requests.get(
        url,
        headers=get_headers(app_key, app_token),
        params=params or {},
        timeout=timeout,
    )
    response.raise_for_status()
    return response.json() or {}


def fetch_product_and_sku_ids(page_from: int, page_to: int) -> dict[str, Any]:
    return vtex_get(
        "/api/catalog_system/pvt/products/GetProductAndSkuIds",
        params={"_from": page_from, "_to": page_to},
        timeout=60,
    )


def fetch_product_by_id(product_id: str) -> dict[str, Any]:
    return vtex_get(
        f"/api/catalog_system/pvt/products/ProductGet/{product_id}",
        timeout=60,
    )


def fetch_sku_by_id(sku_id: str) -> dict[str, Any]:
    return vtex_get(
        f"/api/catalog_system/pvt/sku/stockkeepingunitbyid/{sku_id}",
        timeout=60,
    )


def extract_category_from_sku(sku_data: dict) -> tuple[str | None, str | None]:
    categories = sku_data.get("ProductCategories") or {}

    if isinstance(categories, dict) and categories:
        ordered = sorted(categories.items(), key=lambda x: int(x[0]) if str(x[0]).isdigit() else 999999)
        names = [str(name).strip() for _, name in ordered if str(name).strip()]

        if len(names) >= 2:
            return names[0], names[-1]

        if len(names) == 1:
            return names[0], names[0]

    return None, None


def extract_spec_from_product(product_data: dict, keys: list[str]) -> str | None:
    wanted = {normalize_text(k) for k in keys}

    groups = product_data.get("SpecificationGroups") or []
    for group in groups:
        for field in group.get("Specifications", []) or []:
            name = normalize_text(field.get("Name"))
            if name in wanted:
                values = field.get("Values") or []
                if values:
                    return str(values[0]).strip()

    return None


def extract_spec_from_sku(sku_data: dict, keys: list[str]) -> str | None:
    wanted = {normalize_text(k) for k in keys}

    possible_lists = [
        sku_data.get("SkuSpecifications"),
        sku_data.get("Specifications"),
        sku_data.get("ProductSpecifications"),
    ]

    for specs in possible_lists:
        if not specs:
            continue

        for field in specs:
            name = normalize_text(
                field.get("FieldName")
                or field.get("Name")
                or field.get("name")
            )

            if name in wanted:
                values = (
                    field.get("FieldValues")
                    or field.get("Values")
                    or field.get("values")
                    or []
                )

                if isinstance(values, list) and values:
                    first = values[0]
                    if isinstance(first, dict):
                        return str(
                            first.get("Value")
                            or first.get("Name")
                            or first.get("value")
                            or ""
                        ).strip()
                    return str(first).strip()

                value = field.get("Value") or field.get("value")
                if value:
                    return str(value).strip()

    return None


def get_first_image_url(sku_data: dict) -> str | None:
    direct = sku_data.get("ImageUrl") or sku_data.get("imageUrl")
    if direct:
        return str(direct).strip()

    images = sku_data.get("Images") or sku_data.get("images") or []
    if images and isinstance(images, list):
        first = images[0]
        if isinstance(first, dict):
            return str(
                first.get("ImageUrl")
                or first.get("imageUrl")
                or first.get("Url")
                or first.get("url")
                or ""
            ).strip() or None

    return None


def get_product_url(product_data: dict, sku_data: dict | None = None) -> str | None:
    url = (
        product_data.get("DetailUrl")
        or product_data.get("Link")
        or product_data.get("link")
        or product_data.get("productUrl")
    )

    if not url and sku_data:
        url = sku_data.get("DetailUrl") or sku_data.get("Link") or sku_data.get("link")

    if not url:
        return None

    return str(url).strip()


def enrich_product_fields(product_data: dict, sku_data: dict | None = None) -> dict:
    sku_data = sku_data or {}

    department, category = extract_category_from_sku(sku_data)

    department = (
        product_data.get("DepartmentName")
        or product_data.get("departmentName")
        or department
    )

    category = (
        product_data.get("CategoryName")
        or product_data.get("categoryName")
        or category
    )

    return {
        "name": product_data.get("Name") or product_data.get("name"),
        "brand": product_data.get("BrandName") or product_data.get("brandName"),
        "department": department,
        "category": category,
        "product_type": (
            extract_spec_from_product(product_data, ["0- Tipo de produto", "Tipo de produto", "tipo"])
            or extract_spec_from_sku(sku_data, ["0- Tipo de produto", "Tipo de produto", "tipo"])
        ),
        "occasion": (
            extract_spec_from_product(product_data, ["0- Ocasião", "Ocasião", "ocasiao"])
            or extract_spec_from_sku(sku_data, ["0- Ocasião", "Ocasião", "ocasiao"])
        ),
        "print_name": (
            extract_spec_from_product(product_data, ["0- Estamparia", "Estamparia"])
            or extract_spec_from_sku(sku_data, ["0- Estamparia", "Estamparia"])
        ),
        "collection": (
            extract_spec_from_product(product_data, ["0- Coleção", "Coleção", "colecao"])
            or extract_spec_from_sku(sku_data, ["0- Coleção", "Coleção", "colecao"])
        ),
        "color": (
            extract_spec_from_product(product_data, ["Cores", "Cor", "cores"])
            or extract_spec_from_sku(sku_data, ["Cores", "Cor", "cores"])
        ),
        "size": (
            extract_spec_from_product(product_data, ["Tamanho", "tamanho"])
            or extract_spec_from_sku(sku_data, ["Tamanho", "tamanho"])
        ),
        "gender": (
            extract_spec_from_product(product_data, ["Gênero", "Genero"])
            or extract_spec_from_sku(sku_data, ["Gênero", "Genero"])
        ),
        "image_url": get_first_image_url(sku_data),
        "product_url": get_product_url(product_data, sku_data),
    }