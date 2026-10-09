"""Logout use case – revoke the refresh token."""

from __future__ import annotations

from app.core.exceptions import AuthError
from app.core.security import hash_refresh_token
from app.infrastructure.database.uow import SqlAlchemyUnitOfWork


async def logout(
    raw_refresh_token: str,
    uow: SqlAlchemyUnitOfWork,
) -> None:
    """Revoke the provided refresh token."""
    token_hash = hash_refresh_token(raw_refresh_token)
    existing = await uow.refresh_tokens.get_by_token_hash(token_hash)
    if existing is None:
        raise AuthError("Invalid refresh token.")
    await uow.refresh_tokens.revoke(existing.id)
    await uow.commit()
