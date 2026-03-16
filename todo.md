# MoodLab Data Fix & Enhancement Plan

## Root Cause Analysis
1. **clientes**: Duplicated rows with corrupted `nome` field (tab-separated data). Clean rows exist (id=5,6,7 and 14,15,16)
2. **pedidos**: `cliente_id=None` for most orders — orders not linked to clients
3. **itens_pedido**: `pedido_id` stores `numero_pedido` (external order number like 222), NOT `pedidos.id` (internal ID like 2)
4. **closet_cliente**: Empty because the chain email→cliente→pedidos→itens→produtos is broken at every link

## Fix Strategy
### Task 1: Rewrite customer_closet_service.py
- Use MULTIPLE lookup strategies in sequence:
  - Strategy A: email → clientes.email → pedidos.cliente_id → itens_pedido.pedido_id (current, broken)
  - Strategy B: email → clientes.email → pedidos by numero_pedido matching → itens_pedido by numero_pedido
  - Strategy C: Direct SKU lookup from itens_pedido where pedido_id matches any numero_pedido from pedidos

### Task 2: Create data cleanup endpoint
- POST /api/v1/import/cleanup-data
  - Remove duplicate/corrupted clientes (keep clean ones)
  - Link pedidos to correct clientes by matching numero_pedido patterns
  - Fix itens_pedido.pedido_id to use internal pedidos.id

### Task 3: Add email_cliente column to pedidos
- ALTER TABLE pedidos ADD COLUMN email_cliente VARCHAR
- Populate from clientes table where possible

### Task 4: Improve MeuClosetPage debug panel
- Show full chain visualization
- Add cleanup button

### Task 5: Improve IntegrationsPage
- Add sync status indicators
- Add last sync timestamp display

### Task 6: Add monitoring dashboard metrics
- Show counts: clientes, pedidos, itens, produtos, closets
- Show data health indicators

## Files to Create/Modify
1. `backend/services/customer_closet_service.py` - Rewrite lookup logic
2. `backend/routers/import_router.py` - Add cleanup endpoint  
3. `backend/services/import_service.py` - Add cleanup + email_cliente logic
4. `frontend/src/pages/MeuClosetPage.tsx` - Enhanced debug + cleanup
5. `frontend/src/pages/IntegrationsPage.tsx` - Sync status
6. `frontend/src/pages/EmpresaDashboardPage.tsx` - Monitoring metrics