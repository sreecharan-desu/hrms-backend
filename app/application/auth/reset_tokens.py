"""Hashing and validation helpers shared by the password reset use cases."""

from __future__ import annotations

import hashlib
import hmac
from datetime import UTC, datetime

from app.infrastructure.database.models.user import PasswordResetToken

OTP_TTL_MINUTES = 10
RESET_TOKEN_TTL_MINUTES = 15


def token_digest(kind: str, user_id: str, secret: str) -> str:
    """sha256 over kind + user id + secret, so a digest is bound to one user and one purpose."""
    return hashlib.sha256(f"{kind}:{user_id}:{secret}".encode()).hexdigest()


def _as_utc(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


def is_usable(token: PasswordResetToken | None, *, user_id: str, expected_digest: str) -> bool:
    """True only for an unused, unexpired token that belongs to *user_id*."""
    if token is None:
        return False
    if not hmac.compare_digest(token.token_hash, expected_digest):
        return False
    if not hmac.compare_digest(token.user_id, user_id):
        return False
    if token.used_at is not None:
        return False
    return _as_utc(token.expires_at) > datetime.now(UTC)
