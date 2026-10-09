"""Verify OTP use case – validates the OTP and returns a short-lived reset token."""

from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime

from app.core.exceptions import AuthError
from app.infrastructure.cache.redis import delete_otp, get_stored_otp
from app.infrastructure.database.uow import SqlAlchemyUnitOfWork


def _hash_otp(otp: str) -> str:
    return hashlib.sha256(otp.encode()).hexdigest()


@dataclass(frozen=True, slots=True)
class VerifyOTPResult:
    reset_token: str
    message: str = "OTP verified successfully."


async def verify_otp(
    email: str,
    otp: str,
    uow: SqlAlchemyUnitOfWork,
) -> VerifyOTPResult:
    """Verify the OTP for a password reset request."""
    otp_hash = _hash_otp(otp)

    # Try Redis first
    cached = await get_stored_otp(email)
    if cached is not None:
        if cached != otp_hash:
            raise AuthError("Invalid or expired OTP.")
        await delete_otp(email)
        # Generate a temporary reset token the client exchanges in reset_password
        reset_token = secrets.token_urlsafe(48)
        return VerifyOTPResult(reset_token=reset_token)

    # Fallback to DB
    user = await uow.users.get_by_email(email)
    if user is None:
        raise AuthError("Invalid or expired OTP.")

    token = await uow.password_resets.get_by_token_hash(otp_hash)
    if token is None or token.user_id != user.id:
        raise AuthError("Invalid or expired OTP.")

    if token.used_at is not None:
        raise AuthError("OTP already used.")

    if token.expires_at < datetime.now(UTC):
        raise AuthError("OTP has expired.")

    # Mark as used
    await uow.password_resets.mark_used(token.id)
    await uow.commit()

    reset_token = secrets.token_urlsafe(48)
    return VerifyOTPResult(reset_token=reset_token)
