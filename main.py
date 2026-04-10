import traceback
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from core.config import settings
from api.customer_closet import router as customer_closet_router

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
    title="FastAPI Modular Template",
    description="A best-practice FastAPI template with modular architecture",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "https://homologaguadecoco.myvtex.com",
        "https://www.aguadecoco.com.br",
        "https://aguadecoco.com.br",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

app.include_router(customer_closet_router)

app.mount("/public", StaticFiles(directory="public"), name="public")


@app.get("/")
async def root():
    return {"message": "FastAPI Modular Template is running"}


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat(),
        "app": settings.app_name,
        "version": settings.version,
    }