"""Password hashing (Argon2) and JWT token helpers."""

from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError

from app.core.config import get_settings

_ph = PasswordHasher()


# ── Password hashing ─────────────────────────────────────────────────

def hash_password(plain: str) -> str:
    """Return an Argon2id hash of *plain*."""
    return _ph.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """Return True when *plain* matches *hashed*; False otherwise."""
    try:
        return _ph.verify(hashed, plain)
    except VerificationError:
        return False


# ── JWT access tokens ────────────────────────────────────────────────

def create_access_token(
    subject: str,
    extra: dict[str, Any] | None = None,
    *,
    expires_delta: timedelta | None = None,
) -> str:
    settings = get_settings()
    now = datetime.now(UTC)
    expire = now + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    payload: dict[str, Any] = {
        "sub": subject,
        "iat": now,
        "exp": expire,
        "type": "access",
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    """Decode and validate an access token. Raises jwt.PyJWTError on failure."""
    settings = get_settings()
    payload: dict[str, Any] = jwt.decode(
        token,
        settings.JWT_SECRET_KEY,
        algorithms=[settings.JWT_ALGORITHM],
    )
    if payload.get("type") != "access":
        raise jwt.InvalidTokenError("Not an access token")
    return payload


# ── Opaque refresh tokens ────────────────────────────────────────────

def generate_refresh_token() -> str:
    """Generate a cryptographically random opaque refresh token."""
    return secrets.token_urlsafe(48)


def hash_refresh_token(token: str) -> str:
    """SHA-256 hash of the opaque token for safe DB storage."""
    return hashlib.sha256(token.encode()).hexdigest()
