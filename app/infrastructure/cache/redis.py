"""Async Redis client with graceful degradation.

When Redis is unavailable (e.g. in tests without a Redis server),
every operation silently returns ``None`` / does nothing.
"""

from __future__ import annotations

import json

import structlog
from redis.asyncio import Redis, from_url

from app.core.config import get_settings

logger = structlog.stdlib.get_logger(__name__)

_client: Redis | None = None


async def get_redis() -> Redis | None:
    """Return a shared async Redis client, or *None* if connection fails."""
    global _client
    if _client is not None:
        return _client
    try:
        settings = get_settings()
        _client = from_url(
            settings.REDIS_URL,
            decode_responses=True,
            socket_connect_timeout=2,
        )
        await _client.ping()
        return _client
    except Exception:
        await logger.awarning("redis_unavailable", url="<redacted>")
        _client = None
        return None


async def close_redis() -> None:
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None


# ── Permission cache ─────────────────────────────────────────────────

_PERM_TTL = 300  # 5 minutes


async def cache_user_permissions(user_id: str, permissions: set[str]) -> None:
    r = await get_redis()
    if r is None:
        return
    key = f"user:{user_id}:permissions"
    await r.set(key, json.dumps(sorted(permissions)), ex=_PERM_TTL)


async def get_cached_permissions(user_id: str) -> set[str] | None:
    r = await get_redis()
    if r is None:
        return None
    key = f"user:{user_id}:permissions"
    raw = await r.get(key)
    if raw is None:
        return None
    return set(json.loads(raw))


async def invalidate_user_permissions(user_id: str) -> None:
    r = await get_redis()
    if r is None:
        return
    await r.delete(f"user:{user_id}:permissions")


# ── Login lockout ────────────────────────────────────────────────────

_MAX_LOGIN_ATTEMPTS = 5
_LOCKOUT_WINDOW = 900  # 15 minutes


async def check_login_lockout(email: str, ip: str) -> bool:
    """Return True if the email+ip combo is locked out."""
    r = await get_redis()
    if r is None:
        return False
    key = f"login_lockout:{email}:{ip}"
    attempts = await r.get(key)
    return attempts is not None and int(attempts) >= _MAX_LOGIN_ATTEMPTS


async def record_failed_login(email: str, ip: str) -> None:
    r = await get_redis()
    if r is None:
        return
    key = f"login_lockout:{email}:{ip}"
    pipe = r.pipeline()
    pipe.incr(key)
    pipe.expire(key, _LOCKOUT_WINDOW)
    await pipe.execute()


async def clear_login_lockout(email: str, ip: str) -> None:
    r = await get_redis()
    if r is None:
        return
    await r.delete(f"login_lockout:{email}:{ip}")


# ── OTP store (optional Redis-backed, fallback to DB) ────────────────

_OTP_TTL = 600  # 10 minutes


async def store_otp(email: str, otp_hash: str) -> None:
    r = await get_redis()
    if r is None:
        return
    await r.set(f"otp:{email}", otp_hash, ex=_OTP_TTL)


async def get_stored_otp(email: str) -> str | None:
    r = await get_redis()
    if r is None:
        return None
    return await r.get(f"otp:{email}")


async def delete_otp(email: str) -> None:
    r = await get_redis()
    if r is None:
        return
    await r.delete(f"otp:{email}")
