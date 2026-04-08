import json
import os
import sys
import time
from pathlib import Path
from typing import Any

import requests


# como o arquivo está em /services, a raiz do projeto é o parent do parent
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_MODELS_DIR = BASE_DIR / "data_models"

OUTPUT_ENRICHED_FILE = DATA_MODELS_DIR / "products_enriched.json"
OUTPUT_ERRORS_FILE = DATA_MODELS_DIR / "products_enriched_errors.json"

VTEX_ACCOUNT = os.getenv("VTEX_ACCOUNT", "").strip()
VTEX_ENV = os.getenv("VTEX_ENV", "vtexcommercestable").strip()
VTEX_APP_KEY = os.getenv("VTEX_APP_KEY", "").strip()
VTEX_APP_TOKEN = os.getenv("VTEX_APP_TOKEN", "").strip()

REQUEST_TIMEOUT = int(os.getenv("VTEX_TIMEOUT", "30"))
REQUEST_SLEEP = float(os.getenv("VTEX_SLEEP", "0.15"))
PAGE_SIZE = int(os.getenv("VTEX_PAGE_SIZE", "50"))
MAX_PAGES = int(os.getenv("VTEX_MAX_PAGES", "200"))

BASE_URL = f"https://{VTEX_ACCOUNT}.{VTEX_ENV}.com.br" if VTEX_ACCOUNT else ""

HEADERS = {
    "Accept": "application/json",
    "Content-Type": "application/json",
    "X-VTEX-API-AppKey": VTEX_APP_KEY,
    "X-VTEX-API-AppToken": VTEX_APP_TOKEN,
}


def log(message: str) -> None:
    print(message, flush=True)


def ensure_config() -> None:
    missing = []
    if not VTEX_ACCOUNT:
        missing.append("VTEX_ACCOUNT")
    if not VTEX_APP_KEY:
        missing.append("VTEX_APP_KEY")
    if not VTEX_APP_TOKEN:
        missing.append("VTEX_APP_TOKEN")

    if missing:
        raise RuntimeError("Variáveis de ambiente ausentes: " + ", ".join(missing))


def save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def request_json(method: str, url: str, **kwargs) -> Any:
    response = requests.request(
        method,
        url,
        headers=HEADERS,
        timeout=REQUEST_TIMEOUT,
        **kwargs,
    )

    if response.status_code >= 400:
        raise RuntimeError(
            f"Erro VTEX {response.status_code} em {url}: {response.text[:500]}"
        )

    if not response.text.strip():
        return None

    return response.json()


def normalize_images(images: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized = []

    for image in images or []:
        if not isinstance(image, dict):
            continue

        normalized.append(
            {
                "ImageUrl": image.get("Url")
                or image.get("ImageUrl")
                or image.get("Archive")
                or "",
                "ImageName": image.get("Name")
                or image.get("ImageName")
                or "",
                "FileId": image.get("Id") or image.get("FileId"),
            }
        )

    return normalized


def normalize_spec_list(specs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized = []

    for spec in specs or []:
        if not isinstance(spec, dict):
            continue

        name = (
            spec.get("Name")
            or spec.get("name")
            or spec.get("FieldName")
            or spec.get("OriginalName")
            or ""
        )

        value = (
            spec.get("Value")
            or spec.get("value")
            or spec.get("Text")
            or spec.get("Values")
            or spec.get("values")
            or ""
        )

        values = (
            value
            if isinstance(value, list)
            else ([value] if value not in [None, ""] else [])
        )

        normalized.append(
            {
                "name": name,
                "field_id": spec.get("FieldId") or spec.get("fieldId"),
                "field_value_id": spec.get("FieldValueId") or spec.get("fieldValueId"),
                "value": values,
                "raw": spec,
            }
        )

    return normalized


def build_spec_map(
    product_specs: list[dict[str, Any]],
    sku_specs: list[dict[str, Any]],
) -> dict[str, list[str]]:
    spec_map: dict[str, list[str]] = {}

    for spec in (product_specs or []) + (sku_specs or []):
        name = str(spec.get("name") or "").strip()
        if not name:
            continue

        values = spec.get("value") or []
        if not isinstance(values, list):
            values = [values]

        clean_values = []
        for value in values:
            text = str(value or "").strip()
            if text and text not in clean_values:
                clean_values.append(text)

        if name not in spec_map:
            spec_map[name] = []

        for value in clean_values:
            if value not in spec_map[name]:
                spec_map[name].append(value)

    return spec_map


def get_all_products() -> list[dict[str, Any]]:
    """
    Busca a base geral da VTEX.

    Suporta resposta no formato:
    {
      "data": {
        "123": [111, 112],
        "456": [221]
      },
      "range": {
        ...
      }
    }

    E também no formato direto:
    {
      "123": [111, 112],
      "456": [221]
    }
    """
    all_products: list[dict[str, Any]] = []

    for page in range(1, MAX_PAGES + 1):
        from_idx = (page - 1) * PAGE_SIZE + 1
        to_idx = page * PAGE_SIZE

        url = (
            f"{BASE_URL}/api/catalog_system/pvt/products/"
            f"GetProductAndSkuIds?_from={from_idx}&_to={to_idx}"
        )

        response_data = request_json("GET", url)
        time.sleep(REQUEST_SLEEP)

        if not response_data:
            break

        product_map = None

        if isinstance(response_data, dict):
            if "data" in response_data and isinstance(response_data["data"], dict):
                product_map = response_data["data"]
            elif all(isinstance(v, list) for v in response_data.values()):
                product_map = response_data

        if not product_map:
            log(f"Resposta inesperada na página {page}: {type(response_data)}")
            log(f"Conteúdo recebido: {str(response_data)[:500]}")
            break

        page_products = []
        for product_id, sku_ids in product_map.items():
            page_products.append(
                {
                    "product_id": str(product_id).strip(),
                    "sku_ids": sku_ids if isinstance(sku_ids, list) else [],
                }
            )

        if not page_products:
            break

        all_products.extend(page_products)
        log(f"Página {page}: {len(page_products)} produtos")

        if len(page_products) < PAGE_SIZE:
            break

    return all_products


def get_product_by_id(product_id: int | str) -> dict[str, Any]:
    url = f"{BASE_URL}/api/catalog/pvt/product/{product_id}"
    data = request_json("GET", url)
    time.sleep(REQUEST_SLEEP)
    return data or {}


def get_product_specifications(product_id: int | str) -> list[dict[str, Any]]:
    url = f"{BASE_URL}/api/catalog/pvt/product/{product_id}/specification"
    try:
        data = request_json("GET", url)
        time.sleep(REQUEST_SLEEP)
        return data if isinstance(data, list) else []
    except Exception:
        return []


def get_sku_by_id(sku_id: int | str) -> dict[str, Any]:
    url = f"{BASE_URL}/api/catalog/pvt/stockkeepingunit/{sku_id}"
    data = request_json("GET", url)
    time.sleep(REQUEST_SLEEP)
    return data or {}


def get_sku_specifications(sku_id: int | str) -> list[dict[str, Any]]:
    url = f"{BASE_URL}/api/catalog/pvt/stockkeepingunit/{sku_id}/specification"
    try:
        data = request_json("GET", url)
        time.sleep(REQUEST_SLEEP)
        return data if isinstance(data, list) else []
    except Exception:
        return []


def get_sku_images(sku_id: int | str) -> list[dict[str, Any]]:
    url = f"{BASE_URL}/api/catalog/pvt/stockkeepingunit/{sku_id}/file"
    try:
        data = request_json("GET", url)
        time.sleep(REQUEST_SLEEP)
        return data if isinstance(data, list) else []
    except Exception:
        return []


def enrich_one_product(base_product: dict[str, Any]) -> dict[str, Any]:
    product_id = base_product.get("product_id")
    sku_ids = base_product.get("sku_ids") or []

    product_data = get_product_by_id(product_id)
    product_specs = normalize_spec_list(get_product_specifications(product_id))

    sku_details = []
    all_sku_specs = []

    for sku_id in sku_ids:
        sku_data = get_sku_by_id(sku_id)
        sku_specs = normalize_spec_list(get_sku_specifications(sku_id))
        sku_images = normalize_images(get_sku_images(sku_id))

        all_sku_specs.extend(sku_specs)

        sku_details.append(
            {
                "sku_id": sku_data.get("Id") or sku_id,
                "product_id": sku_data.get("ProductId") or product_id,
                "name": sku_data.get("NameComplete") or sku_data.get("Name") or "",
                "ref_id": sku_data.get("RefId"),
                "images": sku_images,
                "sku_specifications": sku_specs,
                "raw_sku": sku_data,
            }
        )

    spec_map = build_spec_map(product_specs, all_sku_specs)

    return {
        "product_id": product_data.get("Id") or product_id,
        "product_name": product_data.get("Name") or "",
        "description": product_data.get("Description") or "",
        "brand_id": product_data.get("BrandId"),
        "brand_name": product_data.get("BrandName") or "",
        "category_id": product_data.get("CategoryId"),
        "category_name": product_data.get("CategoryName") or "",
        "ref_id": product_data.get("RefId"),
        "link_id": product_data.get("LinkId"),
        "product_specifications": product_specs,
        "specifications": spec_map,
        "sku_ids": [sku.get("sku_id") for sku in sku_details],
        "sku_details": sku_details,
        "raw_product": product_data,
    }


def main() -> None:
    ensure_config()

    log("Buscando base geral da VTEX...")
    base_products = get_all_products()

    log(f"Total base VTEX: {len(base_products)} produtos")
    if base_products:
        log(f"Primeiro produto da base: {base_products[0]}")

    enriched_products: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []

    for idx, product in enumerate(base_products, start=1):
        product_id = product.get("product_id")
        log(f"[{idx}/{len(base_products)}] Enriquecendo product_id={product_id}")

        try:
            enriched = enrich_one_product(product)
            enriched_products.append(enriched)
        except Exception as exc:
            errors.append(
                {
                    "product_id": product_id,
                    "error": str(exc),
                    "raw": product,
                }
            )

    save_json(OUTPUT_ENRICHED_FILE, enriched_products)
    save_json(OUTPUT_ERRORS_FILE, errors)

    log("")
    log("Processo concluído.")
    log(f"Arquivo gerado: {OUTPUT_ENRICHED_FILE}")
    log(f"Erros: {len(errors)}")
    log(f"Produtos enriquecidos: {len(enriched_products)}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log("Processo interrompido pelo usuário.")
        sys.exit(1)
    except Exception as exc:
        log(f"Erro fatal: {exc}")
        sys.exit(1)