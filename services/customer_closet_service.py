from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.customer import Customer
from models.customer_closet_item import CustomerClosetItem
from services.closet_db import AsyncSessionLocal
from services.recommendation_service import get_customer_recommendations


def normalize_email(email: str) -> str:
    return str(email or "").strip().lower()


def fix_image_url(url: str) -> str:
    """
    Garante que a URL da imagem usa o domínio correto da VTEX.
    Algumas imagens estão salvas com 'lojaaguadecoco.vteximg.com.br'
    que pode retornar 404. Mantém o domínio original mas adiciona
    fallback para imagens inativas.
    """
    if not url:
        return ""
    return str(url).strip()


def fix_product_url(url: str) -> str:
    """
    Garante que a URL do produto aponta para o site de produção.
    """
    if not url:
        return ""
    url = str(url).strip()
    # Se a URL não tem domínio, adiciona o domínio correto
    if url.startswith("/"):
        return f"https://aguadecoco.com.br{url}"
    return url


async def get_customer_closet_payload(email: str) -> dict:
    email = normalize_email(email)

    if not email:
        return {
            "found": False,
            "customer": None,
            "closet": [],
            "looks": [],
            "recommendations": [],
            "debug": {
                "email": "",
                "closet_count": 0,
                "message": "E-mail vazio.",
            },
        }

    async with AsyncSessionLocal() as session:
        customer = await _get_customer(session, email)
        closet_items = await _get_customer_closet_items(session, email)

    recommendations = await get_customer_recommendations(email)

    customer_name = None
    if customer:
        customer_name = customer.full_name or customer.first_name or email.split("@")[0]
    else:
        customer_name = email.split("@")[0]

    closet_payload = [
        {
            # IDs
            "id": item.product_id or item.sku_id,
            "sku_id": item.sku_id,
            "product_id": item.product_id,
            "ref_id": item.ref_id,

            # Nome — compatível com frontend VTEX e MeuClosetPage
            "nome": item.name,
            "name": item.name,

            # Categoria — ambos os formatos
            "categoria": item.category,
            "category": item.category,

            # Departamento
            "departamento": item.department,
            "department": item.department,

            # Imagem — ambos os formatos que o frontend usa
            "imagem_url": fix_image_url(item.image_url),
            "image_url": fix_image_url(item.image_url),

            # Link — ambos os formatos
            "link_produto": fix_product_url(item.product_url),
            "product_url": fix_product_url(item.product_url),
            "url": fix_product_url(item.product_url),

            # Outros campos
            "brand": item.brand,
            "cor": None,
            "color": None,
            "preco": None,
            "price": None,
            "purchase_count": item.purchase_count,
            "quantity": item.total_quantity,
            "total_spent": float(item.total_spent or 0),
            "last_purchase_at": item.last_purchase_at.isoformat() if item.last_purchase_at else None,
        }
        for item in closet_items
    ]

    # Formata recomendações compatível com frontend VTEX
    recs_payload = [
        {
            "produto_id": r.get("product_id"),
            "sku_id": r.get("sku_id"),
            "ref_id": r.get("ref_id"),
            "nome": r.get("name"),
            "name": r.get("name"),
            "motivo": r.get("reason") or "Selecionado para você",
            "reason": r.get("reason") or "Selecionado para você",
            "score": r.get("score", 0),
            "imagem_url": fix_image_url(r.get("image_url", "")),
            "image_url": fix_image_url(r.get("image_url", "")),
            "link_produto": fix_product_url(r.get("url", "") or r.get("product_url", "")),
            "product_url": fix_product_url(r.get("url", "") or r.get("product_url", "")),
            "categoria": r.get("category"),
            "category": r.get("category"),
            "departamento": r.get("department"),
            "department": r.get("department"),
            "price": r.get("price"),
            "preco": r.get("price"),
        }
        for r in recommendations
    ]

    return {
        "found": len(closet_payload) > 0,
        "customer": {
            "name": customer_name,
            "email": email,
        },
        "closet": closet_payload,
        "looks": [],
        "recommendations": recs_payload,
        "debug": {
            "email": email,
            "closet_count": len(closet_payload),
            "recommendation_count": len(recs_payload),
            "message": "Closet e recomendações lidos do banco consolidado.",
        },
    }


async def _get_customer(session: AsyncSession, email: str):
    result = await session.execute(
        select(Customer).where(Customer.email == email)
    )
    return result.scalar_one_or_none()


async def _get_customer_closet_items(session: AsyncSession, email: str):
    result = await session.execute(
        select(CustomerClosetItem)
        .where(CustomerClosetItem.email == email)
        .order_by(CustomerClosetItem.last_purchase_at.desc().nullslast())
    )
    return result.scalars().all()
