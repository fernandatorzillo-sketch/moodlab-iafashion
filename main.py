import traceback
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from core.config import settings

# ── API pública (sem autenticação) ───────────────────────────────────────────
from api.customer_closet import router as customer_closet_public_router
from api.image_proxy import router as image_proxy_router

# ── Routers autenticados ─────────────────────────────────────────────────────
from routers.auth import router as auth_router
from routers.user import router as user_router
from routers.engine import router as engine_router
from routers.import_router import router as import_router
from routers.brand_rules import router as brand_rules_router
from routers.brand_settings import router as brand_settings_router
from routers.empresas import router as empresas_router
from routers.clientes import router as clientes_router
from routers.curated_looks import router as curated_looks_router
from routers.curated_look_items import router as curated_look_items_router
from routers.pedidos import router as pedidos_router
from routers.itens_pedido import router as itens_pedido_router
from routers.produtos_empresa import router as produtos_empresa_router
from routers.recommendation_logs import router as recommendation_logs_router
from routers.outfit_recommendations import router as outfit_recs_router
from routers.closet_cliente import router as closet_cliente_router
from routers.style_preferences import router as style_prefs_router
from routers.storage import router as storage_router
from routers.settings import router as settings_router
from routers.price_router import router as price_router
from routers.stock_router import router as stock_router
from routers.aihub import router as aihub_router
from routers.health import router as health_router

from services.database import initialize_database, close_database
from services.mock_data import initialize_mock_data
from services.auth import initialize_admin_user


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        await initialize_database()
        await initialize_mock_data()
        await initialize_admin_user()
    except Exception:
        traceback.print_exc()
    yield
    await close_database()


app = FastAPI(
    title="MoodLab API",
    description="Closet virtual SaaS — Água de Coco x VTEX Legacy",
    version="2.0.0",
    lifespan=lifespan,
)

# Adicione aqui o domínio Render do seu frontend quando souber
# ex: "https://moodlab-frontend.onrender.com"
ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "https://homologaguadecoco.myvtex.com",
    "https://www.aguadecoco.com.br",
    "https://aguadecoco.com.br",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# ── API pública ───────────────────────────────────────────────────────────────
app.include_router(customer_closet_public_router)
app.include_router(image_proxy_router)

# ── Routers autenticados ──────────────────────────────────────────────────────
app.include_router(auth_router)
app.include_router(user_router)
app.include_router(engine_router)
app.include_router(import_router)
app.include_router(brand_rules_router)
app.include_router(brand_settings_router)
app.include_router(empresas_router)
app.include_router(clientes_router)
app.include_router(curated_looks_router)
app.include_router(curated_look_items_router)
app.include_router(pedidos_router)
app.include_router(itens_pedido_router)
app.include_router(produtos_empresa_router)
app.include_router(recommendation_logs_router)
app.include_router(outfit_recs_router)
app.include_router(closet_cliente_router)
app.include_router(style_prefs_router)
app.include_router(storage_router)
app.include_router(settings_router)
app.include_router(price_router)
app.include_router(stock_router)
app.include_router(aihub_router)
app.include_router(health_router)

app.mount("/public", StaticFiles(directory="public"), name="public")


@app.get("/")
async def root():
    return {"message": "MoodLab API is running", "version": "2.0.0"}


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat(),
        "app": settings.app_name,
        "version": settings.version,
    }
