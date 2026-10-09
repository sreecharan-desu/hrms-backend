"""Refresh-token rotation with reuse detection."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from app.core.config import get_settings
from app.core.exceptions import AuthError
from app.core.security import (
    create_access_token,
    generate_refresh_token,
    hash_refresh_token,
)
from app.infrastructure.database.models.user import RefreshToken
from app.infrastructure.database.uow import SqlAlchemyUnitOfWork


@dataclass(frozen=True, slots=True)
class RefreshResult:
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 0


async def rotate_refresh_token(
    raw_token: str,
    uow: SqlAlchemyUnitOfWork,
) -> RefreshResult:
    """Rotate refresh token; detect reuse and revoke the family."""
    token_hash = hash_refresh_token(raw_token)
    existing = await uow.refresh_tokens.get_by_token_hash(token_hash)

    if existing is None:
        raise AuthError("Invalid refresh token.")

    # Reuse detection: token was already consumed → compromise assumed
    if existing.revoked_at is not None:
        await uow.refresh_tokens.revoke_family(existing.family_id)
        await uow.commit()
        raise AuthError("Refresh token reuse detected. All sessions revoked.")

    if existing.expires_at < datetime.now(UTC):
        raise AuthError("Refresh token expired.")

    # Revoke old token
    new_raw = generate_refresh_token()
    new_id = str(uuid.uuid4())
    await uow.refresh_tokens.revoke(existing.id, replaced_by=new_id)

    settings = get_settings()
    new_row = RefreshToken(
        id=new_id,
        token_hash=hash_refresh_token(new_raw),
        user_id=existing.user_id,
        family_id=existing.family_id,
        expires_at=datetime.now(UTC) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )
    await uow.refresh_tokens.create(new_row)

    # Fetch user for access token claims
    user = await uow.users.get_by_id(existing.user_id)
    if user is None:
        raise AuthError("User no longer exists.")

    role_names = [r.name for r in user.roles]
    access_token = create_access_token(
        subject=user.id,
        extra={"email": user.email, "roles": role_names},
    )
    await uow.commit()

    return RefreshResult(
        access_token=access_token,
        refresh_token=new_raw,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
