import os

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from models.base import Base


def normalize_database_url(raw_url: str | None) -> str:
    url = (raw_url or "").strip()

    if not url:
        return "sqlite+aiosqlite:///./closet.db"

    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+asyncpg://", 1)

    if url.startswith("postgresql://") and "+asyncpg" not in url:
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)

    if url.startswith("sqlite:///") and "+aiosqlite" not in url:
        return url.replace("sqlite:///", "sqlite+aiosqlite:///", 1)

    return url


DATABASE_URL = normalize_database_url(
    os.getenv("CLOSET_DATABASE_URL") or os.getenv("DATABASE_URL")
)

engine_kwargs = {"echo": False}

if not DATABASE_URL.startswith("sqlite"):
    engine_kwargs.update(
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
        pool_timeout=30,
    )

engine = create_async_engine(DATABASE_URL, **engine_kwargs)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def init_closet_db() -> None:
    import models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)