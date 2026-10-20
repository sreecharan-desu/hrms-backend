"""Reset password use case – set new password, revoke all refresh tokens."""

from __future__ import annotations

from app.application.auth.reset_tokens import is_usable, token_digest
from app.core.exceptions import AuthError
from app.core.security import hash_password
from app.infrastructure.cache.redis import invalidate_user_permissions
from app.infrastructure.database.uow import SqlAlchemyUnitOfWork

_INVALID = "Invalid or expired reset token."


async def reset_password(
    email: str,
    reset_token: str,
    new_password: str,
    uow: SqlAlchemyUnitOfWork,
) -> None:
    """Set a new password using a reset token from verify_otp, then revoke all sessions."""
    user = await uow.users.get_by_email(email)
    if user is None:
        raise AuthError(_INVALID)

    expected = token_digest("reset", user.id, reset_token)
    token = await uow.password_resets.get_by_token_hash(expected)
    if not is_usable(token, user_id=user.id, expected_digest=expected):
        raise AuthError(_INVALID)
    assert token is not None
    await uow.password_resets.mark_used(token.id)

    user.password_hash = hash_password(new_password)

    # Revoke all refresh tokens to force re-login everywhere
    await uow.refresh_tokens.revoke_all_for_user(user.id)

    # Invalidate any remaining password reset tokens
    await uow.password_resets.invalidate_all_for_user(user.id)

    await uow.commit()
    await invalidate_user_permissions(user.id)
