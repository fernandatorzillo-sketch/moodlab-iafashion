import asyncio

print("1. arquivo sync_catalog_incremental carregado")

from models.catalog_product import CatalogProduct
from services.closet_db import AsyncSessionLocal, init_closet_db
from services.sync_control_service import mark_sync_error, mark_sync_success
from services.vtex_catalog_service import (
    fetch_product_and_sku_ids,
    fetch_product_by_id,
    fetch_sku_by_id,
    get_fashion_category_ids,
    fetch_category_map,
)

print("2. imports concluídos")

JOB_NAME = "catalog_incremental"


def extract_first_spec(product_data: dict, keys: list[str]) -> str | None:
    specs = product_data.get("SpecificationGroups") or []
    wanted = [k.lower() for k in keys]
    for group in specs:
        for field in group.get("Specifications", []) or []:
            name = str(field.get("Name") or "").strip().lower()
            # Substring match: "0- Gênero" contém "gênero" → match
            if any(name == w or w in name for w in wanted):
                values = field.get("Values") or []
                if values:
                    return str(values[0]).strip()
    return None


async def run() -> None:
    print("3. run iniciou")
    await init_closet_db()
    print("4. banco inicializado")

    async with AsyncSessionLocal() as session:
        print("5. sessão aberta")
        try:
            page_size = 100
            total_upserts = 0

            # Constrói mapa category_id → {name, department_name} da árvore VTEX
            print("5.0 construindo mapa de categorias VTEX...")
            category_map = fetch_category_map()
            print(f"5.0 category_map: {len(category_map)} categorias mapeadas")

            # Descobre departamentos de moda (exclui Casa, Lifestyle etc.)
            print("5.1 descobrindo categorias de moda...")
            fashion_category_ids = get_fashion_category_ids()
            if fashion_category_ids:
                print(f"5.2 categorias de moda: {fashion_category_ids}")
            else:
                print("5.2 sem filtro — sincronizando todas as categorias")
                fashion_category_ids = [None]

            print(f"6. início do loop | page_size={page_size}")

            for category_id in fashion_category_ids:
                cat_label = f"categoria={category_id}" if category_id else "todas"
                print(f"6.1 iniciando sync para {cat_label}")
                start = 0

                while True:
                    print(f"7. buscando faixa {cat_label}: {start} até {start + page_size - 1}")
                    payload = fetch_product_and_sku_ids(
                        start, start + page_size - 1, category_id=category_id
                    )
                    print("8. payload recebido")

                    data = payload.get("data") or {}
                    print(f"9. products na faixa: {len(data)}")

                    if not data:
                        print(f"10. sem dados para {cat_label}, próxima categoria")
                        break

                    for product_id, sku_ids in data.items():
                        try:
                            print(f"11. processando product_id={product_id}")
                            product = fetch_product_by_id(str(product_id))
                            print(f"12. product carregado | product_id={product_id}")

                            first_sku = None
                            sku_list = sku_ids or []
                            if sku_list:
                                print(f"13. sku principal | sku_id={sku_list[0]}")
                                first_sku = fetch_sku_by_id(str(sku_list[0]))
                                print(f"14. sku carregado | sku_id={sku_list[0]}")
                            else:
                                print(f"13. sem sku_list para product_id={product_id}")

                            row = await session.get(CatalogProduct, str(product_id))
                            if not row:
                                row = CatalogProduct(product_id=str(product_id))
                                session.add(row)
                                print(f"15. novo CatalogProduct | product_id={product_id}")
                            else:
                                print(f"15. CatalogProduct existente | product_id={product_id}")

                            row.ref_id  = str(product.get("RefId") or "") or None
                            row.sku_id  = str(first_sku.get("Id") or "") if first_sku else None
                            row.name    = product.get("Name")
                            row.brand   = product.get("BrandName")

                            # Departamento e categoria: fonte primária = spec "Departamento" (id=531)
                            # Fallback = category_map via DepartmentId/CategoryId
                            dept_id = int(product.get("DepartmentId") or 0)
                            cat_id  = int(product.get("CategoryId") or 0)
                            dept_entry = category_map.get(dept_id) or {}
                            cat_entry  = category_map.get(cat_id) or {}

                            dept_from_spec = extract_first_spec(product, ["departamento", "department"])
                            cat_from_spec  = extract_first_spec(product, ["tipo de produto", "tipo"])
                            dept_from_map  = dept_entry.get("name") or cat_entry.get("department_name") or None
                            cat_from_map   = cat_entry.get("name") or None

                            row.department   = dept_from_spec or dept_from_map or product.get("DepartmentName")
                            row.category     = cat_from_spec  or cat_from_map  or product.get("CategoryName")
                            row.product_type = extract_first_spec(product, ["tipo de produto", "tipo"])
                            row.occasion     = extract_first_spec(product, ["ocasião", "ocasiao"])
                            row.color        = extract_first_spec(product, ["cores", "cor"])
                            row.print_name   = extract_first_spec(product, ["estamparia"])
                            row.size         = extract_first_spec(product, ["tamanho"])
                            row.gender       = extract_first_spec(product, ["gênero", "genero"])
                            row.collection   = extract_first_spec(product, ["coleção", "colecao"])

                            row.image_url = (first_sku or {}).get("ImageUrl")

                            # LinkId é o slug limpo (sem sufixo de variação do SKU)
                            link_id    = str(product.get("LinkId") or "").strip()
                            detail_url = str(product.get("DetailUrl") or "").strip()
                            if link_id:
                                row.product_url = f"https://www.aguadecoco.com.br/{link_id}/p"
                            elif detail_url.startswith("/"):
                                row.product_url = "https://www.aguadecoco.com.br" + detail_url
                            elif detail_url.startswith("http"):
                                row.product_url = detail_url
                            else:
                                row.product_url = None

                            row.is_active = 1
                            row.raw_json  = {"product": product, "sku": first_sku}

                            total_upserts += 1
                            if total_upserts % 100 == 0:
                                print(f"16. checkpoint commit | total_upserts={total_upserts}")
                                await session.commit()

                        except Exception as item_error:
                            print(f"ERRO ao processar product_id={product_id}: {item_error}")

                    start += page_size
                    print(f"17. próxima faixa | start={start}")

            # Desativa produtos não-moda pelo nome
            print("18. desativando produtos não-moda...")
            from sqlalchemy import text as sql_text
            for pat in ["%bandeja%", "%castical%", "%difusor%", "%porta-retrato%",
                        "%guardanapo%", "%toalha de mesa%", "%corel sandi%",
                        "%caixa osso%", "%caixa geometrica%"]:
                await session.execute(
                    sql_text("UPDATE catalog_products SET is_active = 0 WHERE LOWER(name) LIKE :pat"),
                    {"pat": pat},
                )
            await session.commit()
            print("18.1 desativação concluída")

            await mark_sync_success(
                session=session,
                job_name=JOB_NAME,
                reference_value=str(total_upserts),
                notes=f"catalog_upserts={total_upserts}",
            )
            await session.commit()
            print(f"19. sync_catalog_incremental concluído: {total_upserts}")

        except Exception as e:
            print(f"ERRO GERAL: {e}")
            await session.rollback()
            await mark_sync_error(session, JOB_NAME, notes=str(e))
            await session.commit()
            raise


if __name__ == "__main__":
    asyncio.run(run())
