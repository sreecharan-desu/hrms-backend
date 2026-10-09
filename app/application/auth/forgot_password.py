"""Forgot password – generate OTP, store hashed, enqueue email job."""

from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime, timedelta

from app.infrastructure.cache.redis import store_otp
from app.infrastructure.database.models.jobs import BackgroundJob
from app.infrastructure.database.models.user import PasswordResetToken
from app.infrastructure.database.uow import SqlAlchemyUnitOfWork


def _generate_otp(length: int = 6) -> str:
    """Generate a numeric OTP string."""
    return "".join(str(secrets.randbelow(10)) for _ in range(length))


def _hash_otp(otp: str) -> str:
    return hashlib.sha256(otp.encode()).hexdigest()


async def forgot_password(
    email: str,
    uow: SqlAlchemyUnitOfWork,
) -> None:
    """Create an OTP for password reset and enqueue a notification email.

    Always returns success to prevent email enumeration.
    """
    user = await uow.users.get_by_email(email)
    if user is None:
        return  # silent – no enumeration

    # Invalidate old tokens
    await uow.password_resets.invalidate_all_for_user(user.id)

    otp = _generate_otp()
    otp_hash = _hash_otp(otp)

    # Store in DB
    token = PasswordResetToken(
        token_hash=otp_hash,
        user_id=user.id,
        expires_at=datetime.now(UTC) + timedelta(minutes=10),
    )
    await uow.password_resets.create(token)

    # Store in Redis for fast lookup
    await store_otp(email, otp_hash)

    # Enqueue email via background_jobs outbox
    job = BackgroundJob(
        type="SEND_PASSWORD_RESET_EMAIL",
        payload={"email": email, "otp": otp, "user_id": user.id},
        status="PENDING",
        available_at=datetime.now(UTC),
    )
    uow.session.add(job)
    await uow.commit()
