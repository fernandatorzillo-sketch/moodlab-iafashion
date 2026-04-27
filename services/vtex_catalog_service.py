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


# IDs das categorias de MODA da Água de Coco no VTEX.
# Exclui "Casa", "Lifestyle" e outras categorias não-moda.
# Para obter os IDs: /api/catalog_system/pub/category/tree/10
# Deixe vazio ([]) para sincronizar TODOS os produtos (não recomendado).
FASHION_CATEGORY_IDS: list[int] = []  # preenchido automaticamente ou via env


def fetch_category_tree(account: str, app_key: str, app_token: str) -> list[dict]:
    """Busca a árvore de categorias da VTEX para identificar categorias de moda."""
    url = f"https://{account}.vtexcommercestable.com.br/api/catalog_system/pub/category/tree/3"
    try:
        response = requests.get(url, headers=get_headers(app_key, app_token), timeout=30)
        response.raise_for_status()
        return response.json() or []
    except Exception:
        return []


def get_fashion_category_ids() -> list[int]:
    """
    Retorna IDs das categorias de moda da Água de Coco.
    Usa variável de ambiente VTEX_FASHION_CATEGORY_IDS (CSV) se disponível,
    caso contrário descobre automaticamente pela árvore de categorias.
    """
    from_env = os.getenv("VTEX_FASHION_CATEGORY_IDS", "").strip()
    if from_env:
        try:
            return [int(x.strip()) for x in from_env.split(",") if x.strip()]
        except ValueError:
            pass

    # Descobre automaticamente: exclui departamentos não-moda por nome
    NON_FASHION = {"casa", "lifestyle", "decor", "decoracao", "decoração",
                   "utilidades", "cozinha", "banheiro", "quarto", "sala"}
    try:
        account, app_key, app_token = get_vtex_credentials()
        tree = fetch_category_tree(account, app_key, app_token)
        ids = []
        for dept in tree:
            dept_name = str(dept.get("Name") or "").strip().lower()
            dept_name_norm = dept_name.replace("ã","a").replace("ç","c").replace("é","e").replace("ó","o")
            if dept_name_norm in NON_FASHION:
                print(f"  [catalog] Ignorando departamento não-moda: '{dept.get('Name')}' (id={dept.get('id')})")
                continue
            dept_id = dept.get("id") or dept.get("Id")
            if dept_id:
                ids.append(int(dept_id))
                print(f"  [catalog] Incluindo departamento: '{dept.get('Name')}' (id={dept_id})")
        return ids
    except Exception as e:
        print(f"  [catalog] Erro ao descobrir categorias: {e} — sincronizando tudo")
        return []


def fetch_product_and_sku_ids(page_from: int, page_to: int, category_id: int | None = None) -> dict[str, Any]:
    account, app_key, app_token = get_vtex_credentials()
    headers = get_headers(app_key, app_token)

    url = f"https://{account}.vtexcommercestable.com.br/api/catalog_system/pvt/products/GetProductAndSkuIds"
    params: dict = {"_from": page_from, "_to": page_to}
    if category_id:
        params["categoryId"] = category_id

    response = requests.get(url, headers=headers, params=params, timeout=60)
    response.raise_for_status()
    return response.json() or {}


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
    return response.json() or {}