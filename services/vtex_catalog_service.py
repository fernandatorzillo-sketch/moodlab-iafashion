import os
from typing import Any

import requests


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


def fetch_product_and_sku_ids(page_from: int, page_to: int) -> dict[str, Any]:
    account, app_key, app_token = get_vtex_credentials()
    headers = get_headers(app_key, app_token)

    url = f"https://{account}.vtexcommercestable.com.br/api/catalog_system/pvt/products/GetProductAndSkuIds"
    params = {"_from": page_from, "_to": page_to}

    response = requests.get(url, headers=headers, params=params, timeout=60)
    response.raise_for_status()
    return response.json() or {}


def fetch_category_tree(account: str, app_key: str, app_token: str) -> list[dict]:
    """Busca a árvore de categorias da VTEX."""
    url = f"https://{account}.vtexcommercestable.com.br/api/catalog_system/pub/category/tree/3"
    try:
        response = requests.get(url, headers=get_headers(app_key, app_token), timeout=30)
        response.raise_for_status()
        return response.json() or []
    except Exception as e:
        print(f"  [catalog] Erro ao buscar category tree: {e}")
        return []


def fetch_category_map() -> dict[int, dict]:
    """
    Constrói mapa {category_id: {name, department_name}} a partir da árvore VTEX.
    Usado no sync para enriquecer produtos com DepartmentName/CategoryName
    já que ProductGet retorna apenas os IDs numéricos.
    """
    try:
        account, app_key, app_token = get_vtex_credentials()
        tree = fetch_category_tree(account, app_key, app_token)
        result: dict[int, dict] = {}

        def get_name(node: dict) -> str:
            # API pública usa "name", API privada usa "Name"
            return str(
                node.get("name") or node.get("Name") or
                node.get("nome") or node.get("title") or ""
            ).strip()

        def get_id(node: dict) -> int:
            return int(node.get("id") or node.get("Id") or 0)

        for dept in tree:
            dept_id   = get_id(dept)
            dept_name = get_name(dept)
            if dept_id:
                result[dept_id] = {"name": dept_name, "department_name": dept_name}
            for cat in dept.get("children") or dept.get("Children") or []:
                cat_id   = get_id(cat)
                cat_name = get_name(cat)
                if cat_id:
                    result[cat_id] = {"name": cat_name, "department_name": dept_name}
                for subcat in cat.get("children") or cat.get("Children") or []:
                    sub_id   = get_id(subcat)
                    sub_name = get_name(subcat)
                    if sub_id:
                        result[sub_id] = {"name": sub_name, "department_name": dept_name}

        if result:
            return result

        # Fallback: se a árvore não retornou nomes, usa map hardcoded dos IDs conhecidos.
        # Os nomes corretos virão do campo "Departamento" nas specs do produto.
        print("  [catalog] category tree sem nomes — usando IDs hardcoded como fallback")
        for cat_id in [2, 3, 4, 5, 6, 7, 47, 48]:
            result[cat_id] = {"name": "", "department_name": ""}
        return result
    except Exception as e:
        print(f"  [catalog] Erro ao construir category_map: {e}")
        return {}


def fetch_product_by_id(product_id: str) -> dict[str, Any]:
    account, app_key, app_token = get_vtex_credentials()
    headers = get_headers(app_key, app_token)

    url = f"https://{account}.vtexcommercestable.com.br/api/catalog_system/pvt/products/ProductGet/{product_id}"
    response = requests.get(url, headers=headers, timeout=60)
    response.raise_for_status()
    return response.json() or {}


def fetch_sku_by_id(sku_id: str) -> dict[str, Any]:
    account, app_key, app_token = get_vtex_credentials()
    headers = get_headers(app_key, app_token)

    url = f"https://{account}.vtexcommercestable.com.br/api/catalog_system/pvt/sku/stockkeepingunitbyid/{sku_id}"
    response = requests.get(url, headers=headers, timeout=60)
    response.raise_for_status()
    data = response.json() or {}

    # lojaaguadecoco.vteximg.com.br é o domínio correto da Água de Coco na VTEX.
    # Não alterar a URL retornada pela API.
    return data