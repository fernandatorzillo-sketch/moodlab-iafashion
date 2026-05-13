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
    Normaliza a URL da imagem VTEX para 500x500.
    Remove query string (?v=...) que pode causar erros no proxy.
    Suporta formatos:
      /arquivos/ids/123456/nome.jpg
      /arquivos/ids/123456-728-1090/nome.jpg
      /arquivos/ids/123456-728-1090/nome.jpg?v=638...
    """
    if not url:
        return ""
    import re
    url = str(url).strip()
    # Remove query string (?v=... ou qualquer ?...)
    url = re.sub(r'\?.*$', '', url)
    # Normaliza dimensoes para 500-500
    # Caso 1: tem dimensoes  -> /ids/123456-728-1090/nome -> /ids/123456-500-500/nome
    # Caso 2: sem dimensoes  -> /ids/123456/nome          -> /ids/123456-500-500/nome
    url = re.sub(
        r'(/arquivos/ids/[0-9]+)(?:-[0-9]+-[0-9]+)?(/[^?#]+)',
        lambda m: m.group(1) + "-500-500" + m.group(2),
        url,
    )
    return url


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


def _analyze_print_preference(closet_items) -> str:
    """
    Analisa o campo estamparia das peças do closet para determinar
    preferência do cliente: 'estampado', 'liso' ou 'misto'.
    """
    estampados = 0
    lisos = 0
    for item in closet_items:
        # Tenta ler estamparia do nome do produto como fallback
        name = (item.name or "").lower()
        # Padrões de liso
        if any(t in name for t in ["liso", "basico", "básico", "solido", "sólido", "uni"]):
            lisos += 1
        # Padrões de estampado
        elif any(t in name for t in [
            "estampa", "floral", "listrad", "xadrez", "tie dye", "animal",
            "onça", "onca", "zebra", "cobra", "leopard", "floresta", "folhagem",
            "coqueiros", "borboleta", "palha", "tropical", "geometr", "poa", "poá",
            "losango", "arabesco", "abstrat", "wave", "onda", "espiral",
        ]):
            estampados += 1
        else:
            lisos += 1  # default: considera liso
    total = estampados + lisos
    if total == 0:
        return "misto"
    ratio = estampados / total
    if ratio >= 0.6:
        return "estampado"
    elif ratio <= 0.3:
        return "liso"
    return "misto"


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

    # Analisa perfil de estamparia do cliente (liso vs estampado)
    estamparia_profile = _analyze_print_preference(closet_items)

    recommendations = await get_customer_recommendations(
        email,
        print_preference=estamparia_profile,
    )

    customer_name = None
    if customer:
        customer_name = customer.full_name or customer.first_name or email.split("@")[0]
    else:
        customer_name = email.split("@")[0]

    # Departamentos que NÃO são moda — excluir do closet
    NON_FASHION_DEPTS = {"casa", "infantil", "kit", "kits", "utilidades", "mesa", "cama", "banho"}
    def is_fashion_item(item) -> bool:
        dept = (item.department or "").lower().strip()
        name = (item.name or "").lower()
        # Exclui departamentos não-moda
        if dept in NON_FASHION_DEPTS:
            return False
        # Exclui itens sem nome ou nome genérico
        if not name or name == "produto":
            return False
        # Exclui itens claramente de casa pelo nome
        casa_terms = ["taça", "taca", "copo", "prato", "vaso", "vela", "toalha",
                      "almofada", "colcha", "lençol", "lenco", "porta", "quadro"]
        if any(t in name for t in casa_terms):
            return False
        return True

    fashion_items = [item for item in closet_items if is_fashion_item(item)]

    closet_payload = [
        {
            # IDs
            "id": item.product_id or item.sku_id,
            "sku_id": item.sku_id,
            "product_id": item.product_id,
            "ref_id": item.ref_id,

            # Nome
            "nome": item.name,
            "name": item.name,

            # Categoria
            "categoria": item.category,
            "category": item.category,

            # Departamento
            "departamento": item.department,
            "department": item.department,

            # Imagem — URL limpa sem ?v=
            "imagem_url": fix_image_url(item.image_url),
            "image_url": fix_image_url(item.image_url),

            # Link
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
        for item in fashion_items
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
        "found": len(closet_payload) > 0 or customer is not None,
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
