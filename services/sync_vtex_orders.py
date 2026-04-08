import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import requests


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_MODELS_DIR = BASE_DIR / "data_models"

OUTPUT_ORDERS_FILE = DATA_MODELS_DIR / "orders_vtex_24m.json"
OUTPUT_ERRORS_FILE = DATA_MODELS_DIR / "orders_vtex_24m_errors.json"
OUTPUT_META_FILE = DATA_MODELS_DIR / "orders_vtex_24m_meta.json"

VTEX_ACCOUNT = os.getenv("VTEX_ACCOUNT", "").strip()
VTEX_ENV = os.getenv("VTEX_ENV", "vtexcommercestable").strip()
VTEX_APP_KEY = os.getenv("VTEX_APP_KEY", "").strip()
VTEX_APP_TOKEN = os.getenv("VTEX_APP_TOKEN", "").strip()

REQUEST_TIMEOUT = int(os.getenv("VTEX_TIMEOUT", "30"))
REQUEST_SLEEP = float(os.getenv("VTEX_SLEEP", "0.15"))
PER_PAGE = int(os.getenv("VTEX_OMS_PER_PAGE", "50"))
MAX_PAGES = int(os.getenv("VTEX_OMS_MAX_PAGES", "30"))
MONTHS_BACK = int(os.getenv("VTEX_ORDERS_MONTHS_BACK", "24"))
CHUNK_DAYS = int(os.getenv("VTEX_ORDERS_CHUNK_DAYS", "15"))
CHECKPOINT_INTERVAL = int(os.getenv("VTEX_ORDERS_CHECKPOINT_INTERVAL", "100"))

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


def save_checkpoint(
    normalized_orders: list[dict[str, Any]],
    errors: list[dict[str, Any]],
    meta: dict[str, Any],
) -> None:
    save_json(OUTPUT_ORDERS_FILE, normalized_orders)
    save_json(OUTPUT_ERRORS_FILE, errors)
    save_json(OUTPUT_META_FILE, meta)


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
            f"Erro VTEX {response.status_code} em {url}: {response.text[:1000]}"
        )

    if not response.text.strip():
        return None

    return response.json()


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def format_vtex_datetime(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")


def get_date_range_24m() -> tuple[datetime, datetime]:
    end_dt = utc_now()
    start_dt = end_dt - timedelta(days=MONTHS_BACK * 30)
    return start_dt, end_dt


def build_creation_date_filter(start_str: str, end_str: str) -> str:
    return f"creationDate:[{start_str} TO {end_str}]"


def split_date_range(start_dt: datetime, end_dt: datetime, days: int = 15) -> list[tuple[datetime, datetime]]:
    ranges: list[tuple[datetime, datetime]] = []
    current = start_dt

    while current < end_dt:
        chunk_end = min(current + timedelta(days=days), end_dt)
        ranges.append((current, chunk_end))
        current = chunk_end

    return ranges


def safe_str(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def safe_float_from_cents(value: Any) -> float:
    try:
        if value in (None, ""):
            return 0.0
        return round(float(value) / 100.0, 2)
    except Exception:
        return 0.0


def normalize_item(item: dict[str, Any]) -> dict[str, Any]:
    additional_info = item.get("additionalInfo") or {}

    return {
        "sku_id": safe_str(item.get("id")),
        "ref_id": safe_str(item.get("refId")),
        "ean": safe_str(item.get("ean")),
        "product_id": safe_str(item.get("productId")),
        "unique_id": safe_str(item.get("uniqueId")),
        "name": safe_str(item.get("name")),
        "quantity": int(item.get("quantity") or 0),
        "price": safe_float_from_cents(item.get("price")),
        "list_price": safe_float_from_cents(item.get("listPrice")),
        "selling_price": safe_float_from_cents(item.get("sellingPrice")),
        "manual_price": safe_float_from_cents(item.get("manualPrice")),
        "seller": safe_str(item.get("seller")),
        "brand": safe_str(additional_info.get("brandName")),
        "brand_id": safe_str(additional_info.get("brandId")),
        "category_ids": item.get("productCategories") or {},
        "categories": item.get("productCategoryIds") or "",
        "raw": item,
    }


def normalize_payment_data(payment_data: dict[str, Any]) -> list[dict[str, Any]]:
    payments = []

    for payment in (payment_data or {}).get("payments", []) or []:
        if not isinstance(payment, dict):
            continue

        payments.append(
            {
                "payment_system": safe_str(payment.get("paymentSystemName")),
                "group": safe_str(payment.get("group")),
                "value": safe_float_from_cents(payment.get("value")),
                "installments": int(payment.get("installments") or 0),
                "reference_value": safe_float_from_cents(payment.get("referenceValue")),
            }
        )

    return payments


def normalize_totals(totals: list[dict[str, Any]]) -> dict[str, float]:
    result: dict[str, float] = {}

    for total in totals or []:
        if not isinstance(total, dict):
            continue

        total_id = safe_str(total.get("id"))
        if not total_id:
            continue

        result[total_id] = safe_float_from_cents(total.get("value"))

    return result


def normalize_order_detail(order: dict[str, Any]) -> dict[str, Any]:
    client = order.get("clientProfileData") or {}
    shipping = order.get("shippingData") or {}
    address = shipping.get("address") or {}
    store_prefs = order.get("storePreferencesData") or {}

    items = [normalize_item(item) for item in order.get("items", []) or []]

    return {
        "order_id": safe_str(order.get("orderId")),
        "sequence": safe_str(order.get("sequence")),
        "marketplace_order_id": safe_str(order.get("marketplaceOrderId")),
        "creation_date": safe_str(order.get("creationDate")),
        "authorized_date": safe_str(order.get("authorizedDate")),
        "invoiced_date": safe_str(order.get("invoicedDate")),
        "last_change": safe_str(order.get("lastChange")),
        "status": safe_str(order.get("status")),
        "status_description": safe_str(order.get("statusDescription")),
        "origin": safe_str(order.get("origin")),
        "sales_channel": safe_str(order.get("salesChannel")),
        "affiliate_id": safe_str(order.get("affiliateId")),
        "hostname": safe_str(order.get("hostname")),
        "order_group": safe_str(order.get("orderGroup")),
        "value": safe_float_from_cents(order.get("value")),
        "totals": normalize_totals(order.get("totals") or []),
        "currency_code": safe_str(store_prefs.get("currencyCode")),
        "channel": "online",
        "customer": {
            "user_profile_id": safe_str(client.get("userProfileId")),
            "customer_class": safe_str(client.get("customerClass")),
            "email": safe_str(client.get("email")),
            "first_name": safe_str(client.get("firstName")),
            "last_name": safe_str(client.get("lastName")),
            "document": safe_str(client.get("document")),
            "document_type": safe_str(client.get("documentType")),
            "phone": safe_str(client.get("phone")),
            "corporate_name": safe_str(client.get("corporateName")),
            "is_corporate": bool(client.get("isCorporate") or False),
        },
        "shipping": {
            "receiver_name": safe_str(address.get("receiverName")),
            "city": safe_str(address.get("city")),
            "state": safe_str(address.get("state")),
            "country": safe_str(address.get("country")),
            "postal_code": safe_str(address.get("postalCode")),
            "neighborhood": safe_str(address.get("neighborhood")),
        },
        "payments": normalize_payment_data(order.get("paymentData") or {}),
        "items": items,
        "items_count": len(items),
        "raw": order,
    }


def get_orders_page(page: int, start_str: str, end_str: str) -> dict[str, Any]:
    url = f"{BASE_URL}/api/oms/pvt/orders"
    params = {
        "page": page,
        "per_page": PER_PAGE,
        "f_creationDate": build_creation_date_filter(start_str, end_str),
    }

    data = request_json("GET", url, params=params)
    time.sleep(REQUEST_SLEEP)
    return data or {}


def get_order_detail(order_id: str) -> dict[str, Any]:
    url = f"{BASE_URL}/api/oms/pvt/orders/{order_id}"
    data = request_json("GET", url)
    time.sleep(REQUEST_SLEEP)
    return data or {}


def get_all_order_summaries(start_str: str, end_str: str) -> list[dict[str, Any]]:
    all_orders: list[dict[str, Any]] = []

    for page in range(1, MAX_PAGES + 1):
        data = get_orders_page(page, start_str, end_str)
        order_list = data.get("list") or []

        if not order_list:
            break

        all_orders.extend(order_list)
        log(f"  Página {page}: {len(order_list)} pedidos")

        if len(order_list) < PER_PAGE:
            break

    return all_orders


def deduplicate_order_summaries(order_summaries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    deduped: list[dict[str, Any]] = []

    for order in order_summaries:
        order_id = safe_str(order.get("orderId"))
        if not order_id:
            continue

        if order_id in seen:
            continue

        seen.add(order_id)
        deduped.append(order)

    return deduped


def build_meta(
    start_dt: datetime,
    end_dt: datetime,
    all_summaries_count: int,
    deduped_summaries_count: int,
    normalized_orders_count: int,
    errors_count: int,
    last_processed_index: int = 0,
    last_processed_order_id: str = "",
    status: str = "running",
) -> dict[str, Any]:
    return {
        "period_start": format_vtex_datetime(start_dt),
        "period_end": format_vtex_datetime(end_dt),
        "months_back": MONTHS_BACK,
        "chunk_days": CHUNK_DAYS,
        "per_page": PER_PAGE,
        "max_pages": MAX_PAGES,
        "checkpoint_interval": CHECKPOINT_INTERVAL,
        "total_order_summaries_raw": all_summaries_count,
        "total_order_summaries_deduped": deduped_summaries_count,
        "total_orders_normalized": normalized_orders_count,
        "total_errors": errors_count,
        "last_processed_index": last_processed_index,
        "last_processed_order_id": last_processed_order_id,
        "generated_at": format_vtex_datetime(utc_now()),
        "account": VTEX_ACCOUNT,
        "environment": VTEX_ENV,
        "status": status,
    }


def main() -> None:
    ensure_config()

    start_dt, end_dt = get_date_range_24m()
    date_ranges = split_date_range(start_dt, end_dt, days=CHUNK_DAYS)

    log(f"Período total consultado: {format_vtex_datetime(start_dt)} até {format_vtex_datetime(end_dt)}")
    log(f"Quantidade de janelas: {len(date_ranges)}")
    log(f"Tamanho da janela: {CHUNK_DAYS} dias")
    log(f"Checkpoint a cada: {CHECKPOINT_INTERVAL} pedidos")

    all_summaries: list[dict[str, Any]] = []
    chunk_errors: list[dict[str, Any]] = []

    for i, (start_chunk, end_chunk) in enumerate(date_ranges, start=1):
        start_str = format_vtex_datetime(start_chunk)
        end_str = format_vtex_datetime(end_chunk)

        log("")
        log(f"[Chunk {i}/{len(date_ranges)}] Buscando pedidos")
        log(f"Período: {start_str} -> {end_str}")

        try:
            chunk_orders = get_all_order_summaries(start_str, end_str)
            log(f"Pedidos encontrados no chunk: {len(chunk_orders)}")
            all_summaries.extend(chunk_orders)
        except Exception as exc:
            chunk_errors.append(
                {
                    "step": "chunk_fetch",
                    "chunk_index": i,
                    "start": start_str,
                    "end": end_str,
                    "error": str(exc),
                }
            )
            log(f"Erro no chunk {i}: {exc}")

    deduped_summaries = deduplicate_order_summaries(all_summaries)

    log("")
    log(f"Total bruto de pedidos: {len(all_summaries)}")
    log(f"Total deduplicado de pedidos: {len(deduped_summaries)}")

    normalized_orders: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = list(chunk_errors)

    try:
        for idx, summary in enumerate(deduped_summaries, start=1):
            order_id = safe_str(summary.get("orderId"))

            if not order_id:
                errors.append(
                    {
                        "step": "summary_without_order_id",
                        "summary": summary,
                        "error": "Resumo sem orderId",
                    }
                )
                continue

            log(f"[{idx}/{len(deduped_summaries)}] Detalhando pedido {order_id}")

            try:
                detail = get_order_detail(order_id)
                normalized = normalize_order_detail(detail)
                normalized_orders.append(normalized)
            except Exception as exc:
                errors.append(
                    {
                        "step": "detail_fetch",
                        "order_id": order_id,
                        "error": str(exc),
                        "summary": summary,
                    }
                )

            if idx % CHECKPOINT_INTERVAL == 0:
                meta = build_meta(
                    start_dt=start_dt,
                    end_dt=end_dt,
                    all_summaries_count=len(all_summaries),
                    deduped_summaries_count=len(deduped_summaries),
                    normalized_orders_count=len(normalized_orders),
                    errors_count=len(errors),
                    last_processed_index=idx,
                    last_processed_order_id=order_id,
                    status="checkpoint",
                )
                save_checkpoint(normalized_orders, errors, meta)
                log(f"💾 Checkpoint salvo em {idx} pedidos")

    except KeyboardInterrupt:
        meta = build_meta(
            start_dt=start_dt,
            end_dt=end_dt,
            all_summaries_count=len(all_summaries),
            deduped_summaries_count=len(deduped_summaries),
            normalized_orders_count=len(normalized_orders),
            errors_count=len(errors),
            last_processed_index=len(normalized_orders),
            last_processed_order_id=safe_str(normalized_orders[-1].get("order_id")) if normalized_orders else "",
            status="interrupted",
        )
        save_checkpoint(normalized_orders, errors, meta)
        log("")
        log("⚠️ Processo interrompido pelo usuário.")
        log("💾 Último checkpoint salvo antes de sair.")
        sys.exit(1)

    meta = build_meta(
        start_dt=start_dt,
        end_dt=end_dt,
        all_summaries_count=len(all_summaries),
        deduped_summaries_count=len(deduped_summaries),
        normalized_orders_count=len(normalized_orders),
        errors_count=len(errors),
        last_processed_index=len(deduped_summaries),
        last_processed_order_id=safe_str(normalized_orders[-1].get("order_id")) if normalized_orders else "",
        status="completed",
    )

    save_checkpoint(normalized_orders, errors, meta)

    log("")
    log("Processo concluído.")
    log(f"Arquivo de pedidos: {OUTPUT_ORDERS_FILE}")
    log(f"Arquivo de erros: {OUTPUT_ERRORS_FILE}")
    log(f"Arquivo meta: {OUTPUT_META_FILE}")
    log(f"Pedidos normalizados: {len(normalized_orders)}")
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