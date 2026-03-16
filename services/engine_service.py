import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from sqlalchemy import select, and_, or_, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from models.produtos_empresa import Produtos_empresa
from models.clientes import Clientes
from models.closet_cliente import Closet_cliente
from models.pedidos import Pedidos
from models.itens_pedido import Itens_pedido
from models.curated_looks import Curated_looks
from models.curated_look_items import Curated_look_items
from models.brand_rules import Brand_rules
from models.brand_settings import Brand_settings
from models.recommendation_logs import Recommendation_logs
from services.aihub import AIHubService
from schemas.aihub import GenTxtRequest, ChatMessage

logger = logging.getLogger(__name__)


def row_to_dict(obj) -> dict:
    """Convert SQLAlchemy model to dict"""
    if obj is None:
        return {}
    return {c.name: getattr(obj, c.name) for c in obj.__table__.columns}


class EngineService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def search_products(
        self, empresa_id: int, user_id: str,
        query: str = "", categoria: str = "", ocasiao: str = "",
        tags: str = "", limit: int = 20, skip: int = 0,
    ) -> Dict[str, Any]:
        """Search products by text, category, occasion, tags"""
        conditions = [
            Produtos_empresa.empresa_id == empresa_id,
            Produtos_empresa.user_id == user_id,
        ]

        if query:
            search = f"%{query}%"
            conditions.append(
                or_(
                    Produtos_empresa.nome.ilike(search),
                    Produtos_empresa.sku.ilike(search),
                    Produtos_empresa.tags_estilo.ilike(search),
                    Produtos_empresa.cor.ilike(search),
                )
            )
        if categoria:
            conditions.append(Produtos_empresa.categoria.ilike(f"%{categoria}%"))
        if ocasiao:
            conditions.append(Produtos_empresa.ocasiao.ilike(f"%{ocasiao}%"))
        if tags:
            for tag in tags.split(","):
                conditions.append(Produtos_empresa.tags_estilo.ilike(f"%{tag.strip()}%"))

        # Count
        count_stmt = select(func.count()).select_from(Produtos_empresa).where(and_(*conditions))
        count_result = await self.db.execute(count_stmt)
        total = count_result.scalar() or 0

        # Fetch
        stmt = (
            select(Produtos_empresa)
            .where(and_(*conditions))
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        products = [row_to_dict(p) for p in result.scalars().all()]

        return {"items": products, "total": total, "skip": skip, "limit": limit}

    async def get_customer_closet(
        self, empresa_id: int, cliente_id: int, user_id: str,
    ) -> Dict[str, Any]:
        """Get customer closet with full product details"""
        stmt = select(Closet_cliente).where(
            and_(
                Closet_cliente.empresa_id == empresa_id,
                Closet_cliente.cliente_id == cliente_id,
                Closet_cliente.user_id == user_id,
            )
        )
        result = await self.db.execute(stmt)
        closet_entries = result.scalars().all()

        items = []
        for entry in closet_entries:
            prod_stmt = select(Produtos_empresa).where(Produtos_empresa.id == entry.produto_id)
            prod_result = await self.db.execute(prod_stmt)
            product = prod_result.scalar_one_or_none()
            items.append({
                "closet_id": entry.id,
                "produto_id": entry.produto_id,
                "origem": entry.origem,
                "data_entrada": str(entry.data_entrada) if entry.data_entrada else None,
                "produto": row_to_dict(product) if product else None,
            })

        # Get client info
        client_stmt = select(Clientes).where(
            and_(Clientes.id == cliente_id, Clientes.user_id == user_id)
        )
        client_result = await self.db.execute(client_stmt)
        client = client_result.scalar_one_or_none()

        return {
            "cliente": row_to_dict(client) if client else {},
            "closet_items": items,
            "total": len(items),
        }

    async def generate_recommendations(
        self, empresa_id: int, user_id: str,
        cliente_id: Optional[int] = None, ocasiao: Optional[str] = None,
        limit: int = 5,
    ) -> Dict[str, Any]:
        """Hybrid AI recommendations combining catalog, closet, curation, rules"""

        # 1. Get brand settings & aesthetic
        brand_stmt = select(Brand_settings).where(
            and_(Brand_settings.empresa_id == empresa_id, Brand_settings.user_id == user_id)
        )
        brand_result = await self.db.execute(brand_stmt)
        brand = brand_result.scalar_one_or_none()

        # 2. Get brand rules
        rules_stmt = select(Brand_rules).where(
            and_(Brand_rules.empresa_id == empresa_id, Brand_rules.user_id == user_id, Brand_rules.ativo == True)
        )
        rules_result = await self.db.execute(rules_stmt)
        rules = rules_result.scalars().all()

        # 3. Get products — EXCLUDE out-of-stock (estoque <= 0) and inactive
        prod_stmt = (
            select(Produtos_empresa)
            .where(and_(
                Produtos_empresa.empresa_id == empresa_id,
                Produtos_empresa.user_id == user_id,
                or_(
                    Produtos_empresa.estoque.is_(None),
                    Produtos_empresa.estoque > 0,
                ),
                or_(
                    Produtos_empresa.ativo.is_(None),
                    Produtos_empresa.ativo == True,
                ),
            ))
            .limit(50)
        )
        prod_result = await self.db.execute(prod_stmt)
        products = [row_to_dict(p) for p in prod_result.scalars().all()]

        # Count out-of-stock products for context
        oos_stmt = select(func.count()).select_from(Produtos_empresa).where(and_(
            Produtos_empresa.empresa_id == empresa_id,
            Produtos_empresa.user_id == user_id,
            Produtos_empresa.estoque != None,
            Produtos_empresa.estoque <= 0,
        ))
        oos_result = await self.db.execute(oos_stmt)
        out_of_stock_count = oos_result.scalar() or 0

        # 4. Get curated looks
        looks_conditions = [
            Curated_looks.empresa_id == empresa_id,
            Curated_looks.user_id == user_id,
            Curated_looks.ativo == True,
        ]
        if ocasiao:
            looks_conditions.append(Curated_looks.ocasiao.ilike(f"%{ocasiao}%"))
        looks_stmt = select(Curated_looks).where(and_(*looks_conditions)).limit(10)
        looks_result = await self.db.execute(looks_stmt)
        curated_looks = [row_to_dict(l) for l in looks_result.scalars().all()]

        # 5. Get customer data if provided
        customer_data = {}
        closet_items = []
        purchase_history = []
        if cliente_id:
            client_stmt = select(Clientes).where(
                and_(Clientes.id == cliente_id, Clientes.user_id == user_id)
            )
            client_result = await self.db.execute(client_stmt)
            client = client_result.scalar_one_or_none()
            if client:
                customer_data = row_to_dict(client)

            closet_stmt = select(Closet_cliente).where(
                and_(Closet_cliente.empresa_id == empresa_id, Closet_cliente.cliente_id == cliente_id, Closet_cliente.user_id == user_id)
            )
            closet_result = await self.db.execute(closet_stmt)
            closet_items = [row_to_dict(c) for c in closet_result.scalars().all()]

            orders_stmt = select(Pedidos).where(
                and_(Pedidos.empresa_id == empresa_id, Pedidos.cliente_id == cliente_id, Pedidos.user_id == user_id)
            )
            orders_result = await self.db.execute(orders_stmt)
            purchase_history = [row_to_dict(o) for o in orders_result.scalars().all()]

        # 6. Build AI prompt
        rules_text = "\n".join([f"- {r.rule_type}: {r.rule_value} (prioridade {r.prioridade})" for r in rules]) if rules else "Sem regras específicas."
        aesthetic = brand.aesthetic_description if brand and brand.aesthetic_description else "Moda contemporânea"
        tone = brand.tone_of_voice if brand and brand.tone_of_voice else "Sofisticado e acolhedor"

        products_summary = json.dumps([
            {"id": p["id"], "nome": p.get("nome"), "categoria": p.get("categoria"), "cor": p.get("cor"),
             "preco": p.get("preco"), "estoque": p.get("estoque"), "ocasiao": p.get("ocasiao"),
             "tags_estilo": p.get("tags_estilo"), "colecao": p.get("colecao"), "tamanho": p.get("tamanho")}
            for p in products[:30]
        ], ensure_ascii=False)

        curated_summary = json.dumps([
            {"nome": l.get("nome"), "ocasiao": l.get("ocasiao"), "estilo": l.get("estilo"), "tags": l.get("tags")}
            for l in curated_looks
        ], ensure_ascii=False) if curated_looks else "Nenhum look curado."

        customer_summary = ""
        if customer_data:
            customer_summary = f"""
Cliente: {customer_data.get('nome', 'N/A')}
Estilo: {customer_data.get('estilo_resumo', 'N/A')}
Tamanhos: Top {customer_data.get('tamanho_top', 'N/A')}, Bottom {customer_data.get('tamanho_bottom', 'N/A')}, Dress {customer_data.get('tamanho_dress', 'N/A')}
Itens no closet: {len(closet_items)}
Pedidos: {len(purchase_history)}
"""

        prompt = f"""Você é um estilista de moda especializado. Gere {limit} recomendações de produtos para o contexto abaixo.

IMPORTANTE: Todos os produtos listados abaixo estão em estoque. {out_of_stock_count} produtos foram excluídos por estarem esgotados. NUNCA recomende produtos fora de estoque.

ESTÉTICA DA MARCA: {aesthetic}
TOM DE VOZ: {tone}
OCASIÃO: {ocasiao or 'Geral'}

REGRAS DA MARCA:
{rules_text}

CATÁLOGO DISPONÍVEL (apenas em estoque):
{products_summary}

LOOKS CURADOS PELA MARCA:
{curated_summary}

{customer_summary}

Responda APENAS em JSON válido com esta estrutura:
{{
  "recommendations": [
    {{
      "produto_id": <int>,
      "nome": "<nome do produto>",
      "motivo": "<por que recomendar este produto>",
      "score": <float 0-1>,
      "combina_com": [<lista de produto_ids que combinam>]
    }}
  ],
  "look_sugerido": {{
    "nome": "<nome do look>",
    "descricao": "<descrição editorial>",
    "produtos": [<lista de produto_ids>]
  }},
  "dicas_estilo": ["<dica 1>", "<dica 2>"]
}}"""

        try:
            ai_service = AIHubService()
            request = GenTxtRequest(
                messages=[
                    ChatMessage(role="system", content="Você é um motor de recomendação de moda. Responda sempre em JSON válido."),
                    ChatMessage(role="user", content=prompt),
                ],
                model="deepseek-v3.2",
            )
            response = await ai_service.gentxt(request)
            ai_text = response.content

            # Parse JSON from response
            json_start = ai_text.find("{")
            json_end = ai_text.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                ai_result = json.loads(ai_text[json_start:json_end])
            else:
                ai_result = {"recommendations": [], "look_sugerido": None, "dicas_estilo": []}

        except Exception as e:
            logger.error(f"AI recommendation error: {e}")
            # Fallback: return top products
            ai_result = {
                "recommendations": [
                    {"produto_id": p["id"], "nome": p.get("nome"), "motivo": "Produto popular", "score": 0.5, "combina_com": []}
                    for p in products[:limit]
                ],
                "look_sugerido": None,
                "dicas_estilo": ["Explore nosso catálogo para encontrar peças que combinam com seu estilo."],
            }

        # 7. Log recommendation
        try:
            log_entry = Recommendation_logs(
                empresa_id=empresa_id,
                cliente_id=cliente_id,
                produtos_recomendados=json.dumps([r.get("produto_id") for r in ai_result.get("recommendations", [])]),
                ocasiao=ocasiao,
                fonte="hibrido",
                clicado=False,
                created_at=datetime.now(),
                user_id=user_id,
            )
            self.db.add(log_entry)
            await self.db.commit()
        except Exception as e:
            logger.error(f"Failed to log recommendation: {e}")

        return {
            "recommendations": ai_result.get("recommendations", []),
            "look_sugerido": ai_result.get("look_sugerido"),
            "dicas_estilo": ai_result.get("dicas_estilo", []),
            "fonte": "hibrido",
            "total_produtos_analisados": len(products),
            "produtos_fora_estoque": out_of_stock_count,
            "looks_curados_considerados": len(curated_looks),
            "regras_aplicadas": len(rules),
        }

    async def generate_outfit(
        self, empresa_id: int, user_id: str,
        cliente_id: Optional[int] = None, ocasiao: str = "casual",
    ) -> Dict[str, Any]:
        """Generate a complete outfit from closet + catalog"""
        # Get closet items with product details
        closet_products = []
        if cliente_id:
            closet_stmt = select(Closet_cliente).where(
                and_(Closet_cliente.empresa_id == empresa_id, Closet_cliente.cliente_id == cliente_id, Closet_cliente.user_id == user_id)
            )
            closet_result = await self.db.execute(closet_stmt)
            closet_entries = closet_result.scalars().all()

            for entry in closet_entries:
                prod_stmt = select(Produtos_empresa).where(Produtos_empresa.id == entry.produto_id)
                prod_result = await self.db.execute(prod_stmt)
                product = prod_result.scalar_one_or_none()
                if product:
                    closet_products.append(row_to_dict(product))

        # Also get catalog products — EXCLUDE out-of-stock and inactive
        catalog_stmt = (
            select(Produtos_empresa)
            .where(and_(
                Produtos_empresa.empresa_id == empresa_id,
                Produtos_empresa.user_id == user_id,
                or_(
                    Produtos_empresa.estoque.is_(None),
                    Produtos_empresa.estoque > 0,
                ),
                or_(
                    Produtos_empresa.ativo.is_(None),
                    Produtos_empresa.ativo == True,
                ),
            ))
            .limit(30)
        )
        catalog_result = await self.db.execute(catalog_stmt)
        catalog_products = [row_to_dict(p) for p in catalog_result.scalars().all()]

        # Get brand aesthetic
        brand_stmt = select(Brand_settings).where(
            and_(Brand_settings.empresa_id == empresa_id, Brand_settings.user_id == user_id)
        )
        brand_result = await self.db.execute(brand_stmt)
        brand = brand_result.scalar_one_or_none()
        aesthetic = brand.aesthetic_description if brand and brand.aesthetic_description else "Moda contemporânea"

        all_products = json.dumps([
            {"id": p["id"], "nome": p.get("nome"), "categoria": p.get("categoria"), "cor": p.get("cor"),
             "preco": p.get("preco"), "ocasiao": p.get("ocasiao"), "tags_estilo": p.get("tags_estilo"),
             "fonte": "closet" if p in closet_products else "catalogo"}
            for p in (closet_products + catalog_products)[:40]
        ], ensure_ascii=False)

        prompt = f"""Monte um look completo para a ocasião "{ocasiao}" usando os produtos disponíveis.
Priorize peças do closet do cliente. Complete com peças do catálogo se necessário.

ESTÉTICA DA MARCA: {aesthetic}

PRODUTOS DISPONÍVEIS:
{all_products}

Responda APENAS em JSON válido:
{{
  "outfit": {{
    "nome": "<nome do look>",
    "ocasiao": "{ocasiao}",
    "descricao": "<descrição editorial do look>",
    "pecas": [
      {{"produto_id": <int>, "nome": "<nome>", "categoria": "<categoria>", "fonte": "closet|catalogo", "papel": "<papel no look: base, destaque, complemento, acessório>"}}
    ]
  }},
  "dicas": ["<dica 1>", "<dica 2>"]
}}"""

        try:
            ai_service = AIHubService()
            request = GenTxtRequest(
                messages=[
                    ChatMessage(role="system", content="Você é um estilista de moda expert. Responda sempre em JSON válido."),
                    ChatMessage(role="user", content=prompt),
                ],
                model="deepseek-v3.2",
            )
            response = await ai_service.gentxt(request)
            ai_text = response.content
            json_start = ai_text.find("{")
            json_end = ai_text.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                ai_result = json.loads(ai_text[json_start:json_end])
            else:
                ai_result = {"outfit": None, "dicas": []}
        except Exception as e:
            logger.error(f"AI outfit error: {e}")
            ai_result = {"outfit": None, "dicas": ["Não foi possível gerar o look. Tente novamente."]}

        return ai_result

    async def get_recommendation_analytics(
        self, empresa_id: int, user_id: str,
    ) -> Dict[str, Any]:
        """Get recommendation analytics for AI learning dashboard"""
        # Total recommendations
        total_stmt = select(func.count()).select_from(Recommendation_logs).where(
            and_(Recommendation_logs.empresa_id == empresa_id, Recommendation_logs.user_id == user_id)
        )
        total_result = await self.db.execute(total_stmt)
        total = total_result.scalar() or 0

        # Clicked
        clicked_stmt = select(func.count()).select_from(Recommendation_logs).where(
            and_(Recommendation_logs.empresa_id == empresa_id, Recommendation_logs.user_id == user_id, Recommendation_logs.clicado == True)
        )
        clicked_result = await self.db.execute(clicked_stmt)
        clicked = clicked_result.scalar() or 0

        # Approved by brand
        approved_stmt = select(func.count()).select_from(Recommendation_logs).where(
            and_(Recommendation_logs.empresa_id == empresa_id, Recommendation_logs.user_id == user_id, Recommendation_logs.aprovado_marca == True)
        )
        approved_result = await self.db.execute(approved_stmt)
        approved = approved_result.scalar() or 0

        # Recent logs
        recent_stmt = (
            select(Recommendation_logs)
            .where(and_(Recommendation_logs.empresa_id == empresa_id, Recommendation_logs.user_id == user_id))
            .order_by(desc(Recommendation_logs.created_at))
            .limit(20)
        )
        recent_result = await self.db.execute(recent_stmt)
        recent_logs = [row_to_dict(r) for r in recent_result.scalars().all()]

        # By occasion
        occasion_stmt = (
            select(Recommendation_logs.ocasiao, func.count().label("count"))
            .where(and_(Recommendation_logs.empresa_id == empresa_id, Recommendation_logs.user_id == user_id))
            .group_by(Recommendation_logs.ocasiao)
        )
        occasion_result = await self.db.execute(occasion_stmt)
        by_occasion = {row[0] or "geral": row[1] for row in occasion_result.all()}

        return {
            "total_recommendations": total,
            "total_clicked": clicked,
            "total_approved": approved,
            "click_rate": round(clicked / total * 100, 1) if total > 0 else 0,
            "approval_rate": round(approved / total * 100, 1) if total > 0 else 0,
            "by_occasion": by_occasion,
            "recent_logs": recent_logs,
        }