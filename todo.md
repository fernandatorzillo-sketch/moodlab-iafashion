# Moodlab.AI — Full Recommendation Engine MVP

## Design Guidelines
- **Primary**: #A3966A (Gold), **Secondary**: #895D2B (Dark Gold)
- **Background**: #FFFFFF, **Text**: #1A1A1A
- **Font**: DM Serif Display (headings), DM Sans (body)
- **Cards**: rounded-xl, border, hover shadow
- **Brand**: Moodlab.AI — AI-powered fashion recommendation engine

## Database Tables (DONE)
- ✅ empresas, clientes, produtos_empresa, pedidos, itens_pedido, closet_cliente
- ✅ brand_settings, curated_looks, curated_look_items, brand_rules, recommendation_logs

## Backend APIs to Create
1. `/api/v1/engine/search` — Product search by text, category, tags, occasion
2. `/api/v1/engine/recommendations` — AI hybrid recommendations (deepseek-v3.2)
3. `/api/v1/engine/outfits` — AI outfit generation from closet + catalog
4. `/api/v1/engine/customer-closet` — Customer closet with full product details

## Frontend Pages to Create/Update
1. **BrandSettingsPage** — White-label visual customization per company
2. **CuratedLooksPage** — Look library: create/edit/manage curated looks + items
3. **BrandRulesPage** — Recommendation rules configuration
4. **AILearningPage** — AI learning dashboard with recommendation analytics
5. **Update Header** — Add new nav items
6. **Update App.tsx** — Add new routes

## Files to Create
- `app/backend/routers/engine.py` — All 4 engine API endpoints
- `app/backend/services/engine_service.py` — Engine logic + AI integration
- `app/frontend/src/pages/BrandSettingsPage.tsx` — White-label settings
- `app/frontend/src/pages/CuratedLooksPage.tsx` — Look library + curation
- `app/frontend/src/pages/BrandRulesPage.tsx` — Recommendation rules
- `app/frontend/src/pages/AILearningPage.tsx` — AI learning dashboard
- Update: `Header.tsx`, `App.tsx`, `LanguageContext.tsx`