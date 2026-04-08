import json
import os
import sys
import time
from pathlib import Path
from typing import Any

import requests


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_MODELS_DIR = BASE_DIR / "data_models"

OUTPUT_CLIENTES_FILE = DATA_MODELS_DIR / "clientes.json"
OUTPUT_PEDIDOS_FILE = DATA_MODELS_DIR / "pedidos.json"
OUTPUT_ERRORS_FILE = DATA_MODELS_DIR / "vtex_fetch_errors.json"

VTEX_ACCOUNT = os.getenv("VTEX_ACCOUNT", "").strip()
VTEX_ENV = os.getenv("VTEX_ENV", "vtexcommercestable").strip()
VTEX_APP_KEY = os.getenv("VTEX_APP_KEY", "").strip()
VTEX_APP_TOKEN = os.getenv("VTEX_APP_TOKEN", "").strip()

REQUEST_TIMEOUT = int(os.getenv("VTEX_TIMEOUT", "30"))
REQUEST_SLEEP = float(os.getenv("VTEX_SLEEP", "0.2"))
ORDERS_PAGE_SIZE = int(os.getenv("VTEX_ORDERS_PAGE_SIZE", "100"))
MAX_ORDER_PAGES = int(os.getenv("VTEX_MAX_ORDER_PAGES", "200"))
MAX_CLIENT_PAGES = int(os.getenv("VTEX_MAX_CLIENT_PAGES", "200"))

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


def normalize_email(email: Any) -> str:
    return str(email or "").strip().lower()


def fetch_clients() -> list[dict[str, Any]]:
    clients: list[dict[str, Any]] = []

    for page in range(1, MAX_CLIENT_PAGES + 1):
        url = (
            f"{BASE_URL}/api/dataentities/CL/search"
            f"?_fields=id,email,firstName,lastName,homePhone,phone,birthDate"
            f"&_where=email is not null"
            f"&_page={page}&_size=100"
        )

        data = request_json("GET", url)
        time.sleep(REQUEST_SLEEP)

        if not isinstance(data, list) or not data:
            break

        for row in data:
            if not isinstance(row, dict):
                continue

            email = normalize_email(row.get("email"))
            if not email:
                continue

            clients.append(
                {
                    "id": row.get("id"),
                    "nome": f"{row.get('firstName', '')} {row.get('lastName', '')}".strip() or email.split("@")[0],
                    "email": email,
                    "phone": row.get("phone") or row.get("homePhone") or "",
                    "birthDate": row.get("birthDate") or "",
                }
            )

        log(f"Clientes - página {page}: {len(data)} registros")

        if len(data) < 100:
            break

    dedup: dict[str, dict[str, Any]] = {}
    for client in clients:
        email = client.get("email")
        if email and email not in dedup:
            dedup[email] = client

    return list(dedup.values())


def fetch_order_detail(order_id: str) -> dict[str, Any]:
    url = f"{BASE_URL}/api/oms/pvt/orders/{order_id}"
    data = request_json("GET", url)
    time.sleep(REQUEST_SLEEP)
    return data or {}


def normalize_order_item(item: dict[str, Any]) -> dict[str, Any]:
    sku_id = item.get("id") or item.get("skuId") or item.get("refId")
    product_id = item.get("productId")
    quantity = item.get("quantity") or 1

    selling_price = item.get("sellingPrice") or item.get("price") or 0
    try:
        unit_price = float(selling_price) / 100 if float(selling_price) > 1000 else float(selling_price)
    except Exception:
        unit_price = 0.0

    return {
        "sku_id": str(sku_id or "").strip(),
        "product_id": str(product_id or "").strip(),
        "ref_id": item.get("refId"),
        "name": item.get("name") or "",
        "quantity": quantity,
        "price": unit_price,
        "detailUrl": item.get("detailUrl") or item.get("detailUrl") or "#",
        "imageUrl": item.get("imageUrl") or "",
    }


def fetch_orders() -> list[dict[str, Any]]:
    orders: list[dict[str, Any]] = []

    for page in range(1, MAX_ORDER_PAGES + 1):
        url = (
            f"{BASE_URL}/api/oms/pvt/orders"
            f"?page={page}&per_page={ORDERS_PAGE_SIZE}"
        )

        payload = request_json("GET", url)
        time.sleep(REQUEST_SLEEP)

        list_data = payload.get("list") if isinstance(payload, dict) else None
        if not isinstance(list_data, list) or not list_data:
            break

        log(f"Pedidos - página {page}: {len(list_data)} pedidos")

        for order_row in list_data:
            try:
                order_id = order_row.get("orderId")
                if not order_id:
                    continue

                detail = fetch_order_detail(order_id)
                client_profile = detail.get("clientProfileData") or {}
                items = detail.get("items") or []

                normalized_items = [normalize_order_item(item) for item in items if isinstance(item, dict)]

                orders.append(
                    {
                        "orderId": order_id,
                        "sequence": detail.get("sequence"),
                        "creationDate": detail.get("creationDate"),
                        "status": detail.get("status"),
                        "email": normalize_email(client_profile.get("email")),
                        "firstName": client_profile.get("firstName") or "",
                        "lastName": client_profile.get("lastName") or "",
                        "items": normalized_items,
                        "total_value": detail.get("value"),
                    }
                )
            except Exception as exc:
                log(f"Erro ao detalhar pedido: {exc}")

        if len(list_data) < ORDERS_PAGE_SIZE:
            break

    return orders


def main() -> None:
    ensure_config()

    errors: list[str] = []

    log("Buscando clientes VTEX...")
    try:
        clientes = fetch_clients()
    except Exception as exc:
        clientes = []
        errors.append(f"Erro clientes: {exc}")

    log("Buscando pedidos VTEX...")
    try:
        pedidos = fetch_orders()
    except Exception as exc:
        pedidos = []
        errors.append(f"Erro pedidos: {exc}")

    save_json(OUTPUT_CLIENTES_FILE, clientes)
    save_json(OUTPUT_PEDIDOS_FILE, pedidos)
    save_json(OUTPUT_ERRORS_FILE, errors)

    log("")
    log("Processo concluído.")
    log(f"Clientes salvos: {len(clientes)}")
    log(f"Pedidos salvos: {len(pedidos)}")
    log(f"Arquivo clientes: {OUTPUT_CLIENTES_FILE}")
    log(f"Arquivo pedidos: {OUTPUT_PEDIDOS_FILE}")
    log(f"Erros: {len(errors)}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log("Processo interrompido pelo usuário.")
        sys.exit(1)
    except Exception as exc:
        log(f"Erro fatal: {exc}")
        sys.exit(1)