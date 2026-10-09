"""FastAPI dependencies – UoW, auth, permission checks, request context."""

from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator, Callable
from dataclasses import dataclass
from typing import Annotated

import jwt
from fastapi import Depends, Header, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.database import async_session_factory
from app.core.exceptions import AuthError, ForbiddenError
from app.core.permissions import ROLE_PERMISSIONS
from app.core.security import decode_access_token
from app.infrastructure.cache.redis import (
    cache_user_permissions,
    get_cached_permissions,
)
from app.infrastructure.database.uow import SqlAlchemyUnitOfWork

_bearer = HTTPBearer(auto_error=False)


# ── DB session (legacy compat) ───────────────────────────────────────

async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async DB session and handle commit/rollback."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


def get_app_settings() -> Settings:
    """Return the cached application settings singleton."""
    return get_settings()


# ── Unit of Work ─────────────────────────────────────────────────────

async def get_uow() -> AsyncGenerator[SqlAlchemyUnitOfWork, None]:
    """Yield a UoW scoped to the request."""
    async with SqlAlchemyUnitOfWork() as uow:
        yield uow


# ── Request context ──────────────────────────────────────────────────

@dataclass(frozen=True, slots=True)
class RequestContext:
    ip: str
    user_agent: str
    request_id: str


async def get_request_context(request: Request) -> RequestContext:
    """Extract IP, User-Agent and X-Request-ID from the incoming request."""
    ip = request.headers.get("X-Forwarded-For", request.client.host if request.client else "unknown")
    if "," in ip:
        ip = ip.split(",")[0].strip()
    return RequestContext(
        ip=ip,
        user_agent=request.headers.get("User-Agent", ""),
        request_id=request.headers.get("X-Request-ID", uuid.uuid4().hex),
    )


# ── Current user (Bearer access token) ──────────────────────────────

@dataclass(frozen=True, slots=True)
class CurrentUser:
    id: str
    email: str
    roles: list[str]
    permissions: frozenset[str]


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)] = None,
) -> CurrentUser:
    """Decode the Bearer token and return a lightweight ``CurrentUser``."""
    if credentials is None:
        raise AuthError("Missing authentication token.")
    try:
        payload = decode_access_token(credentials.credentials)
    except jwt.PyJWTError as exc:
        raise AuthError(f"Invalid or expired token: {exc}") from exc

    user_id = payload.get("sub")
    if not user_id:
        raise AuthError("Token missing subject.")

    roles: list[str] = payload.get("roles", [])

    # Resolve permissions – check cache first
    cached = await get_cached_permissions(user_id)
    if cached is not None:
        perms = frozenset(cached)
    else:
        perm_set: set[str] = set()
        for role_name in roles:
            perm_set |= ROLE_PERMISSIONS.get(role_name, frozenset())
        perms = frozenset(perm_set)
        await cache_user_permissions(user_id, perm_set)

    return CurrentUser(
        id=user_id,
        email=payload.get("email", ""),
        roles=roles,
        permissions=perms,
    )


# ── Permission gate factory ─────────────────────────────────────────

def require_permission(code: str) -> Callable:
    """Return a FastAPI dependency that checks the user has *code* permission."""

    async def _check(
        user: Annotated[CurrentUser, Depends(get_current_user)],
    ) -> CurrentUser:
        if code not in user.permissions:
            raise ForbiddenError(f"Missing required permission: {code}")
        return user

    return _check


# ── Internal token guard ─────────────────────────────────────────────

async def require_internal_token(
    x_internal_token: Annotated[str | None, Header(alias="X-Internal-Token")] = None,
    settings: Settings = Depends(get_app_settings),
) -> None:
    """Validate the internal API token for protected internal routes."""
    if not settings.INTERNAL_API_TOKEN:
        raise AuthError("Internal API token not configured.")
    if x_internal_token != settings.INTERNAL_API_TOKEN:
        raise AuthError("Invalid internal API token.")
