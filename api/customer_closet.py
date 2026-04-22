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


@router.post("/lookup")
async def lookup_customer_closet(payload: LookupRequest):
    email = normalize_email(payload.email)
    if not email:
        raise HTTPException(status_code=400, detail="E-mail é obrigatório")

    return await get_customer_closet_payload(email)


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
                "label": "Qual linguagem visual você quer priorizar hoje?",
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

    occasion = str(payload.answers.get("occasion") or "").strip().lower()
    goal = str(payload.answers.get("goal") or "").strip().lower()
    style = str(payload.answers.get("style") or "").strip().lower()

    recommendations = await get_customer_recommendations(
        email=email,
        occasion=occasion,
        goal=goal,
        style=style,
        limit=payload.limit,
    )

    return {
        "email": email,
        "answers": {
            "occasion": occasion,
            "goal": goal,
            "style": style,
        },
        "count": len(recommendations),
        "recommendations": recommendations,
        "message": "Recomendações lidas do banco com filtros da jornada atual.",
    }