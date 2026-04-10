import json
import traceback
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from services.customer_closet_service import get_customer_closet
from services.recommendation_engine import build_recommendations

router = APIRouter(prefix="/api/v1/customer-closet", tags=["customer-closet"])

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_MODELS_DIR = BASE_DIR / "data_models"


class LookupRequest(BaseModel):
    email: str


class RecommendationRequest(BaseModel):
    email: str
    answers: dict[str, Any] = {}
    context: dict[str, Any] = {}
    limit: int = 8


def load_json(filename: str):
    filepath = DATA_MODELS_DIR / filename
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def normalize_text(value: Any) -> str:
    text = str(value or "").strip().lower()
    replacements = {
        "á": "a",
        "à": "a",
        "ã": "a",
        "â": "a",
        "é": "e",
        "ê": "e",
        "í": "i",
        "ó": "o",
        "ô": "o",
        "õ": "o",
        "ú": "u",
        "ç": "c",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return " ".join(text.split())


def normalize_email(email: str) -> str:
    return normalize_text(email)


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


def find_cliente_by_email(clientes: list[Any], email_normalized: str):
    for c in clientes:
        if isinstance(c, dict):
            email_cliente = normalize_email(c.get("email", ""))
            if email_cliente == email_normalized:
                return {
                    "nome": c.get("nome", email_normalized.split("@")[0]),
                    "email": email_cliente,
                    "estilo_resumo": c.get("estilo_resumo", ""),
                    "tamanho_top": c.get("tamanho_top", ""),
                    "tamanho_bottom": c.get("tamanho_bottom", ""),
                    "tamanho_dress": c.get("tamanho_dress", ""),
                    "cidade": c.get("cidade", ""),
                }

        elif isinstance(c, str):
            email_cliente = normalize_email(c)
            if email_cliente == email_normalized:
                return {
                    "nome": email_normalized.split("@")[0],
                    "email": email_cliente,
                    "estilo_resumo": "",
                    "tamanho_top": "",
                    "tamanho_bottom": "",
                    "tamanho_dress": "",
                    "cidade": "",
                }
    return None


@router.post("/lookup")
def lookup_customer_closet(payload: LookupRequest):
    try:
        email = normalize_email(payload.email)

        if not email:
            raise HTTPException(status_code=400, detail="E-mail é obrigatório")

        clientes_path = DATA_MODELS_DIR / "clientes.json"
        clientes = load_json("clientes.json") if clientes_path.exists() else []

        if not isinstance(clientes, list):
            clientes = []

        cliente_encontrado = find_cliente_by_email(clientes, email)
        closet_data = get_customer_closet(email)
        closet_products = closet_data.get("closet_products", [])

        customer_name = (
            cliente_encontrado.get("nome")
            if cliente_encontrado
            else email.split("@")[0]
        )

        customer = {
            "name": customer_name,
            "email": email,
        }

        return {
            "customer": customer,
            "closet": closet_products,
            "looks": [],
            "recommendations": [],
            "debug": {
                "email_input": payload.email,
                "email_normalized": email,
                "cliente_found": cliente_encontrado is not None,
                "pedidos_count": closet_data.get("total_pedidos", 0),
                "closet_final_count": len(closet_products),
                "messages": [
                    f"{closet_data.get('total_pedidos', 0)} pedido(s) encontrado(s)",
                    f"{len(closet_products)} peça(s) no closet",
                ],
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        print("🔥 ERRO REAL NO LOOKUP:")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/questions")
def get_questions():
    return {
        "questions": [
            {
                "id": "ocasiao",
                "label": "Para qual ocasião você quer montar esse look?",
                "type": "single_select",
                "options": [
                    {"value": "praia", "label": "Praia / Resort"},
                    {"value": "dia_a_dia", "label": "Dia a dia"},
                    {"value": "viagem", "label": "Viagem"},
                    {"value": "evento", "label": "Evento especial"},
                ],
            },
            {
                "id": "objetivo",
                "label": "O que você quer encontrar agora?",
                "type": "single_select",
                "options": [
                    {"value": "completar_look", "label": "Completar look"},
                    {"value": "novidades", "label": "Ver novidades"},
                    {"value": "similares", "label": "Peças similares"},
                ],
            },
            {
                "id": "estilo",
                "label": "Qual estilo combina mais com você?",
                "type": "single_select",
                "options": [
                    {"value": "elegante", "label": "Elegante"},
                    {"value": "classico", "label": "Clássico"},
                    {"value": "casual", "label": "Casual"},
                    {"value": "colorido", "label": "Colorido"},
                ],
            },
        ]
    }


@router.post("/recommendations")
def get_recommendations(payload: RecommendationRequest):
    try:
        email = normalize_email(payload.email)
        if not email:
            raise HTTPException(status_code=400, detail="E-mail é obrigatório")

        closet_data = get_customer_closet(email)
        closet_products = closet_data.get("closet_products", [])

        if not closet_products:
            return {
                "email": email,
                "profile": {},
                "recommendations": [],
                "insights": ["Nenhuma peça encontrada no closet para gerar recomendações."],
            }

        products_path = DATA_MODELS_DIR / "products_enriched.json"
        raw_catalog = load_json("products_enriched.json") if products_path.exists() else []
        catalog = flatten_catalog(raw_catalog)

        result = build_recommendations(
            closet_products=closet_products,
            catalog=catalog,
            answers=payload.answers or {},
            limit=payload.limit or 8,
        )

        return {
            "email": email,
            "profile": result["profile"],
            "filters_applied": result["rules"],
            "recommendations": result["recommendations"],
            "meta": result["meta"],
            "insights": [
                f"{len(closet_products)} peça(s) analisadas no closet",
                f"Catálogo analisado: {len(catalog)} itens",
                "Produtos já comprados foram excluídos por SKU, product_id, ref_id e nome",
                "Regras de ocasião, objetivo, departamento, gênero e categoria foram aplicadas",
            ],
        }

    except HTTPException:
        raise
    except Exception as e:
        print("🔥 ERRO REAL NAS RECOMMENDATIONS:")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))