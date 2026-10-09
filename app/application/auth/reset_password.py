"""Reset password use case – set new password, revoke all refresh tokens."""

from __future__ import annotations

from app.core.exceptions import AuthError
from app.core.security import hash_password
from app.infrastructure.cache.redis import invalidate_user_permissions
from app.infrastructure.database.uow import SqlAlchemyUnitOfWork


async def reset_password(
    email: str,
    new_password: str,
    uow: SqlAlchemyUnitOfWork,
) -> None:
    """Set a new password for the user and revoke all sessions."""
    user = await uow.users.get_by_email(email)
    if user is None:
        raise AuthError("User not found.")

    user.password_hash = hash_password(new_password)

    # Revoke all refresh tokens to force re-login everywhere
    await uow.refresh_tokens.revoke_all_for_user(user.id)

    # Invalidate any remaining password reset tokens
    await uow.password_resets.invalidate_all_for_user(user.id)

    await uow.commit()
    await invalidate_user_permissions(user.id)
