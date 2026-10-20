"""Verify OTP use case – validates the OTP and returns a short-lived reset token."""

from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from app.application.auth.reset_tokens import (
    RESET_TOKEN_TTL_MINUTES,
    is_usable,
    token_digest,
)
from app.core.exceptions import AuthError
from app.infrastructure.database.models.user import PasswordResetToken
from app.infrastructure.database.uow import SqlAlchemyUnitOfWork

_INVALID = "Invalid or expired OTP."


@dataclass(frozen=True, slots=True)
class VerifyOTPResult:
    reset_token: str
    message: str = "OTP verified successfully."


async def verify_otp(
    email: str,
    otp: str,
    uow: SqlAlchemyUnitOfWork,
) -> VerifyOTPResult:
    """Consume a valid OTP and issue a single-use reset token bound to the user."""
    user = await uow.users.get_by_email(email)
    if user is None:
        raise AuthError(_INVALID)

    expected = token_digest("otp", user.id, otp)
    token = await uow.password_resets.get_by_token_hash(expected)
    if not is_usable(token, user_id=user.id, expected_digest=expected):
        raise AuthError(_INVALID)
    assert token is not None
    await uow.password_resets.mark_used(token.id)

    reset_token = secrets.token_urlsafe(48)
    await uow.password_resets.create(
        PasswordResetToken(
            token_hash=token_digest("reset", user.id, reset_token),
            user_id=user.id,
            expires_at=datetime.now(UTC) + timedelta(minutes=RESET_TOKEN_TTL_MINUTES),
        )
    )
    await uow.commit()
    return VerifyOTPResult(reset_token=reset_token)
