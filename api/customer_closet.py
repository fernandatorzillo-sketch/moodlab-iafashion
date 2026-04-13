import traceback
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from services.customer_closet_service import get_customer_closet_payload
from services.catalog_service import get_catalog_products
from services.recommendation_engine import build_recommendations

router = APIRouter(prefix="/api/v1/customer-closet", tags=["customer-closet"])


class LookupRequest(BaseModel):
    email: str


class RecommendationRequest(BaseModel):
    email: str
    answers: dict[str, Any] = {}
    limit: int = 8


def normalize_email(email: Any) -> str:
    return str(email or "").strip().lower()


@router.post("/lookup")
async def lookup_customer_closet(payload: LookupRequest):
    try:
        email = normalize_email(payload.email)
        if not email:
            raise HTTPException(status_code=400, detail="E-mail é obrigatório")

        return get_customer_closet_payload(email)

    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/questions")
async def get_questions():
    return {
        "questions": [
            {
                "id": "occasion",
                "label": "Para qual ocasião você quer sugestões agora?",
                "type": "single_select",
                "options": [
                    {"value": "praia", "label": "Praia"},
                    {"value": "resort", "label": "Resort"},
                    {"value": "jantar", "label": "Jantar"},
                    {"value": "viagem", "label": "Viagem"},
                    {"value": "dia_a_dia", "label": "Dia a dia"},
                ],
            },
            {
                "id": "goal",
                "label": "O que você quer encontrar?",
                "type": "single_select",
                "options": [
                    {"value": "cross_sell", "label": "Complementar meus looks"},
                    {"value": "up_sell", "label": "Peças mais sofisticadas"},
                    {"value": "novidades", "label": "Novidades para meu estilo"},
                ],
            },
            {
                "id": "style",
                "label": "Qual estilo você quer priorizar hoje?",
                "type": "single_select",
                "options": [
                    {"value": "elegante", "label": "Elegante"},
                    {"value": "casual", "label": "Casual"},
                    {"value": "sofisticado", "label": "Sofisticado"},
                    {"value": "leve", "label": "Leve"},
                ],
            },
        ]
    }


@router.post("/recommendations")
async def recommend(payload: RecommendationRequest):
    try:
        email = normalize_email(payload.email)
        if not email:
            raise HTTPException(status_code=400, detail="E-mail é obrigatório")

        closet_payload = get_customer_closet_payload(email)
        catalog = get_catalog_products()

        result = build_recommendations(
            closet_products=closet_payload.get("closet", []),
            catalog=catalog,
            answers=payload.answers or {},
            style_preferences=closet_payload.get("customer", {}).get("style_preferences", {}),
            limit=payload.limit or 8,
        )

        return result

    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))