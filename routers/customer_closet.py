import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from services.customer_closet_service import (
    CustomerClosetService,
    get_customer_closet_payload,
)
from services.recommendation_service import get_customer_recommendations

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/customer-closet", tags=["customer-closet"])


class EmailLookupRequest(BaseModel):
    email: str


class RecommendationRequest(BaseModel):
    email: str
    ocasiao: Optional[str] = None
    objetivo: Optional[str] = None
    estilo: Optional[str] = None
    answers: Optional[dict] = None
    limit: int = 8


class QuestionsResponse(BaseModel):
    questions: list


@router.post("/lookup")
async def lookup_customer(
    data: EmailLookupRequest,
    db: AsyncSession = Depends(get_db),
):
    """Public endpoint: look up customer by email and return closet data."""
    try:
        # Tenta via CustomerClosetService primeiro
        try:
            service = CustomerClosetService(db)
            result = await service.lookup_by_email(data.email)
            if result:
                return result
        except Exception:
            pass

        # Fallback para get_customer_closet_payload
        result = await get_customer_closet_payload(data.email)
        
        # Adapta formato para o frontend
        closet = result.get("closet", [])
        return {
            "found": result.get("found", False),
            "cliente": result.get("customer") or {"name": data.email.split("@")[0], "email": data.email},
            "closet_products": closet,
            "recommendations": result.get("recommendations", []),
            "debug": result.get("debug", {}),
        }
    except Exception as e:
        logger.error(f"Customer lookup error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/recommendations")
async def get_customer_recommendations_endpoint(
    data: RecommendationRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Public endpoint: get recommendations for a customer.
    Compatível com o widget JS da VTEX e o MeuClosetPage.tsx
    """
    try:
        # Extrai answers do quiz
        answers = data.answers or {}
        ocasiao = data.ocasiao or answers.get("ocasiao") or answers.get("occasion") or ""
        objetivo = data.objetivo or answers.get("objetivo") or answers.get("goal") or ""
        estilo = data.estilo or answers.get("estilo") or answers.get("style") or ""

        recs = await get_customer_recommendations(
            email=data.email,
            occasion=ocasiao,
            goal=objetivo,
            style=estilo,
            limit=data.limit,
        )

        # Formata compatível com widget VTEX
        formatted = []
        for r in recs:
            url = r.get("url") or r.get("product_url") or ""
            if url and url.startswith("/"):
                url = f"https://aguadecoco.com.br{url}"

            img = r.get("image_url") or r.get("imagem_url") or ""

            formatted.append({
                "produto_id": r.get("product_id"),
                "sku_id": r.get("sku_id"),
                "ref_id": r.get("ref_id"),
                "nome": r.get("name"),
                "name": r.get("name"),
                "motivo": r.get("reason") or "Selecionado para você",
                "reason": r.get("reason") or "Selecionado para você",
                "score": r.get("score", 0),
                "imagem_url": img,
                "image_url": img,
                "link_produto": url,
                "product_url": url,
                "categoria": r.get("category"),
                "category": r.get("category"),
                "departamento": r.get("department"),
                "department": r.get("department"),
                "price": r.get("price"),
                "preco": r.get("price"),
            })

        return {
            "email": data.email,
            "recommendations": formatted,
            "total": len(formatted),
            "answers": {
                "ocasiao": ocasiao,
                "objetivo": objetivo,
                "estilo": estilo,
            },
        }

    except Exception as e:
        logger.error(f"Recommendations error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/questions")
async def get_quiz_questions():
    """
    Retorna as perguntas do quiz de estilo.
    Usado pelo widget JS da VTEX para montar o formulário.
    """
    return {
        "questions": [
            {
                "id": "ocasiao",
                "label": "Para qual ocasião você está montando seu look?",
                "options": [
                    {"value": "praia", "label": "Praia / Resort"},
                    {"value": "casual", "label": "Dia a dia casual"},
                    {"value": "trabalho", "label": "Trabalho / Reuniões"},
                    {"value": "festa", "label": "Festa / Evento especial"},
                ],
            },
            {
                "id": "objetivo",
                "label": "O que você está buscando agora?",
                "options": [
                    {"value": "completar_look", "label": "Completar um look que já tenho"},
                    {"value": "novidades", "label": "Descobrir novidades da coleção"},
                    {"value": "similares", "label": "Encontrar peças parecidas com as que amo"},
                    {"value": "presente", "label": "Estou procurando um presente"},
                ],
            },
            {
                "id": "estilo",
                "label": "Qual estilo mais combina com você agora?",
                "options": [
                    {"value": "minimalista", "label": "Minimalista e clean"},
                    {"value": "colorido", "label": "Colorido e alegre"},
                    {"value": "sofisticado", "label": "Sofisticado e elegante"},
                    {"value": "despojado", "label": "Despojado e confortável"},
                ],
            },
            {
                "id": "preferencia",
                "label": "O que você prefere no momento?",
                "options": [
                    {"value": "estampado", "label": "Estampas e prints"},
                    {"value": "liso", "label": "Cores sólidas e lisas"},
                    {"value": "neutros", "label": "Tons neutros (bege, branco, preto)"},
                    {"value": "colorblock", "label": "Color block e contrastes"},
                ],
            },
        ]
    }
