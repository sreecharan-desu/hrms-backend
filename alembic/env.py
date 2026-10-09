"""Async Alembic env.py – uses asyncpg against Neon/Postgres."""

from __future__ import annotations

import asyncio
import os
import re
import ssl as _ssl
from logging.config import fileConfig
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

from app.core.database import Base

# Import all models so metadata is populated
import app.infrastructure.database.models  # noqa: F401

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# Query params that asyncpg does not accept via the DSN
_STRIP_PARAMS = {"channel_binding", "sslmode"}


def _get_url_and_connect_args() -> tuple[str, dict]:
    """Return a clean asyncpg URL and any extra connect_args."""
    raw = os.environ.get("DATABASE_URL_UNPOOLED") or os.environ.get("DATABASE_URL", "")
    raw = re.sub(r"^postgresql://", "postgresql+asyncpg://", raw)

    parsed = urlparse(raw)
    params = parse_qs(parsed.query, keep_blank_values=True)

    needs_ssl = params.pop("sslmode", [None])[0] in ("require", "verify-ca", "verify-full")
    for key in _STRIP_PARAMS:
        params.pop(key, None)

    clean_query = urlencode({k: v[0] for k, v in params.items()}, doseq=False)
    clean_url = urlunparse(parsed._replace(query=clean_query))

    connect_args: dict = {}
    if needs_ssl:
        ssl_ctx = _ssl.create_default_context()
        ssl_ctx.check_hostname = False
        ssl_ctx.verify_mode = _ssl.CERT_NONE
        connect_args["ssl"] = ssl_ctx

    return clean_url, connect_args


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode – emit SQL to stdout."""
    url, _ = _get_url_and_connect_args()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection) -> None:  # noqa: ANN001
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations in 'online' mode with an async engine."""
    url, connect_args = _get_url_and_connect_args()

    cfg = config.get_section(config.config_ini_section, {})
    cfg["sqlalchemy.url"] = url

    connectable = async_engine_from_config(
        cfg,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        connect_args=connect_args,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
