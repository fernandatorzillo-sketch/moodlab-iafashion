import asyncio
from collections import defaultdict

from sqlalchemy import delete, select

from models.catalog_product import CatalogProduct
from models.customer_closet_item import CustomerClosetItem
from models.customer_questionnaire_answer import CustomerQuestionnaireAnswer
from models.customer_recommendation import CustomerRecommendation
from models.inventory_by_sku import InventoryBySku
from services.closet_db import AsyncSessionLocal, init_closet_db
from services.sync_control_service import mark_sync_error, mark_sync_success

JOB_NAME = "rebuild_recommendations"


def normalize(value):
    return str(value or "").strip().lower()


def safe_text(value):
    return str(value or "").strip()


def text_contains_any(value: str, options: list[str]) -> bool:
    value_norm = normalize(value)
    return any(opt in value_norm for opt in options if opt)


def get_complementary_targets(category: str, department: str, product_type: str) -> list[str]:
    """
    Retorna categorias/departamentos/tipos complementares para ajudar no cross sell.
    A lógica é simples, mas já cria recomendações mais coerentes.
    """
    cat = normalize(category)
    dept = normalize(department)
    ptype = normalize(product_type)

    source = " ".join([cat, dept, ptype])

    rules = {
        "biquini_top": [
            "calcinha", "bottom", "saida", "acessorio", "acessório", "praia",
        ],
        "biquini_bottom": [
            "sutia", "sutiã", "top", "saida", "acessorio", "acessório", "praia",
        ],
        "maio": [
            "saida", "acessorio", "acessório", "praia",
        ],
        "saida_praia": [
            "biquini", "maiô", "maio", "acessorio", "acessório", "praia",
        ],
        "vestido": [
            "acessorio", "acessório", "calcado", "calçado", "sandalia", "sandália", "bolsa",
        ],
        "camisa": [
            "calca", "calça", "short", "saia", "top", "blusa",
        ],
        "blusa": [
            "calca", "calça", "short", "saia",
        ],
        "top": [
            "calca", "calça", "short", "saia",
        ],
        "calca": [
            "camisa", "blusa", "top",
        ],
        "short": [
            "camisa", "blusa", "top",
        ],
        "saia": [
            "camisa", "blusa", "top",
        ],
    }

    matched_keys = []

    if text_contains_any(source, ["sutia", "sutiã", "top", "cortininha"]):
        matched_keys.append("biquini_top")
    if text_contains_any(source, ["calcinha", "bottom"]):
        matched_keys.append("biquini_bottom")
    if text_contains_any(source, ["maiô", "maio"]):
        matched_keys.append("maio")
    if text_contains_any(source, ["saida", "saída"]):
        matched_keys.append("saida_praia")
    if text_contains_any(source, ["vestido"]):
        matched_keys.append("vestido")
    if text_contains_any(source, ["camisa"]):
        matched_keys.append("camisa")
    if text_contains_any(source, ["blusa"]):
        matched_keys.append("blusa")
    if text_contains_any(source, ["top"]):
        matched_keys.append("top")
    if text_contains_any(source, ["calca", "calça"]):
        matched_keys.append("calca")
    if text_contains_any(source, ["short"]):
        matched_keys.append("short")
    if text_contains_any(source, ["saia"]):
        matched_keys.append("saia")

    result = []
    for key in matched_keys:
        result.extend(rules.get(key, []))

    return list(set(result))


def derive_style_tags(product: CatalogProduct) -> set[str]:
    """
    Cria tags simples de estilo com base nos campos já existentes.
    """
    tags = set()

    joined = " ".join(
        [
            normalize(product.name),
            normalize(product.category),
            normalize(product.department),
            normalize(product.product_type),
            normalize(product.occasion),
            normalize(product.collection),
        ]
    )

    if text_contains_any(joined, ["elegante", "sofistic", "alfaiat", "resort", "premium"]):
        tags.add("elegante")
        tags.add("sofisticado")

    if text_contains_any(joined, ["casual", "leve", "dia a dia", "dia_a_dia", "conforto"]):
        tags.add("casual")
        tags.add("leve")

    if text_contains_any(joined, ["praia", "beach", "biquini", "maiô", "maio", "saida", "saída"]):
        tags.add("leve")

    return tags


def build_reason(goal: str, occasion: str, style: str, product: CatalogProduct, reason_mode: str) -> str:
    """
    reason_mode:
      - complementary
      - elevated
      - affinity
      - occasion
      - newness
    """
    category = safe_text(product.category)
    dept = safe_text(product.department)
    occasion_txt = safe_text(product.occasion)

    parts = []

    if goal == "cross_sell":
        if reason_mode == "complementary":
            parts.append("Essa peça entra como complemento natural para ampliar as combinações do seu closet.")
        else:
            parts.append("Escolhi essa sugestão para complementar melhor as peças que você já tem.")
    elif goal == "up_sell":
        if reason_mode == "elevated":
            parts.append("Essa opção tem uma proposta mais sofisticada para elevar seus looks.")
        else:
            parts.append("Separei uma peça com mais potencial de elevar a percepção do look.")
    else:
        if reason_mode == "newness":
            parts.append("Essa peça traz novidade com aderência ao seu histórico de compras.")
        else:
            parts.append("Essa sugestão conversa bem com o seu estilo e com o que você já compra.")

    if occasion:
        parts.append(f"Ela faz sentido para momentos de {occasion}.")
    elif occasion_txt:
        parts.append(f"Ela se encaixa bem em ocasiões ligadas a {occasion_txt}.")

    if style:
        parts.append(f"O visual dela se aproxima de um estilo {style}.")
    else:
        product_style_tags = derive_style_tags(product)
        if product_style_tags:
            tags_txt = ", ".join(sorted(product_style_tags))
            parts.append(f"Ela traz uma leitura de estilo mais {tags_txt}.")

    if category:
        parts.append(f"Categoria: {category}.")
    elif dept:
        parts.append(f"Departamento: {dept}.")

    return " ".join(parts)


def score_candidate(
    product: CatalogProduct,
    owned_categories: set[str],
    owned_departments: set[str],
    owned_brands: set[str],
    owned_complement_targets: set[str],
    goal: str,
    occasion: str,
    style: str,
) -> tuple[float, str, str]:
    """
    Retorna:
      score, rec_type, reason_mode
    """
    score = 0.0
    rec_type = "new_in"
    reason_mode = "affinity"

    product_category = normalize(product.category)
    product_department = normalize(product.department)
    product_brand = normalize(product.brand)
    product_occasion = normalize(product.occasion)
    product_type = normalize(product.product_type)
    product_name = normalize(product.name)

    product_style_tags = derive_style_tags(product)

    # Afinidade base
    if product_category and product_category in owned_categories:
        score += 4

    if product_department and product_department in owned_departments:
        score += 3

    if product_brand and product_brand in owned_brands:
        score += 1

    # Ocasião
    if occasion:
        if occasion == product_occasion:
            score += 6
            reason_mode = "occasion"
        elif occasion in f"{product_occasion} {product_type} {product_name}":
            score += 4
            reason_mode = "occasion"

    # Estilo
    if style:
        style_norm = normalize(style)
        if style_norm in product_style_tags:
            score += 4
        elif style_norm in f"{product_type} {product_name} {product_category}":
            score += 2

    # Goal específico
    if goal == "cross_sell":
        rec_type = "cross_sell"

        product_joined = " ".join([product_category, product_department, product_type, product_name])
        if any(target in product_joined for target in owned_complement_targets):
            score += 8
            reason_mode = "complementary"
        elif product_department and product_department in owned_departments:
            score += 3
            reason_mode = "complementary"
        else:
            score += 1

    elif goal == "up_sell":
        rec_type = "up_sell"

        if any(tag in derive_style_tags(product) for tag in {"elegante", "sofisticado"}):
            score += 6
            reason_mode = "elevated"

        if text_contains_any(product_name, ["resort", "premium", "bordado", "luxo", "elegante"]):
            score += 3
            reason_mode = "elevated"

        if text_contains_any(product_category, ["vestido", "camisa", "saida", "saída"]):
            score += 2

    else:
        rec_type = "new_in"
        score += 2
        reason_mode = "newness" if occasion or style else "affinity"

    return score, rec_type, reason_mode


async def run() -> None:
    await init_closet_db()

    async with AsyncSessionLocal() as session:
        try:
            print("1. Limpando recomendações antigas...")
            await session.execute(delete(CustomerRecommendation))

            print("2. Lendo estoque...")
            inventory_result = await session.execute(select(InventoryBySku))
            inventory_rows = inventory_result.scalars().all()

            available_skus = {
                row.sku_id
                for row in inventory_rows
                if int(row.quantity or 0) > 0 and int(row.is_available or 0) == 1
            }
            print(f"2.1. SKUs disponíveis: {len(available_skus)}")

            print("3. Lendo catálogo ativo...")
            catalog_result = await session.execute(
                select(CatalogProduct).where(CatalogProduct.is_active == 1)
            )
            catalog_rows = catalog_result.scalars().all()
            print(f"3.1. Produtos ativos no catálogo: {len(catalog_rows)}")

            print("4. Lendo closet dos clientes...")
            closet_result = await session.execute(select(CustomerClosetItem))
            closet_rows = closet_result.scalars().all()
            print(f"4.1. Itens de closet: {len(closet_rows)}")

            print("5. Lendo respostas do questionário...")
            answers_result = await session.execute(select(CustomerQuestionnaireAnswer))
            answers_rows = answers_result.scalars().all()
            answers_map = {row.email: row for row in answers_rows}
            print(f"5.1. Clientes com respostas: {len(answers_map)}")

            closet_by_email = defaultdict(list)
            for row in closet_rows:
                closet_by_email[row.email].append(row)

            inserted = 0

            print(f"6. Gerando recomendações para {len(closet_by_email)} clientes...")

            for email, closet_items in closet_by_email.items():
                owned_skus = {normalize(item.sku_id) for item in closet_items if item.sku_id}
                owned_categories = {normalize(item.category) for item in closet_items if item.category}
                owned_departments = {normalize(item.department) for item in closet_items if item.department}
                owned_brands = {normalize(item.brand) for item in closet_items if item.brand}

                owned_complement_targets = set()
                for item in closet_items:
                    owned_complement_targets.update(
                        get_complementary_targets(
                            category=safe_text(item.category),
                            department=safe_text(item.department),
                            product_type=safe_text(getattr(item, "product_type", "")),
                        )
                    )

                answers = answers_map.get(email)
                goal = normalize(answers.goal if answers else "")
                occasion = normalize(answers.occasion if answers else "")
                style = normalize(answers.style if answers else "")

                candidates = []

                for product in catalog_rows:
                    sku_norm = normalize(product.sku_id)
                    if not sku_norm or sku_norm in owned_skus:
                        continue

                    if product.sku_id not in available_skus:
                        continue

                    score, rec_type, reason_mode = score_candidate(
                        product=product,
                        owned_categories=owned_categories,
                        owned_departments=owned_departments,
                        owned_brands=owned_brands,
                        owned_complement_targets=owned_complement_targets,
                        goal=goal,
                        occasion=occasion,
                        style=style,
                    )

                    if score <= 0:
                        continue

                    candidates.append((score, rec_type, reason_mode, product))

                # Ordena por score desc
                candidates.sort(key=lambda x: x[0], reverse=True)

                # Diversifica o mix final
                diversified = []
                category_count = defaultdict(int)
                department_count = defaultdict(int)

                for score, rec_type, reason_mode, product in candidates:
                    cat = normalize(product.category)
                    dept = normalize(product.department)

                    if cat and category_count[cat] >= 3:
                        continue

                    if dept and department_count[dept] >= 6:
                        continue

                    diversified.append((score, rec_type, reason_mode, product))
                    if cat:
                        category_count[cat] += 1
                    if dept:
                        department_count[dept] += 1

                    if len(diversified) >= 12:
                        break

                for score, rec_type, reason_mode, product in diversified:
                    session.add(
                        CustomerRecommendation(
                            email=email,
                            sku_id=product.sku_id,
                            product_id=product.product_id,
                            ref_id=product.ref_id,
                            name=product.name,
                            category=product.category,
                            department=product.department,
                            image_url=product.image_url,
                            product_url=product.product_url,
                            reason=build_reason(goal, occasion, style, product, reason_mode),
                            recommendation_type=rec_type,
                            score=float(score),
                        )
                    )
                    inserted += 1

                if inserted > 0 and inserted % 200 == 0:
                    print(f"Checkpoint parcial de recomendações: {inserted}")
                    await session.commit()

            print(f"7. Marcando sucesso. Total inserido: {inserted}")
            await mark_sync_success(
                session=session,
                job_name=JOB_NAME,
                reference_value=str(inserted),
                notes=f"recommendations={inserted}",
            )
            await session.commit()

            print(f"rebuild_recommendations concluído: {inserted}")

        except Exception as e:
            print(f"ERRO no rebuild_recommendations: {e}")
            await session.rollback()
            await mark_sync_error(session, JOB_NAME, notes=str(e))
            await session.commit()
            raise


if __name__ == "__main__":
    asyncio.run(run())