import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from sqlalchemy import select, and_, delete, update, func, text, or_
from sqlalchemy.ext.asyncio import AsyncSession

from models.clientes import Clientes
from models.produtos_empresa import Produtos_empresa
from models.pedidos import Pedidos
from models.itens_pedido import Itens_pedido
from models.closet_cliente import Closet_cliente

logger = logging.getLogger(__name__)

MODEL_MAP = {
    "clientes": Clientes,
    "produtos": Produtos_empresa,
    "pedidos": Pedidos,
    "itens_pedido": Itens_pedido,
}

# Fields that should not be set from CSV
PROTECTED_FIELDS = {"id", "user_id"}


class ImportService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def process_csv_rows(
        self,
        empresa_id: int,
        entity_type: str,
        field_mapping: Dict[str, str],
        rows: List[Dict[str, Any]],
        user_id: str,
        auto_sync_closet: bool = True,
    ) -> Dict[str, Any]:
        model_class = MODEL_MAP.get(entity_type)
        if not model_class:
            return {"success": 0, "errors": [], "closet_synced": 0}

        success_count = 0
        errors = []

        # Pre-build SKU → produto_id lookup for itens_pedido imports
        sku_to_produto_id: Dict[str, int] = {}
        if entity_type == "itens_pedido":
            sku_stmt = select(Produtos_empresa.sku, Produtos_empresa.id).where(
                and_(
                    Produtos_empresa.empresa_id == empresa_id,
                    Produtos_empresa.user_id == user_id,
                    Produtos_empresa.sku != None,
                )
            )
            sku_result = await self.db.execute(sku_stmt)
            for sku_val, prod_id in sku_result.all():
                if sku_val:
                    sku_to_produto_id[str(sku_val).strip()] = prod_id

        # Pre-build numero_pedido → pedido.id lookup for itens_pedido imports
        numero_to_pedido_id: Dict[str, int] = {}
        if entity_type == "itens_pedido":
            ped_stmt = select(Pedidos.numero_pedido, Pedidos.id).where(
                and_(
                    Pedidos.empresa_id == empresa_id,
                    Pedidos.user_id == user_id,
                )
            )
            ped_result = await self.db.execute(ped_stmt)
            for num, pid in ped_result.all():
                if num:
                    numero_to_pedido_id[str(num).strip()] = pid

        # Pre-build email → cliente_id lookup for pedidos imports
        email_to_cliente: Dict[str, int] = {}
        if entity_type == "pedidos":
            cli_stmt = select(Clientes.email, Clientes.id).where(
                and_(
                    Clientes.empresa_id == empresa_id,
                    Clientes.user_id == user_id,
                    Clientes.email != None,
                )
            )
            cli_result = await self.db.execute(cli_stmt)
            for email_val, cli_id in cli_result.all():
                if email_val and '@' in str(email_val):
                    email_to_cliente[str(email_val).strip().lower()] = cli_id

        for idx, row in enumerate(rows):
            try:
                mapped_data: Dict[str, Any] = {}
                for csv_col, db_field in field_mapping.items():
                    if db_field in PROTECTED_FIELDS:
                        continue
                    value = row.get(csv_col)
                    if value is not None and value != "":
                        mapped_data[db_field] = value

                mapped_data["empresa_id"] = empresa_id
                mapped_data["user_id"] = user_id

                # Type conversions
                for field_name, value in list(mapped_data.items()):
                    col = getattr(model_class, field_name, None)
                    if col is None:
                        del mapped_data[field_name]
                        continue
                    col_type = str(col.type)
                    if "INTEGER" in col_type and not isinstance(value, int):
                        try:
                            mapped_data[field_name] = int(float(str(value)))
                        except (ValueError, TypeError):
                            mapped_data[field_name] = None
                    elif "FLOAT" in col_type and not isinstance(value, float):
                        try:
                            mapped_data[field_name] = float(str(value).replace(",", "."))
                        except (ValueError, TypeError):
                            mapped_data[field_name] = None
                    elif "BOOLEAN" in col_type:
                        mapped_data[field_name] = str(value).lower() in ("true", "1", "sim", "yes")
                    elif "DATETIME" in col_type and isinstance(value, str):
                        try:
                            mapped_data[field_name] = datetime.fromisoformat(value.replace("/", "-"))
                        except (ValueError, TypeError):
                            try:
                                parts = value.split("/")
                                if len(parts) == 3:
                                    mapped_data[field_name] = datetime(int(parts[2]), int(parts[1]), int(parts[0]))
                                else:
                                    mapped_data[field_name] = None
                            except Exception:
                                mapped_data[field_name] = None

                # For pedidos: auto-link cliente_id from email if available
                if entity_type == "pedidos":
                    # Try to resolve cliente_id from email mapping
                    email_col = None
                    for csv_col, db_field in field_mapping.items():
                        if db_field == "email_cliente" or "email" in csv_col.lower():
                            email_col = csv_col
                            break
                    if email_col and row.get(email_col):
                        email_val = str(row[email_col]).strip().lower()
                        if '@' in email_val:
                            # Auto-resolve cliente_id
                            if not mapped_data.get("cliente_id") and email_val in email_to_cliente:
                                mapped_data["cliente_id"] = email_to_cliente[email_val]

                # For itens_pedido: resolve produto_id from SKU if not provided
                if entity_type == "itens_pedido":
                    produto_id = mapped_data.get("produto_id")
                    sku_val = mapped_data.get("sku")
                    if (produto_id is None) and sku_val:
                        resolved_id = sku_to_produto_id.get(str(sku_val).strip())
                        if resolved_id:
                            mapped_data["produto_id"] = resolved_id
                        else:
                            errors.append(f"Row {idx + 1}: SKU '{sku_val}' não encontrado no catálogo de produtos")
                            logger.warning(f"Import row {idx + 1}: SKU '{sku_val}' not found in produtos_empresa")
                            continue

                    # Final check: produto_id must exist
                    if not mapped_data.get("produto_id"):
                        errors.append(f"Row {idx + 1}: produto_id ausente e SKU não mapeado")
                        continue

                    # Resolve pedido_id: if it matches a numero_pedido, convert to internal ID
                    pedido_id_val = mapped_data.get("pedido_id")
                    if pedido_id_val is not None:
                        pedido_id_str = str(pedido_id_val).strip()
                        # Check if this pedido_id is actually a numero_pedido
                        if pedido_id_str in numero_to_pedido_id:
                            mapped_data["pedido_id"] = numero_to_pedido_id[pedido_id_str]

                obj = model_class(**mapped_data)
                self.db.add(obj)
                await self.db.flush()
                success_count += 1
            except Exception as e:
                # Rollback the failed flush so the session stays usable
                await self.db.rollback()
                errors.append(f"Row {idx + 1}: {str(e)}")
                logger.error(f"Import error row {idx + 1}: {e}")

        await self.db.commit()

        # Auto-sync closet when pedidos are imported
        closet_synced = 0
        stock_deducted = 0
        if auto_sync_closet and entity_type == "pedidos" and success_count > 0:
            try:
                sync_result = await self.sync_closet(empresa_id, user_id)
                closet_synced = sync_result.get("new_entries", 0)
                logger.info(f"Auto-synced {closet_synced} closet entries after pedidos import")
            except Exception as e:
                logger.error(f"Auto closet sync failed: {e}")
                errors.append(f"Closet auto-sync error: {str(e)}")

            # Auto-deduct stock for purchase events
            try:
                stock_result = await self.deduct_stock_from_orders(empresa_id, user_id)
                stock_deducted = stock_result.get("total_deductions", 0)
                if stock_deducted > 0:
                    logger.info(f"Auto-deducted stock for {stock_deducted} items after pedidos import")
            except Exception as e:
                logger.error(f"Auto stock deduction failed: {e}")
                errors.append(f"Stock deduction error: {str(e)}")

        # Auto-deduct stock when itens_pedido are imported
        if entity_type == "itens_pedido" and success_count > 0:
            try:
                stock_result = await self.deduct_stock_from_items(empresa_id, user_id, rows, field_mapping)
                stock_deducted = stock_result.get("deducted", 0)
                if stock_deducted > 0:
                    logger.info(f"Auto-deducted stock for {stock_deducted} items after itens_pedido import")
            except Exception as e:
                logger.error(f"Auto stock deduction from items failed: {e}")
                errors.append(f"Stock deduction error: {str(e)}")

        return {"success": success_count, "errors": errors, "closet_synced": closet_synced, "stock_deducted": stock_deducted}

    async def sync_closet(self, empresa_id: int, user_id: str) -> Dict[str, Any]:
        """Get completed orders and sync products to closet.
        
        Uses multiple strategies to handle broken data:
        - Standard: pedidos.cliente_id → itens_pedido.pedido_id = pedidos.id
        - Fallback: itens_pedido.pedido_id matches numero_pedido (common corruption)
        """
        completed_statuses = ["entregue", "completo", "delivered", "completed"]
        # Case-insensitive status matching
        stmt = select(Pedidos).where(
            and_(
                Pedidos.empresa_id == empresa_id,
                Pedidos.user_id == user_id,
                func.lower(Pedidos.status).in_(completed_statuses),
            )
        )
        result = await self.db.execute(stmt)
        orders = result.scalars().all()

        new_entries = 0
        for order in orders:
            # Resolve cliente_id — try order.cliente_id first, then email_cliente lookup
            cliente_id = order.cliente_id
            if not cliente_id:
                # Try email_cliente column via raw SQL (not in ORM model)
                try:
                    email_sql = text(
                        "SELECT email_cliente FROM pedidos WHERE id = :pid"
                    )
                    email_result = await self.db.execute(email_sql, {"pid": order.id})
                    email_row = email_result.fetchone()
                    if email_row and email_row[0] and '@' in str(email_row[0]):
                        email_val = str(email_row[0]).strip().lower()
                        cli_stmt = select(Clientes.id).where(
                            and_(
                                Clientes.empresa_id == empresa_id,
                                func.lower(func.trim(Clientes.email)) == email_val,
                            )
                        )
                        cli_result = await self.db.execute(cli_stmt)
                        cli_row = cli_result.scalar_one_or_none()
                        if cli_row:
                            cliente_id = cli_row
                except Exception:
                    pass

            if not cliente_id:
                continue

            # Get items — try both internal ID and numero_pedido
            conditions = [Itens_pedido.user_id == user_id]
            id_conditions = [Itens_pedido.pedido_id == order.id]
            if order.numero_pedido:
                try:
                    num_as_int = int(order.numero_pedido)
                    id_conditions.append(Itens_pedido.pedido_id == num_as_int)
                except (ValueError, TypeError):
                    pass
            
            items_stmt = select(Itens_pedido).where(
                and_(
                    or_(*id_conditions),
                    *conditions,
                )
            )
            items_result = await self.db.execute(items_stmt)
            items = items_result.scalars().all()

            for item in items:
                if not item.produto_id:
                    continue
                existing_stmt = select(Closet_cliente).where(
                    and_(
                        Closet_cliente.empresa_id == empresa_id,
                        Closet_cliente.cliente_id == cliente_id,
                        Closet_cliente.produto_id == item.produto_id,
                        Closet_cliente.user_id == user_id,
                    )
                )
                existing_result = await self.db.execute(existing_stmt)
                existing = existing_result.scalar_one_or_none()

                if not existing:
                    closet_entry = Closet_cliente(
                        empresa_id=empresa_id,
                        cliente_id=cliente_id,
                        produto_id=item.produto_id,
                        origem="compra",
                        data_entrada=order.data_pedido or datetime.now(),
                        user_id=user_id,
                    )
                    self.db.add(closet_entry)
                    new_entries += 1

        await self.db.commit()
        return {"new_entries": new_entries}

    async def cleanup_data(self, empresa_id: int, user_id: str) -> Dict[str, Any]:
        """Clean up corrupted data: deduplicate clients, fix relationships, populate email_cliente."""
        results = {
            "clientes_removed": 0,
            "clientes_kept": 0,
            "pedidos_linked": 0,
            "itens_fixed": 0,
            "email_populated": 0,
            "duplicates_removed": 0,
            "messages": [],
        }

        # Step 1: Identify clean vs corrupted clientes
        all_clients_stmt = select(Clientes).where(
            and_(Clientes.empresa_id == empresa_id, Clientes.user_id == user_id)
        )
        all_clients_result = await self.db.execute(all_clients_stmt)
        all_clients = list(all_clients_result.scalars().all())

        # Group by email (normalized)
        email_groups: Dict[str, List] = {}
        corrupted_ids = []

        for c in all_clients:
            # Detect corrupted records
            is_corrupted = False
            real_email = None

            if c.nome and '\t' in c.nome:
                is_corrupted = True
                parts = c.nome.split('\t')
                for p in parts:
                    if '@' in p:
                        real_email = p.strip().lower()
            elif c.email and '@' not in str(c.email):
                is_corrupted = True
            elif not c.email:
                is_corrupted = True

            if is_corrupted:
                corrupted_ids.append(c.id)
                continue

            # Clean record
            email_key = str(c.email).strip().lower() if c.email else f"no_email_{c.id}"
            if email_key not in email_groups:
                email_groups[email_key] = []
            email_groups[email_key].append(c)

        # Step 2: Deduplicate — keep the first clean record per email
        canonical_clients: Dict[str, int] = {}  # email → canonical client id
        duplicate_ids = []

        for email_key, clients in email_groups.items():
            # Sort by id to keep the first one
            clients.sort(key=lambda x: x.id)
            canonical = clients[0]
            canonical_clients[email_key] = canonical.id
            for dup in clients[1:]:
                duplicate_ids.append(dup.id)

        # Step 3: Delete corrupted and duplicate clientes
        ids_to_remove = corrupted_ids + duplicate_ids
        if ids_to_remove:
            # First, update any pedidos referencing these clients to point to canonical
            for email_key, canonical_id in canonical_clients.items():
                for c in all_clients:
                    if c.id in ids_to_remove and c.id != canonical_id:
                        # Check if this corrupted client has pedidos
                        await self.db.execute(
                            update(Pedidos)
                            .where(and_(Pedidos.cliente_id == c.id, Pedidos.empresa_id == empresa_id))
                            .values(cliente_id=canonical_id)
                        )

            # Delete corrupted/duplicate clientes
            await self.db.execute(
                delete(Clientes).where(Clientes.id.in_(ids_to_remove))
            )
            results["clientes_removed"] = len(ids_to_remove)
            results["messages"].append(f"Removidos {len(ids_to_remove)} clientes corrompidos/duplicados")

        results["clientes_kept"] = len(canonical_clients)
        results["messages"].append(f"Mantidos {len(canonical_clients)} clientes canônicos")

        # Step 4: Link pedidos to correct clientes using numero_pedido patterns
        # Pattern: corrupted clientes had nome like "222\tFernanda..." meaning pedido 222 = Fernanda
        numero_to_email: Dict[str, str] = {}
        for c in all_clients:
            if c.nome and '\t' in c.nome:
                parts = c.nome.split('\t')
                possible_numero = parts[0].strip()
                for p in parts:
                    if '@' in p:
                        numero_to_email[possible_numero] = p.strip().lower()

        # Get all pedidos
        pedidos_stmt = select(Pedidos).where(
            and_(Pedidos.empresa_id == empresa_id, Pedidos.user_id == user_id)
        )
        pedidos_result = await self.db.execute(pedidos_stmt)
        all_pedidos = list(pedidos_result.scalars().all())

        for pedido in all_pedidos:
            updated = False
            numero = str(pedido.numero_pedido).strip() if pedido.numero_pedido else ""

            # Try to find email from numero_pedido pattern
            email_for_pedido = numero_to_email.get(numero)

            if email_for_pedido and email_for_pedido in canonical_clients:
                canonical_id = canonical_clients[email_for_pedido]
                if pedido.cliente_id != canonical_id:
                    pedido.cliente_id = canonical_id
                    results["pedidos_linked"] += 1

                # Populate email_cliente via raw SQL
                try:
                    await self.db.execute(
                        text("UPDATE pedidos SET email_cliente = :email WHERE id = :pid AND (email_cliente IS NULL OR email_cliente = '')"),
                        {"email": email_for_pedido, "pid": pedido.id}
                    )
                    results["email_populated"] += 1
                except Exception:
                    pass
            elif pedido.cliente_id and pedido.cliente_id in canonical_clients.values():
                # Already linked correctly, just populate email
                try:
                    for email_key, cid in canonical_clients.items():
                        if cid == pedido.cliente_id and '@' in email_key:
                            await self.db.execute(
                                text("UPDATE pedidos SET email_cliente = :email WHERE id = :pid AND (email_cliente IS NULL OR email_cliente = '')"),
                                {"email": email_key, "pid": pedido.id}
                            )
                            results["email_populated"] += 1
                            break
                except Exception:
                    pass

        # Step 5: Fix itens_pedido.pedido_id — convert numero_pedido references to internal IDs
        # Build numero_pedido → internal pedido.id mapping
        numero_to_internal: Dict[int, int] = {}
        internal_ids = set()
        for p in all_pedidos:
            internal_ids.add(p.id)
            if p.numero_pedido:
                try:
                    num_int = int(p.numero_pedido)
                    if num_int not in internal_ids:
                        numero_to_internal[num_int] = p.id
                except (ValueError, TypeError):
                    pass

        # Get all itens_pedido
        itens_stmt = select(Itens_pedido).where(Itens_pedido.user_id == user_id)
        itens_result = await self.db.execute(itens_stmt)
        all_itens = list(itens_result.scalars().all())

        for item in all_itens:
            if item.pedido_id and item.pedido_id in numero_to_internal:
                item.pedido_id = numero_to_internal[item.pedido_id]
                results["itens_fixed"] += 1

        # Step 6: Deduplicate pedidos (same numero_pedido + empresa)
        seen_pedidos: Dict[str, int] = {}
        pedido_ids_to_remove = []
        pedido_id_remap: Dict[int, int] = {}  # old_id → canonical_id

        for p in sorted(all_pedidos, key=lambda x: x.id):
            key = f"{p.numero_pedido}_{p.empresa_id}"
            if key in seen_pedidos:
                pedido_ids_to_remove.append(p.id)
                pedido_id_remap[p.id] = seen_pedidos[key]
            else:
                seen_pedidos[key] = p.id

        # Remap itens_pedido for duplicate pedidos
        if pedido_id_remap:
            for item in all_itens:
                if item.pedido_id in pedido_id_remap:
                    item.pedido_id = pedido_id_remap[item.pedido_id]

        # Deduplicate itens_pedido (same pedido_id + produto_id + sku)
        seen_itens: set = set()
        itens_to_remove = []
        for item in sorted(all_itens, key=lambda x: x.id):
            key = f"{item.pedido_id}_{item.produto_id}_{item.sku}"
            if key in seen_itens:
                itens_to_remove.append(item.id)
            else:
                seen_itens.add(key)

        if itens_to_remove:
            await self.db.execute(delete(Itens_pedido).where(Itens_pedido.id.in_(itens_to_remove)))
            results["duplicates_removed"] += len(itens_to_remove)
            results["messages"].append(f"Removidos {len(itens_to_remove)} itens de pedido duplicados")

        if pedido_ids_to_remove:
            await self.db.execute(delete(Pedidos).where(Pedidos.id.in_(pedido_ids_to_remove)))
            results["duplicates_removed"] += len(pedido_ids_to_remove)
            results["messages"].append(f"Removidos {len(pedido_ids_to_remove)} pedidos duplicados")

        await self.db.commit()

        # Step 7: Re-sync closet after cleanup
        try:
            sync_result = await self.sync_closet(empresa_id, user_id)
            results["closet_synced"] = sync_result.get("new_entries", 0)
            results["messages"].append(f"Closet sincronizado: {results['closet_synced']} novas entradas")
        except Exception as e:
            results["messages"].append(f"Erro ao sincronizar closet: {str(e)}")

        results["messages"].append("Limpeza concluída com sucesso!")
        return results

    async def get_data_health(self, empresa_id: int, user_id: str) -> Dict[str, Any]:
        """Get data health metrics for monitoring dashboard."""
        metrics: Dict[str, Any] = {}

        # Counts
        for table_name, model in MODEL_MAP.items():
            stmt = select(func.count()).select_from(model).where(
                and_(model.empresa_id == empresa_id, model.user_id == user_id)
            )
            result = await self.db.execute(stmt)
            metrics[f"total_{table_name}"] = result.scalar() or 0

        # Closet count
        closet_stmt = select(func.count()).select_from(Closet_cliente).where(
            and_(Closet_cliente.empresa_id == empresa_id, Closet_cliente.user_id == user_id)
        )
        closet_result = await self.db.execute(closet_stmt)
        metrics["total_closet"] = closet_result.scalar() or 0

        # Corrupted clientes (nome contains tab or email has no @)
        corrupt_stmt = select(func.count()).select_from(Clientes).where(
            and_(
                Clientes.empresa_id == empresa_id,
                Clientes.user_id == user_id,
                or_(
                    Clientes.nome.contains('\t'),
                    and_(Clientes.email != None, ~Clientes.email.contains('@')),
                    Clientes.email.is_(None),
                ),
            )
        )
        corrupt_result = await self.db.execute(corrupt_stmt)
        metrics["corrupted_clientes"] = corrupt_result.scalar() or 0

        # Unlinked pedidos (cliente_id is NULL)
        unlinked_stmt = select(func.count()).select_from(Pedidos).where(
            and_(
                Pedidos.empresa_id == empresa_id,
                Pedidos.user_id == user_id,
                Pedidos.cliente_id.is_(None),
            )
        )
        unlinked_result = await self.db.execute(unlinked_stmt)
        metrics["unlinked_pedidos"] = unlinked_result.scalar() or 0

        # Itens without valid pedido reference
        if metrics["total_itens_pedido"] > 0:
            valid_pedido_ids_stmt = select(Pedidos.id).where(
                and_(Pedidos.empresa_id == empresa_id, Pedidos.user_id == user_id)
            )
            valid_result = await self.db.execute(valid_pedido_ids_stmt)
            valid_ids = set(r[0] for r in valid_result.fetchall())

            all_itens_stmt = select(Itens_pedido.pedido_id).where(Itens_pedido.user_id == user_id)
            itens_result = await self.db.execute(all_itens_stmt)
            orphan_count = sum(1 for r in itens_result.fetchall() if r[0] not in valid_ids)
            metrics["orphan_itens"] = orphan_count
        else:
            metrics["orphan_itens"] = 0

        # Products count
        prod_stmt = select(func.count()).select_from(Produtos_empresa).where(
            and_(
                Produtos_empresa.empresa_id == empresa_id,
                Produtos_empresa.user_id == user_id,
            )
        )
        prod_result = await self.db.execute(prod_stmt)
        metrics["total_produtos"] = prod_result.scalar() or 0

        # Health score (0-100)
        issues = 0
        total_checks = 4
        if metrics["corrupted_clientes"] > 0:
            issues += 1
        if metrics["unlinked_pedidos"] > 0:
            issues += 1
        if metrics["orphan_itens"] > 0:
            issues += 1
        if metrics["total_closet"] == 0 and metrics["total_pedidos"] > 0:
            issues += 1

        metrics["health_score"] = max(0, round((1 - issues / total_checks) * 100))

        return metrics

    async def deduct_stock_from_orders(self, empresa_id: int, user_id: str) -> Dict[str, Any]:
        """Deduct stock for all purchase-status orders."""
        from services.stock_service import StockService
        stock_service = StockService(self.db)
        result = await stock_service.process_orders_by_status(empresa_id, user_id)
        return result

    async def deduct_stock_from_items(
        self, empresa_id: int, user_id: str,
        rows: List[Dict[str, Any]], field_mapping: Dict[str, str],
    ) -> Dict[str, Any]:
        """Deduct stock directly from imported order items."""
        from services.stock_service import StockService
        stock_service = StockService(self.db)

        rev_mapping = {v: k for k, v in field_mapping.items()}
        sku_col = rev_mapping.get("sku")
        qty_col = rev_mapping.get("quantidade")

        deducted = 0
        for row in rows:
            sku = row.get(sku_col, "") if sku_col else ""
            qty_str = row.get(qty_col, "1") if qty_col else "1"
            try:
                qty = int(float(str(qty_str))) if qty_str else 1
            except (ValueError, TypeError):
                qty = 1

            if sku:
                result = await stock_service.deduct_stock(empresa_id, user_id, sku, qty)
                if result.get("success"):
                    deducted += 1

        await self.db.commit()
        return {"deducted": deducted}