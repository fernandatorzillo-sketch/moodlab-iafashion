#!/usr/bin/env python
# -*- coding: utf-8 -*-
# CORRIGIDO: lê DATABASE_URL da variável de ambiente ao invés de usar
# a URL hardcoded do alembic.ini.

import asyncio
import importlib
import os
import pkgutil
from logging.config import fileConfig

import models
from alembic import context
from core.database import Base
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import create_async_engine

# Importa automaticamente todos os models para que o metadata seja populado
for _, module_name, _ in pkgutil.iter_modules(models.__path__):
    importlib.import_module(f"{models.__name__}.{module_name}")

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_url() -> str:
    """
    Lê DATABASE_URL da env e converte para driver síncrono (psycopg2).
    O Alembic usa engine síncrono internamente — asyncpg não é compatível.
    """
    url = os.getenv("DATABASE_URL", "").strip()

    if not url:
        raise RuntimeError(
            "Variável de ambiente DATABASE_URL não definida. "
            "Defina-a antes de rodar alembic upgrade head."
        )

    # asyncpg → psycopg2 (driver síncrono para o Alembic)
    url = url.replace("postgresql+asyncpg://", "postgresql://", 1)
    url = url.replace("postgres://", "postgresql://", 1)

    # aiosqlite → sqlite (para desenvolvimento local)
    url = url.replace("sqlite+aiosqlite:///", "sqlite:///", 1)

    return url


def alembic_include_object(object, name, type_, reflected, compare_to):
    # Ignora tabelas internas de autenticação nas migrações automáticas
    if type_ == "table" and name in ["users", "sessions", "oidc_states"]:
        return False
    return True


async def run_migrations_online():
    # CORREÇÃO: usa get_url() para garantir que aponta para o banco correto
    connectable = create_async_engine(
        get_url().replace("postgresql://", "postgresql+asyncpg://", 1)
        if get_url().startswith("postgresql://")
        else get_url().replace("sqlite:///", "sqlite+aiosqlite:///", 1)
        if get_url().startswith("sqlite:///")
        else get_url(),
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(
            lambda sync_conn: context.configure(
                connection=sync_conn,
                target_metadata=target_metadata,
                compare_type=True,
                compare_server_default=True,
                include_object=alembic_include_object,
            )
        )
        async with connection.begin():
            await connection.run_sync(lambda sync_conn: context.run_migrations())

    await connectable.dispose()


def run_migrations():
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(run_migrations_online())
    except RuntimeError:
        asyncio.run(run_migrations_online())


run_migrations()
