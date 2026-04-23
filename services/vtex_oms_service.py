import os
from datetime import datetime, timezone
from typing import Any

import requests


def normalize_text(value: Any) -> str:
    return str(value or "").strip().lower()


def normalize_email(email: str) -> str:
    """
    Normaliza e valida o e-mail do cliente.
    
    Rejeita e-mails técnicos gerados pela VTEX para pedidos
    B2B, integrações ou operações internas. Esses e-mails
    seguem o padrão hash@ct.vtex.com.br ou similares e
    não correspondem a clientes reais.
    """
    if not email:
        return ""

    email = str(email).strip().lower()

    # Rejeita e-mails técnicos da VTEX
    dominios_tecnicos = [
        "@ct.vtex.com.br",
        "@act.vtex.com.br",
        "@vtex.com.br",
        "@marketplace.vtex.com.br",
        "@vtexcommercestable.com.br",
    ]
    for dominio in dominios_tecnicos:
        if email.endswith(dominio):
            return ""

    # Rejeita strings que não têm formato de e-mail válido
    if "@" not in email:
        return ""

    parts = email.split("@")
    if len(parts) != 2:
        return ""

    domain = parts[1]
    if "." not in domain:
        return ""

    # Rejeita e-mails muito curtos (hashes truncados)
    local = parts[0]
    if len(local) < 2:
        return ""

    return email


def to_str(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def parse_iso_datetime(value: str | None) -> datetime | None:
    if not value:
        return None

    raw = str(value).strip()
    if raw.endswith("Z"):
        raw = raw.replace("Z", "+00:00")

    try:
        dt = datetime.fromisoformat(raw)
        if dt.tzinfo is not None:
            dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
        return dt
    except Exception:
        return None


def format_vtex_datetime(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    return dt.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def cents_to_float(value: Any) -> float:
    try:
        return float(value or 0) / 100.0
    except Exception:
        return 0.0


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


def fetch_order_summaries_by_creation_date(
    start_dt: datetime,
    end_dt: datetime,
    page: int = 1,
    per_page: int = 100,
) -> dict[str, Any]:
    account, app_key, app_token = get_vtex_credentials()
    headers = get_headers(app_key, app_token)

    url = f"https://{account}.vtexcommercestable.com.br/api/oms/pvt/orders"
    params = {
        "f_creationDate": f"creationDate:[{format_vtex_datetime(start_dt)} TO {format_vtex_datetime(end_dt)}]",
        "page": page,
        "per_page": per_page,
    }

    response = requests.get(url, headers=headers, params=params, timeout=60)
    response.raise_for_status()
    return response.json() or {}


def fetch_order_detail(order_id: str) -> dict[str, Any]:
    account, app_key, app_token = get_vtex_credentials()
    headers = get_headers(app_key, app_token)

    url = f"https://{account}.vtexcommercestable.com.br/api/oms/pvt/orders/{order_id}"
    response = requests.get(url, headers=headers, timeout=60)
    response.raise_for_status()
    return response.json() or {}