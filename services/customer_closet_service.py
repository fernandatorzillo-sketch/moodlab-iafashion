import asyncio
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from sqlalchemy import select, and_, or_, func, text
from sqlalchemy.ext.asyncio import AsyncSession

from models.clientes import Clientes
from models.produtos_empresa import Produtos_empresa
from models.pedidos import Pedidos
from models.itens_pedido import Itens_pedido
from models.closet_cliente import Closet_cliente
from models.brand_settings import Brand_settings
from models.brand_rules import Brand_rules
from models.curated_looks import Curated_looks
from services.aihub import AIHubService
from schemas.aihub import GenTxtRequest, ChatMessage

logger = logging.getLogger(__name__)

AI_TIMEOUT_SECONDS = 45


def row_to_dict(obj) -> dict:
    if obj is None:
        return {}
    return {c.name: getattr(obj, c.name) for c in obj.__table__.columns}


def sanitize_dict(d: dict) -> dict:
    """Sanitize datetime fields for JSON serialization."""
    for k, v in d.items():
        if isinstance(v, datetime):
            d[k] = v.isoformat()
    return d


class CustomerClosetService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def lookup_by_email(self, email: str) -> Dict[str, Any]:
        """Find customer by email and return closet data with full debug info.
        
        Uses multiple strategies to handle broken data relationships:
        - Strategy 1: Standard chain (email → cliente → pedidos.cliente_id → itens)
        - Strategy 2: numero_pedido bridge (email → cliente → pedidos → itens via numero_pedido)
        - Strategy 3: Direct email on pedidos.email_cliente if available
        """
        debug = {
            "email_input": email,
            "email_normalized": email.strip().lower(),
            "cliente_found": False,
            "pedidos_count": 0,
            "itens_pedido_count": 0,
            "itens_with_produto_id": 0,
            "itens_with_sku_only": 0,
            "produtos_by_id": 0,
            "produtos_by_sku": 0,
            "closet_entries_existing": 0,
            "closet_final_count": 0,
            "strategy_used": "none",
            "messages": [],
        }

        normalized_email = email.strip().lower()

        # 1. Find customer by email — handle duplicates by picking the cleanest record
        stmt = select(Clientes).where(
            func.lower(func.trim(Clientes.email)) == normalized_email
        )
        result = await self.db.execute(stmt)
        all_clients = result.scalars().all()

        # Also search in corrupted nome field (tab-separated data with email)
        if not all_clients:
            stmt2 = select(Clientes).where(
                func.lower(Clientes.nome).contains(normalized_email)
            )
            result2 = await self.db.execute(stmt2)
            all_clients = result2.scalars().all()
            if all_clients:
                debug["messages"].append(f"Cliente encontrado via campo nome corrompido ({len(all_clients)} registro(s))")

        if not all_clients:
            debug["messages"].append(f"Nenhum cliente encontrado com email: {normalized_email}")
            logger.warning(f"Customer lookup: no client found for email '{normalized_email}'")
            return {"found": False, "message": "Email não encontrado", "debug": debug}

        # Pick the best client record (prefer one with clean email field)
        cliente = None
        for c in all_clients:
            if c.email and c.email.strip().lower() == normalized_email:
                if not cliente or (c.nome and '\t' not in c.nome):
                    cliente = c
        if not cliente:
            cliente = all_clients[0]

        debug["cliente_found"] = True
        cliente_data = sanitize_dict(row_to_dict(cliente))
        empresa_id = cliente.empresa_id
        user_id = cliente.user_id
        cliente_id = cliente.id
        debug["messages"].append(f"Cliente encontrado: {cliente.nome} (ID: {cliente_id}, empresa: {empresa_id})")
        logger.info(f"Customer lookup: found client '{cliente.nome}' (ID={cliente_id}, empresa={empresa_id})")

        # 2. Get ALL orders for this customer — try multiple strategies
        items: list = []
        orders: list = []

        # Strategy 1: Standard — pedidos.cliente_id = cliente.id
        orders_stmt = select(Pedidos).where(
            and_(
                Pedidos.empresa_id == empresa_id,
                Pedidos.cliente_id == cliente_id,
                Pedidos.user_id == user_id,
            )
        )
        orders_result = await self.db.execute(orders_stmt)
        orders = list(orders_result.scalars().all())

        if orders:
            debug["strategy_used"] = "cliente_id"
            debug["messages"].append(f"Estratégia 1 (cliente_id): {len(orders)} pedido(s)")
        else:
            debug["messages"].append("Estratégia 1 (cliente_id): nenhum pedido encontrado")

        # Strategy 2: Try pedidos.email_cliente via raw SQL (column added via ALTER TABLE, not in ORM)
        if not orders:
            try:
                email_sql = text(
                    "SELECT id FROM pedidos WHERE empresa_id = :eid AND user_id = :uid "
                    "AND LOWER(TRIM(email_cliente)) = :email"
                )
                email_result = await self.db.execute(
                    email_sql, {"eid": empresa_id, "uid": user_id, "email": normalized_email}
                )
                matched_ids = [row[0] for row in email_result.fetchall()]
                if matched_ids:
                    orders_by_email_stmt = select(Pedidos).where(Pedidos.id.in_(matched_ids))
                    orders_by_email_result = await self.db.execute(orders_by_email_stmt)
                    orders = list(orders_by_email_result.scalars().all())
                    debug["strategy_used"] = "email_cliente"
                    debug["messages"].append(f"Estratégia 2 (email_cliente): {len(orders)} pedido(s)")
                else:
                    debug["messages"].append("Estratégia 2 (email_cliente): nenhum pedido encontrado")
            except Exception as e:
                debug["messages"].append(f"Estratégia 2 (email_cliente): {str(e)[:80]}")

        # Strategy 3: Get ALL pedidos for this empresa/user and match via numero_pedido
        # This handles the case where pedidos have no cliente_id but we can infer from import patterns
        if not orders:
            all_orders_stmt = select(Pedidos).where(
                and_(
                    Pedidos.empresa_id == empresa_id,
                    Pedidos.user_id == user_id,
                )
            )
            all_orders_result = await self.db.execute(all_orders_stmt)
            all_orders = list(all_orders_result.scalars().all())
            
            if all_orders:
                # Check if any corrupted client records contain numero_pedido hints
                # e.g., nome="222\tFernanda Torzillo\tfernanda@..." means pedido 222 belongs to Fernanda
                for c in all_clients:
                    if c.nome and '\t' in c.nome:
                        parts = c.nome.split('\t')
                        possible_numero = parts[0].strip()
                        for o in all_orders:
                            if str(o.numero_pedido) == possible_numero:
                                if o not in orders:
                                    orders.append(o)

                if orders:
                    debug["strategy_used"] = "corrupted_nome_match"
                    debug["messages"].append(f"Estratégia 3 (nome corrompido): {len(orders)} pedido(s) vinculado(s)")
                else:
                    # Last resort: if there's only one client email, assign all unlinked orders
                    unlinked = [o for o in all_orders if o.cliente_id is None]
                    if unlinked and len(all_clients) == 1:
                        orders = unlinked
                        debug["strategy_used"] = "unlinked_fallback"
                        debug["messages"].append(f"Estratégia 3 (fallback): {len(orders)} pedido(s) sem cliente atribuído")

        debug["pedidos_count"] = len(orders)
        if not orders:
            debug["messages"].append("Nenhum pedido encontrado por nenhuma estratégia")

        # 3. Get order items — handle broken pedido_id references
        order_ids = [o.id for o in orders]
        numero_pedidos = [str(o.numero_pedido) for o in orders if o.numero_pedido]

        if order_ids or numero_pedidos:
            # Try matching itens_pedido.pedido_id against BOTH internal IDs and numero_pedido
            conditions = []
            if order_ids:
                conditions.append(Itens_pedido.pedido_id.in_(order_ids))
            
            # Also match against numero_pedido as integer (common data corruption pattern)
            numero_as_ints = []
            for np in numero_pedidos:
                try:
                    numero_as_ints.append(int(np))
                except (ValueError, TypeError):
                    pass
            
            if numero_as_ints:
                conditions.append(Itens_pedido.pedido_id.in_(numero_as_ints))

            if conditions:
                items_stmt = select(Itens_pedido).where(
                    and_(
                        or_(*conditions),
                        Itens_pedido.user_id == user_id,
                    )
                )
                items_result = await self.db.execute(items_stmt)
                items = list(items_result.scalars().all())

        debug["itens_pedido_count"] = len(items)
        if items:
            debug["messages"].append(f"{len(items)} item(ns) de pedido encontrado(s)")
        else:
            debug["messages"].append("Nenhum item de pedido encontrado")
        logger.info(f"Customer lookup: {len(items)} order items for client {cliente_id}")

        # 4. Resolve products: by produto_id AND by SKU fallback
        produto_ids_from_items: set = set()
        skus_from_items: list = []

        for item in items:
            if item.produto_id:
                produto_ids_from_items.add(item.produto_id)
            if item.sku:
                skus_from_items.append(str(item.sku).strip())

        debug["itens_with_produto_id"] = len(produto_ids_from_items)
        debug["itens_with_sku_only"] = len([i for i in items if not i.produto_id and i.sku])

        # 4a. Fetch products by ID
        all_product_ids = set()
        closet_products: list = []

        if produto_ids_from_items:
            prods_stmt = select(Produtos_empresa).where(
                Produtos_empresa.id.in_(list(produto_ids_from_items))
            )
            prods_result = await self.db.execute(prods_stmt)
            products_by_id = list(prods_result.scalars().all())
            debug["produtos_by_id"] = len(products_by_id)
            debug["messages"].append(f"{len(products_by_id)} produto(s) vinculado(s) por ID")
            for p in products_by_id:
                if p.id not in all_product_ids:
                    all_product_ids.add(p.id)
                    closet_products.append(sanitize_dict(row_to_dict(p)))

        # 4b. Fetch products by SKU (for items without produto_id or as additional match)
        if skus_from_items:
            unique_skus = list(set(skus_from_items))
            sku_stmt = select(Produtos_empresa).where(
                and_(
                    Produtos_empresa.empresa_id == empresa_id,
                    Produtos_empresa.user_id == user_id,
                    func.trim(Produtos_empresa.sku).in_(unique_skus),
                )
            )
            sku_result = await self.db.execute(sku_stmt)
            products_by_sku = list(sku_result.scalars().all())
            new_by_sku = 0
            for p in products_by_sku:
                if p.id not in all_product_ids:
                    all_product_ids.add(p.id)
                    closet_products.append(sanitize_dict(row_to_dict(p)))
                    new_by_sku += 1
            debug["produtos_by_sku"] = new_by_sku
            if new_by_sku:
                debug["messages"].append(f"{new_by_sku} produto(s) adicional(is) vinculado(s) por SKU")

        # 5. Also check existing closet_cliente entries
        closet_stmt = select(Closet_cliente).where(
            and_(
                Closet_cliente.empresa_id == empresa_id,
                Closet_cliente.cliente_id == cliente_id,
                Closet_cliente.user_id == user_id,
            )
        )
        closet_result = await self.db.execute(closet_stmt)
        closet_entries = closet_result.scalars().all()
        debug["closet_entries_existing"] = len(closet_entries)

        if closet_entries:
            debug["messages"].append(f"{len(closet_entries)} entrada(s) existente(s) no closet_cliente")
            extra_ids = set(e.produto_id for e in closet_entries) - all_product_ids
            if extra_ids:
                extra_stmt = select(Produtos_empresa).where(
                    Produtos_empresa.id.in_(list(extra_ids))
                )
                extra_result = await self.db.execute(extra_stmt)
                for p in extra_result.scalars().all():
                    if p.id not in all_product_ids:
                        all_product_ids.add(p.id)
                        closet_products.append(sanitize_dict(row_to_dict(p)))

        debug["closet_final_count"] = len(closet_products)
        debug["messages"].append(f"Closet montado com {len(closet_products)} peça(s)")
        logger.info(f"Customer lookup: closet built with {len(closet_products)} items for client {cliente_id}")

        # Sanitize orders
        orders_data = [sanitize_dict(row_to_dict(o)) for o in orders]

        return {
            "found": True,
            "cliente": cliente_data,
            "empresa_id": empresa_id,
            "user_id": user_id,
            "closet_products": closet_products,
            "orders": orders_data,
            "total_orders": len(orders),
            "total_items": len(closet_products),
            "debug": debug,
        }

    async def get_recommendations_for_customer(
        self, email: str, ocasiao: Optional[str] = None, limit: int = 6,
    ) -> Dict[str, Any]:
        """Generate AI recommendations for a customer. Works even with empty closet."""
        lookup = await self.lookup_by_email(email)
        if not lookup.get("found"):
            return {"error": "Cliente não encontrado", "debug": lookup.get("debug", {})}

        empresa_id = lookup["empresa_id"]
        user_id = lookup["user_id"]
        cliente = lookup["cliente"]
        closet_products = lookup["closet_products"]
        debug_info = lookup.get("debug", {})

        # Get brand settings
        brand_stmt = select(Brand_settings).where(
            and_(Brand_settings.empresa_id == empresa_id, Brand_settings.user_id == user_id)
        )
        brand_result = await self.db.execute(brand_stmt)
        brand = brand_result.scalar_one_or_none()

        # Get brand rules
        rules_stmt = select(Brand_rules).where(
            and_(Brand_rules.empresa_id == empresa_id, Brand_rules.user_id == user_id, Brand_rules.ativo == True)
        )
        rules_result = await self.db.execute(rules_stmt)
        rules = rules_result.scalars().all()

        # Get catalog products (in stock, active)
        catalog_stmt = (
            select(Produtos_empresa)
            .where(and_(
                Produtos_empresa.empresa_id == empresa_id,
                Produtos_empresa.user_id == user_id,
                or_(Produtos_empresa.estoque.is_(None), Produtos_empresa.estoque > 0),
                or_(Produtos_empresa.ativo.is_(None), Produtos_empresa.ativo == True),
            ))
            .limit(40)
        )
        catalog_result = await self.db.execute(catalog_stmt)
        catalog_products = [row_to_dict(p) for p in catalog_result.scalars().all()]

        if not catalog_products:
            logger.warning(f"No catalog products for empresa {empresa_id}")
            return {
                "cliente_nome": cliente.get("nome", ""),
                "recommendations": [],
                "perfil_estilo": "Catálogo vazio",
                "dicas_estilo": ["O catálogo da marca ainda não possui produtos disponíveis."],
                "total_closet": len(closet_products),
                "total_catalog": 0,
                "debug": debug_info,
            }

        # Get curated looks
        looks_conditions = [
            Curated_looks.empresa_id == empresa_id,
            Curated_looks.user_id == user_id,
            Curated_looks.ativo == True,
        ]
        if ocasiao:
            looks_conditions.append(Curated_looks.ocasiao.ilike(f"%{ocasiao}%"))
        looks_stmt = select(Curated_looks).where(and_(*looks_conditions)).limit(5)
        looks_result = await self.db.execute(looks_stmt)
        curated_looks = [row_to_dict(l) for l in looks_result.scalars().all()]

        # Analyze closet preferences
        categories: Dict[str, int] = {}
        colors: Dict[str, int] = {}
        styles: set = set()
        for p in closet_products:
            cat = p.get("categoria", "")
            if cat:
                categories[cat] = categories.get(cat, 0) + 1
            cor = p.get("cor", "")
            if cor:
                colors[cor] = colors.get(cor, 0) + 1
            tags = p.get("tags_estilo", "")
            if tags:
                for tag in str(tags).split(","):
                    t = tag.strip()
                    if t:
                        styles.add(t)

        aesthetic = brand.aesthetic_description if brand and brand.aesthetic_description else "Moda contemporânea"
        tone = brand.tone_of_voice if brand and brand.tone_of_voice else "Sofisticado e acolhedor"
        rules_text = "\n".join([
            f"- {r.rule_type}: {r.rule_value}" for r in rules
        ]) if rules else "Sem regras específicas."

        # Build compact catalog summary (limit to 20 items for speed)
        catalog_for_prompt = catalog_products[:20]
        catalog_summary = json.dumps([
            {"id": p["id"], "nome": p.get("nome", ""), "categoria": p.get("categoria", ""),
             "cor": p.get("cor", ""), "preco": p.get("preco"), "ocasiao": p.get("ocasiao", ""),
             "tags_estilo": p.get("tags_estilo", "")}
            for p in catalog_for_prompt
        ], ensure_ascii=False)

        # Build closet context (compact)
        closet_context = ""
        if closet_products:
            closet_summary = json.dumps([
                {"nome": p.get("nome", ""), "categoria": p.get("categoria", ""), "cor": p.get("cor", "")}
                for p in closet_products[:15]
            ], ensure_ascii=False)
            closet_context = f"""
PEÇAS NO CLOSET ({len(closet_products)} itens):
{closet_summary}

CATEGORIAS PREFERIDAS: {json.dumps(categories, ensure_ascii=False)}
CORES PREFERIDAS: {json.dumps(colors, ensure_ascii=False)}
ESTILOS: {', '.join(styles) if styles else 'N/A'}
"""
        else:
            closet_context = """
CLOSET: Vazio (cliente novo ou sem histórico de compras).
Recomende peças versáteis e populares do catálogo que combinem com o perfil da marca.
"""

        curated_text = ""
        if curated_looks:
            curated_text = "LOOKS CURADOS: " + json.dumps([
                {"nome": l.get("nome", ""), "ocasiao": l.get("ocasiao", "")}
                for l in curated_looks[:5]
            ], ensure_ascii=False)

        prompt = f"""Gere {limit} recomendações de produtos do catálogo abaixo.

CLIENTE: {cliente.get('nome', 'N/A')}
ESTILO: {cliente.get('estilo_resumo', 'N/A')}
TAMANHOS: Top {cliente.get('tamanho_top', 'N/A')}, Bottom {cliente.get('tamanho_bottom', 'N/A')}
{closet_context}
MARCA: {aesthetic}
TOM: {tone}
OCASIÃO: {ocasiao or 'Geral'}
REGRAS: {rules_text}
{curated_text}

CATÁLOGO DISPONÍVEL:
{catalog_summary}

Responda APENAS em JSON:
{{"recommendations":[{{"produto_id":<int>,"nome":"<str>","motivo":"<str>","score":<0-1>,"combina_com":["<str>"]}}],"perfil_estilo":"<str>","dicas_estilo":["<str>"]}}"""

        ai_result = None
        try:
            ai_service = AIHubService()
            request = GenTxtRequest(
                messages=[
                    ChatMessage(role="system", content="Estilista de moda. Responda em JSON válido. Seja conciso."),
                    ChatMessage(role="user", content=prompt),
                ],
                model="deepseek-v3.2",
            )

            # Apply timeout to prevent hanging
            response = await asyncio.wait_for(
                ai_service.gentxt(request),
                timeout=AI_TIMEOUT_SECONDS,
            )
            ai_text = response.content
            logger.info(f"AI response received ({len(ai_text)} chars)")

            json_start = ai_text.find("{")
            json_end = ai_text.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                ai_result = json.loads(ai_text[json_start:json_end])
            else:
                logger.error(f"AI response not valid JSON: {ai_text[:200]}")

        except asyncio.TimeoutError:
            logger.error(f"AI recommendation timed out after {AI_TIMEOUT_SECONDS}s")
        except Exception as e:
            logger.error(f"AI recommendation error: {type(e).__name__}: {e}")

        # Fallback if AI failed
        if not ai_result or not ai_result.get("recommendations"):
            closet_ids = set(p["id"] for p in closet_products)
            fallback_products = [p for p in catalog_products if p["id"] not in closet_ids][:limit]
            if not fallback_products:
                fallback_products = catalog_products[:limit]
            ai_result = {
                "recommendations": [
                    {
                        "produto_id": p["id"],
                        "nome": p.get("nome", "Produto"),
                        "motivo": "Selecionado do catálogo da marca para você",
                        "score": 0.5,
                        "combina_com": [],
                    }
                    for p in fallback_products
                ],
                "perfil_estilo": cliente.get("estilo_resumo", "Em análise"),
                "dicas_estilo": ["Explore o catálogo para descobrir peças que combinam com seu estilo."],
            }
            logger.info(f"Using fallback recommendations ({len(fallback_products)} items)")

        # Enrich recommendations with catalog data
        recs = ai_result.get("recommendations", [])
        catalog_map = {p["id"]: p for p in catalog_products}
        enriched_recs = []
        for rec in recs:
            pid = rec.get("produto_id")
            if pid and pid in catalog_map:
                prod = catalog_map[pid]
                rec["link_produto"] = prod.get("link_produto", "")
                rec["imagem_url"] = prod.get("imagem_url", "")
                rec["preco"] = prod.get("preco")
                rec["categoria"] = prod.get("categoria", "")
                rec["cor"] = prod.get("cor", "")
            enriched_recs.append(rec)

        return {
            "cliente_nome": cliente.get("nome", ""),
            "recommendations": enriched_recs,
            "perfil_estilo": ai_result.get("perfil_estilo", ""),
            "dicas_estilo": ai_result.get("dicas_estilo", []),
            "total_closet": len(closet_products),
            "total_catalog": len(catalog_products),
            "debug": debug_info,
        }