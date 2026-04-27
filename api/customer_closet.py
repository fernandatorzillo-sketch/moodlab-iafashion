from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from services.customer_closet_service import get_customer_closet_payload
from services.recommendation_service import get_customer_recommendations

router = APIRouter(prefix="/api/v1/customer-closet", tags=["customer-closet"])


class LookupRequest(BaseModel):
    email: str


class RecommendationRequest(BaseModel):
    email: str
    answers: dict[str, Any] = {}
    limit: int = 8


def normalize_email(email: Any) -> str:
    return str(email or "").strip().lower()


def normalize_answers(raw: dict[str, Any] | None) -> dict[str, str]:
    raw = raw or {}
    return {
        "occasion": str(raw.get("occasion") or raw.get("ocasiao") or raw.get("ocasião") or "").strip().lower(),
        "goal": str(raw.get("goal") or raw.get("objetivo") or "").strip().lower(),
        "style": str(raw.get("style") or raw.get("estilo") or "").strip().lower(),
    }


@router.post("/lookup")
async def lookup_customer_closet(payload: LookupRequest):
    email = normalize_email(payload.email)
    if not email:
        raise HTTPException(status_code=400, detail="E-mail é obrigatório")

    data = await get_customer_closet_payload(email)

    customer = data.get("customer") or {
        "name": email.split("@")[0],
        "email": email,
    }

    return {
        **data,

        # compatível com MeuClosetPage.tsx
        "cliente": {
            "nome": customer.get("name") or email.split("@")[0],
            "email": customer.get("email") or email,
        },
        "closet_products": data.get("closet", []),
    }


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
    email = normalize_email(payload.email)
    if not email:
        raise HTTPException(status_code=400, detail="E-mail é obrigatório")

    answers = normalize_answers(payload.answers)
    limit = max(1, min(int(payload.limit or 8), 24))

    recommendations = await get_customer_recommendations(
        email=email,
        occasion=answers["occasion"],
        goal=answers["goal"],
        style=answers["style"],
        limit=limit,
    )

    return {
        "email": email,
        "answers": answers,
        "count": len(recommendations),
        "recommendations": recommendations,
        "debug": {
            "email": email,
            "limit": limit,
            "recommendation_count": len(recommendations),
            "message": "Recomendações lidas do banco consolidado.",
        },
    }