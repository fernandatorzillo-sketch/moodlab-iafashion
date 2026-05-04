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
        "bandeja", "copo", "taça", "taca", "vaso", "porta", "guardanapo",
        "mesa", "prato", "casa", "decor", "home", "almofada", "toalha",
        "jogo americano", "infantil", "criança", "crianca", "kids", "baby",
        "bebê", "bebe", "juvenil",
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

    # Bloqueia infantil/kids independente de ter termos de moda
    if any(t in text for t in ["infantil", "criança", "crianca", "kids", "baby", "bebê", "bebe"]):
        return False
    return any(term in text for term in fashion_terms)


def _is_blocked_payload(name, category, department) -> bool:
    text = normalize(" ".join([str(name or ""), str(category or ""), str(department or "")]))

    blocked_terms = [
        "bandeja", "copo", "taça", "taca", "vaso", "porta", "guardanapo",
        "mesa", "prato", "casa", "decor", "home",
        "infantil", "criança", "crianca", "kids", "baby", "bebê", "bebe",
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


def build_reason(
    product: CatalogProduct,
    occasion: str = "",
    goal: str = "",
    style: str = "",
    closet_pieces: list[str] | None = None,
) -> str:
    """Gera motivo personalizado mencionando peças do closet que combinam."""
    product_name = str(product.name or "")
    product_type = str(product.product_type or product.category or "").lower()
    parts = []

    # Detecta o tipo de produto para encontrar complemento no closet
    TYPE_COMPLEMENTS = {
        "sutiã": ["calcinha", "biquíni calcinha", "saída"],
        "sutia": ["calcinha", "saida"],
        "calcinha": ["sutiã", "biquíni sutiã", "saída"],
        "maiô": ["saída de praia", "canga", "sandália"],
        "maio": ["saida", "canga"],
        "saída": ["maiô", "biquíni", "maio"],
        "saida": ["maio", "biquini"],
        "vestido": ["sandália", "bolsa", "acessório"],
        "blusa": ["calça", "short", "saia"],
        "calca": ["blusa", "camisa", "top"],
        "short": ["blusa", "top", "camisa"],
    }

    # Tenta mencionar peça do closet que combina
    closet_match = None
    if closet_pieces:
        name_lower = product_name.lower()
        for piece in closet_pieces:
            piece_lower = piece.lower()
            for ptype, complements in TYPE_COMPLEMENTS.items():
                if ptype in name_lower and any(c in piece_lower for c in complements):
                    closet_match = piece.split(" ")[:4]  # primeiras 4 palavras
                    closet_match = " ".join(closet_match)
                    break
                if ptype in piece_lower and any(c in name_lower for c in complements):
                    closet_match = piece.split(" ")[:4]
                    closet_match = " ".join(closet_match)
                    break
            if closet_match:
                break

    if goal == "cross_sell":
        if closet_match:
            parts.append(f"Combina com seu {closet_match} do closet.")
        else:
            parts.append("Complementa peças que você já tem no closet.")
    elif goal == "up_sell":
        parts.append("Proposta mais sofisticada para elevar o seu look.")
    elif goal == "novidades":
        parts.append("Novidade da coleção alinhada ao seu estilo.")
    else:
        if closet_match:
            parts.append(f"Combina com seu {closet_match}.")
        else:
            parts.append("Selecionado com base no seu histórico de compras.")

    if occasion:
        occ_label = occasion.replace("_", " ")
        parts.append(f"Ideal para {occ_label}.")

    if style and style != "casual":
        parts.append(f"Estilo {style}.")

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
        # Infere perfil do cliente (gênero, tipos já comprados) para filtrar recs
        profile = await _get_customer_profile(email, session)
        dominant_gender = profile.get("dominant_gender")

        saved_result = await session.execute(
            select(CustomerRecommendation)
            .where(CustomerRecommendation.email.ilike(email_like))
            .order_by(CustomerRecommendation.score.desc().nullslast())
            .limit(limit * 3)
        )

        saved_items = saved_result.scalars().all()

        def is_gender_match(item_name, item_cat, item_dept):
            """Verifica se o produto é do gênero dominante do cliente."""
            text = normalize(f"{item_name or ''} {item_cat or ''} {item_dept or ''}")
            if "infantil" in text or "kids" in text or "criança" in text:
                return False
            if dominant_gender == "feminino" and "masculino" in text and "feminino" not in text:
                return False
            if dominant_gender == "masculino" and "feminino" in text and "masculino" not in text:
                return False
            return True

        saved_fashion = [
            _format_saved(item)
            for item in saved_items
            if not _is_blocked_payload(item.name, item.category, item.department)
            and is_gender_match(item.name, item.category, item.department)
        ]

        if saved_fashion and not (occasion or goal):
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

    products = [
        p for p in products
        if is_fashion_product(p) and is_gender_match(p.name, p.category, p.department)
    ]

    scored = [
        (score_product(product, occasion=occasion, goal=goal, style=style), product)
        for product in products
    ]

    scored.sort(key=lambda item: item[0], reverse=True)

    # Pega nomes do closet para personalizar os motivos
    closet_names = []
    try:
        from models.customer_closet_item import CustomerClosetItem
        async with AsyncSessionLocal() as s2:
            r2 = await s2.execute(
                select(CustomerClosetItem.name)
                .where(CustomerClosetItem.email == email)
                .limit(20)
            )
            closet_names = [row[0] for row in r2.fetchall() if row[0]]
    except Exception:
        pass

    return [
        _format_product(
            product=product,
            score=score,
            occasion=occasion,
            goal=goal,
            style=style,
            closet_pieces=closet_names,
        )
        for score, product in scored[:limit]
    ]


async def _get_customer_profile(email: str, session) -> dict:
    """
    Infere perfil do cliente a partir do histórico de compras.
    Retorna: gênero dominante, tipos de produto comprados, cores favoritas.
    """
    from models.order_item import OrderItem
    from models.order import Order

    result = await session.execute(
        select(OrderItem.name, OrderItem.category, OrderItem.department)
        .join(Order, Order.order_id == OrderItem.order_id)
        .where(OrderItem.email == email)
        .limit(50)
    )
    rows = result.fetchall()

    text_all = " ".join([
        f"{r.name or ''} {r.category or ''} {r.department or ''}"
        for r in rows
    ]).lower()

    # Detecta gênero dominante
    fem_score = text_all.count("feminino") + text_all.count("sale feminino") + text_all.count("blusas femininas")
    masc_score = text_all.count("masculino") + text_all.count("sale masculino")
    inf_score = text_all.count("infantil") + text_all.count("kids")

    if fem_score >= masc_score and fem_score >= inf_score:
        dominant_gender = "feminino"
    elif masc_score > fem_score:
        dominant_gender = "masculino"
    else:
        dominant_gender = None  # sem histórico suficiente

    # Tipos de produto mais comprados (para não repetir o mesmo tipo nas recs)
    product_types = []
    type_keywords = {
        "maio": ["maiô", "maio"], "biquini": ["biquíni", "biquini"],
        "vestido": ["vestido"], "blusa": ["blusa"], "camisa": ["camisa", "camiseta"],
        "short": ["short", "bermuda"], "saia": ["saia"], "calca": ["calça", "calca"],
        "saida": ["saída", "saida"], "top": ["top", "cropped"],
    }
    for ptype, keywords in type_keywords.items():
        if any(kw in text_all for kw in keywords):
            product_types.append(ptype)

    return {
        "dominant_gender": dominant_gender,
        "owned_types": product_types,
        "total_orders": len(rows),
    }


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
    closet_pieces: list[str] | None = None,
) -> dict:
    url = clean_url(product.product_url)

    reason = build_reason(product, occasion=occasion, goal=goal, style=style, closet_pieces=closet_pieces)

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