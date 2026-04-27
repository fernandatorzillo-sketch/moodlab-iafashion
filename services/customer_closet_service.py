from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.catalog_product import CatalogProduct
from models.customer import Customer
from models.customer_closet_item import CustomerClosetItem
from services.closet_db import AsyncSessionLocal
from services.recommendation_service import get_customer_recommendations


SITE_BASE = "https://www.aguadecoco.com.br"


def normalize_email(email: str) -> str:
    return str(email or "").strip().lower()


def slugify(value: str) -> str:
    value = str(value or "").strip().lower()
    replacements = {
        "á": "a", "à": "a", "ã": "a", "â": "a",
        "é": "e", "ê": "e",
        "í": "i",
        "ó": "o", "õ": "o", "ô": "o",
        "ú": "u",
        "ç": "c",
    }
    for old, new in replacements.items():
        value = value.replace(old, new)

    cleaned = []
    for char in value:
        if char.isalnum():
            cleaned.append(char)
        elif char in [" ", "-", "_", "/"]:
            cleaned.append("-")

    slug = "".join(cleaned)
    while "--" in slug:
        slug = slug.replace("--", "-")

    return slug.strip("-")


def fix_image_url(url: str | None) -> str:
    if not url:
        return ""
    return str(url).strip()


def build_product_url(name: str | None, product_id: str | None, url: str | None) -> str:
    if url:
        url = str(url).strip()
        if url.startswith("http"):
            return url
        if url.startswith("/"):
            return f"{SITE_BASE}{url}"
        return f"{SITE_BASE}/{url.lstrip('/')}"

    if name:
        slug = slugify(name)
        if slug:
            return f"{SITE_BASE}/{slug}/p"

    if product_id:
        return f"{SITE_BASE}/busca?fq=productId:{product_id}"

    return SITE_BASE


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
                "recommendation_count": 0,
                "message": "E-mail vazio.",
            },
        }

    async with AsyncSessionLocal() as session:
        customer = await _get_customer(session, email)
        closet_items = await _get_customer_closet_items(session, email)

    recommendations = await get_customer_recommendations(email=email, limit=12)

    customer_name = email.split("@")[0]
    if customer:
        customer_name = customer.full_name or customer.first_name or customer_name

    closet_payload = []
    for item, catalog in closet_items:
        name = item.name or (catalog.name if catalog else None)
        product_id = item.product_id or (catalog.product_id if catalog else None)
        sku_id = item.sku_id or (catalog.sku_id if catalog else None)
        ref_id = item.ref_id or (catalog.ref_id if catalog else None)
        category = item.category or (catalog.category if catalog else None)
        department = item.department or (catalog.department if catalog else None)
        brand = item.brand or (catalog.brand if catalog else None)
        image_url = item.image_url or (catalog.image_url if catalog else None)
        product_url = item.product_url or (catalog.product_url if catalog else None)

        final_url = build_product_url(name=name, product_id=product_id, url=product_url)

        closet_payload.append(
            {
                "id": product_id or sku_id,
                "sku": sku_id,
                "sku_id": sku_id,
                "product_id": product_id,
                "produto_id": product_id,
                "ref_id": ref_id,

                "nome": name,
                "name": name,

                "categoria": category,
                "category": category,

                "departamento": department,
                "department": department,

                "brand": brand,

                "imagem_url": fix_image_url(image_url),
                "image_url": fix_image_url(image_url),

                "link_produto": final_url,
                "product_url": final_url,
                "url": final_url,

                "cor": catalog.color if catalog else None,
                "color": catalog.color if catalog else None,
                "tamanho": catalog.size if catalog else None,
                "size": catalog.size if catalog else None,
                "colecao": catalog.collection if catalog else None,
                "collection": catalog.collection if catalog else None,

                "preco": None,
                "price": None,

                "purchase_count": item.purchase_count,
                "quantity": item.total_quantity,
                "total_spent": float(item.total_spent or 0),
                "last_purchase_at": item.last_purchase_at.isoformat() if item.last_purchase_at else None,
            }
        )

    recs_payload = []
    for r in recommendations:
        name = r.get("name")
        product_id = r.get("product_id")
        product_url = r.get("product_url") or r.get("url")
        final_url = build_product_url(name=name, product_id=product_id, url=product_url)

        recs_payload.append(
            {
                "produto_id": product_id,
                "product_id": product_id,
                "sku_id": r.get("sku_id"),
                "ref_id": r.get("ref_id"),

                "nome": name,
                "name": name,

                "motivo": r.get("reason") or "Selecionado para você",
                "reason": r.get("reason") or "Selecionado para você",

                "score": float(r.get("score") or 0),

                "imagem_url": fix_image_url(r.get("image_url")),
                "image_url": fix_image_url(r.get("image_url")),

                "link_produto": final_url,
                "product_url": final_url,
                "url": final_url,

                "categoria": r.get("category"),
                "category": r.get("category"),

                "departamento": r.get("department"),
                "department": r.get("department"),

                "recommendation_type": r.get("recommendation_type"),
                "price": r.get("price"),
                "preco": r.get("price"),
            }
        )

    return {
        "found": len(closet_payload) > 0,
        "customer": {
            "name": customer_name,
            "email": email,
        },

        # formato base
        "closet": closet_payload,
        "looks": [],
        "recommendations": recs_payload,

        # formato usado pelo React atual
        "cliente": {
            "nome": customer_name,
            "email": email,
        },
        "closet_products": closet_payload,

        "debug": {
            "email": email,
            "closet_count": len(closet_payload),
            "recommendation_count": len(recs_payload),
            "message": "Closet e recomendações lidos do banco consolidado com enriquecimento de catálogo.",
        },
    }


async def _get_customer(session: AsyncSession, email: str):
    result = await session.execute(
        select(Customer).where(Customer.email == email)
    )
    return result.scalar_one_or_none()


async def _get_customer_closet_items(session: AsyncSession, email: str):
    result = await session.execute(
        select(CustomerClosetItem, CatalogProduct)
        .outerjoin(
            CatalogProduct,
            CatalogProduct.sku_id == CustomerClosetItem.sku_id,
        )
        .where(CustomerClosetItem.email == email)
        .order_by(CustomerClosetItem.last_purchase_at.desc().nullslast())
    )
    return result.all()