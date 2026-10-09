"""Async SQLAlchemy engine and session factory (asyncpg + Neon)."""

from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import get_settings


def _build_engine():
    settings = get_settings()
    url = settings.DATABASE_URL
    # Normalise scheme for asyncpg
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    elif url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+asyncpg://", 1)

    is_sqlite = url.startswith("sqlite")
    kwargs: dict = {
        "echo": settings.is_development,
    }

    if not is_sqlite:
        # Strip query params that asyncpg can't handle (e.g. channel_binding, sslmode)
        from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

        parsed = urlparse(url)
        qs = parse_qs(parsed.query)
        needs_ssl = qs.pop("sslmode", [None])[0] in ("require", "verify-ca", "verify-full")
        qs.pop("channel_binding", None)
        clean_url = urlunparse(parsed._replace(query=urlencode(qs, doseq=True)))
        url = clean_url

        connect_args: dict = {}
        if needs_ssl or "neon" in url or ".neon." in url:
            import ssl

            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            connect_args["ssl"] = ctx

        kwargs.update(
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=10,
            pool_recycle=300,
            connect_args=connect_args,
        )

    return create_async_engine(url, **kwargs)


engine = _build_engine()

async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency-injectable async session generator."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
