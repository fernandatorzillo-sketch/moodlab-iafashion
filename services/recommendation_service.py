from sqlalchemy import func, or_, select

from models.catalog_product import CatalogProduct
from models.customer_recommendation import CustomerRecommendation
from models.inventory_by_sku import InventoryBySku
from services.closet_db import AsyncSessionLocal

SITE_BASE = "https://www.aguadecoco.com.br"


def normalize(value) -> str:
    return str(value or "").strip().lower()


def clean_url(url) -> str:
    if not url:
        return SITE_BASE

    url = str(url).strip()

    if url.startswith("http"):
        return url

    if url.startswith("/"):
        return f"{SITE_BASE}{url}"

    return f"{SITE_BASE}/{url}"


def is_blocked_home_product(product: CatalogProduct) -> bool:
    text = normalize(
        " ".join(
            [
                str(product.name or ""),
                str(product.category or ""),
                str(product.department or ""),
                str(product.product_type or ""),
            ]
        )
    )

    blocked_terms = [
        "bandeja",
        "copo",
        "taça",
        "taca",
        "vaso",
        "porta",
        "guardanapo",
        "mesa",
        "prato",
        "casa",
        "decor",
        "home",
        "almofada",
        "toalha",
        "jogo americano",
    ]

    return any(term in text for term in blocked_terms)


def is_fashion_product(product: CatalogProduct) -> bool:
    if is_blocked_home_product(product):
        return False

    text = normalize(
        " ".join(
            [
                str(product.name or ""),
                str(product.category or ""),
                str(product.department or ""),
                str(product.product_type or ""),
            ]
        )
    )

    fashion_terms = [
        "biquini",
        "biquíni",
        "sutiã",
        "sutia",
        "calcinha",
        "maiô",
        "maio",
        "vestido",
        "short",
        "saia",
        "camisa",
        "blusa",
        "camiseta",
        "top",
        "cropped",
        "calça",
        "calca",
        "pantalona",
        "pareô",
        "pareo",
        "saída",
        "saida",
        "body",
    ]

    return any(term in text for term in fashion_terms)


def _is_blocked_payload(name, category, department) -> bool:
    text = normalize(" ".join([str(name or ""), str(category or ""), str(department or "")]))

    blocked_terms = [
        "bandeja",
        "copo",
        "taça",
        "taca",
        "vaso",
        "porta",
        "guardanapo",
        "mesa",
        "prato",
        "casa",
        "decor",
        "home",
    ]

    return any(term in text for term in blocked_terms)


def score_product(product: CatalogProduct, occasion: str = "", goal: str = "", style: str = "") -> float:
    text = normalize(
        " ".join(
            [
                str(product.name or ""),
                str(product.category or ""),
                str(product.department or ""),
                str(product.product_type or ""),
                str(product.occasion or ""),
                str(product.collection or ""),
            ]
        )
    )

    score = 1.0

    if occasion:
        if occasion in text:
            score += 5

        if occasion == "praia" and any(
            x in text for x in ["biquini", "biquíni", "maiô", "maio", "saida", "saída", "pareo", "pareô"]
        ):
            score += 5

        if occasion == "resort" and any(
            x in text for x in ["vestido", "camisa", "pantalona", "saia", "linho"]
        ):
            score += 4

        if occasion == "jantar" and any(
            x in text for x in ["vestido", "camisa", "calça", "calca", "alfaiataria"]
        ):
            score += 4

    if goal == "cross_sell":
        if any(
            x in text
            for x in [
                "saida",
                "saída",
                "pareo",
                "pareô",
                "camisa",
                "short",
                "saia",
                "calça",
                "calca",
                "top",
                "blusa",
            ]
        ):
            score += 4

    if goal == "up_sell":
        if any(x in text for x in ["vestido", "resort", "bordado", "alfaiataria", "camisa", "linho"]):
            score += 5

    if style:
        if style in text:
            score += 3

        if style == "elegante" and any(x in text for x in ["vestido", "camisa", "alfaiataria"]):
            score += 3

        if style == "leve" and any(x in text for x in ["linho", "praia", "resort", "saida", "saída", "pareo", "pareô"]):
            score += 3

        if style == "casual" and any(x in text for x in ["short", "camiseta", "blusa", "top"]):
            score += 3

    return score


def build_reason(product: CatalogProduct, occasion: str = "", goal: str = "", style: str = "") -> str:
    parts = []

    if goal == "cross_sell":
        parts.append("Sugestão pensada para complementar peças do seu closet.")
    elif goal == "up_sell":
        parts.append("Sugestão com proposta mais sofisticada para elevar o look.")
    else:
        parts.append("Sugestão de moda disponível em estoque para combinar com seu closet.")

    if occasion:
        parts.append(f"Faz sentido para momentos de {occasion.replace('_', ' ')}.")

    if style:
        parts.append(f"Conversa com um estilo {style}.")

    return " ".join(parts)


async def get_customer_recommendations(
    email: str,
    occasion: str = "",
    goal: str = "",
    style: str = "",
    limit: int = 12,
) -> list[dict]:
    email = normalize(email)
    email_like = email if "%" in email else f"{email}%"
    limit = max(1, min(int(limit or 12), 24))

    async with AsyncSessionLocal() as session:
        saved_result = await session.execute(
            select(CustomerRecommendation)
            .where(CustomerRecommendation.email.ilike(email_like))
            .order_by(CustomerRecommendation.score.desc().nullslast())
            .limit(limit * 3)
        )

        saved_items = saved_result.scalars().all()

        saved_fashion = [
            _format_saved(item)
            for item in saved_items
            if not _is_blocked_payload(item.name, item.category, item.department)
        ]

        if saved_fashion:
            return saved_fashion[:limit]

        product_query = (
            select(CatalogProduct)
            .join(InventoryBySku, InventoryBySku.sku_id == CatalogProduct.sku_id)
            .where(
                CatalogProduct.is_active == 1,
                CatalogProduct.sku_id.is_not(None),
                InventoryBySku.quantity > 0,
                InventoryBySku.is_available == 1,
                or_(
                    func.lower(func.coalesce(CatalogProduct.name, "")).like("%biquini%"),
                    func.lower(func.coalesce(CatalogProduct.name, "")).like("%biquíni%"),
                    func.lower(func.coalesce(CatalogProduct.name, "")).like("%sutia%"),
                    func.lower(func.coalesce(CatalogProduct.name, "")).like("%sutiã%"),
                    func.lower(func.coalesce(CatalogProduct.name, "")).like("%calcinha%"),
                    func.lower(func.coalesce(CatalogProduct.name, "")).like("%maiô%"),
                    func.lower(func.coalesce(CatalogProduct.name, "")).like("%maio%"),
                    func.lower(func.coalesce(CatalogProduct.name, "")).like("%vestido%"),
                    func.lower(func.coalesce(CatalogProduct.name, "")).like("%short%"),
                    func.lower(func.coalesce(CatalogProduct.name, "")).like("%saia%"),
                    func.lower(func.coalesce(CatalogProduct.name, "")).like("%camisa%"),
                    func.lower(func.coalesce(CatalogProduct.name, "")).like("%blusa%"),
                    func.lower(func.coalesce(CatalogProduct.name, "")).like("%camiseta%"),
                    func.lower(func.coalesce(CatalogProduct.name, "")).like("%top%"),
                    func.lower(func.coalesce(CatalogProduct.name, "")).like("%cropped%"),
                    func.lower(func.coalesce(CatalogProduct.name, "")).like("%calça%"),
                    func.lower(func.coalesce(CatalogProduct.name, "")).like("%calca%"),
                    func.lower(func.coalesce(CatalogProduct.name, "")).like("%pantalona%"),
                    func.lower(func.coalesce(CatalogProduct.name, "")).like("%pareô%"),
                    func.lower(func.coalesce(CatalogProduct.name, "")).like("%pareo%"),
                    func.lower(func.coalesce(CatalogProduct.name, "")).like("%saída%"),
                    func.lower(func.coalesce(CatalogProduct.name, "")).like("%saida%"),
                    func.lower(func.coalesce(CatalogProduct.name, "")).like("%body%"),
                ),
            )
            .limit(limit * 5)
        )

        result = await session.execute(product_query)
        products = result.scalars().all()

    products = [product for product in products if is_fashion_product(product)]

    scored = [
        (score_product(product, occasion=occasion, goal=goal, style=style), product)
        for product in products
    ]

    scored.sort(key=lambda item: item[0], reverse=True)

    return [
        _format_product(
            product=product,
            score=score,
            occasion=occasion,
            goal=goal,
            style=style,
        )
        for score, product in scored[:limit]
    ]


def _format_saved(item: CustomerRecommendation) -> dict:
    url = clean_url(item.product_url)

    return {
        "sku_id": item.sku_id,
        "product_id": item.product_id,
        "ref_id": item.ref_id,
        "name": item.name,
        "nome": item.name,
        "category": item.category,
        "categoria": item.category,
        "department": item.department,
        "departamento": item.department,
        "image_url": item.image_url or "",
        "imagem_url": item.image_url or "",
        "product_url": url,
        "link_produto": url,
        "url": url,
        "reason": item.reason or "Sugestão de moda disponível em estoque para combinar com seu closet.",
        "motivo": item.reason or "Sugestão de moda disponível em estoque para combinar com seu closet.",
        "recommendation_type": item.recommendation_type or "fashion_stock",
        "score": float(item.score or 0),
    }


def _format_product(
    product: CatalogProduct,
    score: float,
    occasion: str = "",
    goal: str = "",
    style: str = "",
) -> dict:
    url = clean_url(product.product_url)

    reason = build_reason(product, occasion=occasion, goal=goal, style=style)

    return {
        "sku_id": product.sku_id,
        "product_id": product.product_id,
        "ref_id": product.ref_id,
        "name": product.name,
        "nome": product.name,
        "category": product.category,
        "categoria": product.category,
        "department": product.department,
        "departamento": product.department,
        "product_type": product.product_type,
        "tipo_produto": product.product_type,
        "occasion": product.occasion,
        "ocasiao": product.occasion,
        "estamparia": product.print_name,
        "color": product.color,
        "cor": product.color,
        "size": product.size,
        "tamanho": product.size,
        "collection": product.collection,
        "colecao": product.collection,
        "image_url": product.image_url or "",
        "imagem_url": product.image_url or "",
        "product_url": url,
        "link_produto": url,
        "url": url,
        "reason": reason,
        "motivo": reason,
        "recommendation_type": goal or "fashion_stock",
        "score": float(score or 0),
    }