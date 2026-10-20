"""Forgot password – generate OTP, store hashed, enqueue email job."""

from __future__ import annotations

import secrets
from datetime import UTC, datetime, timedelta

from app.application.auth.reset_tokens import OTP_TTL_MINUTES, token_digest
from app.core.config import get_settings
from app.infrastructure.database.models.jobs import BackgroundJob
from app.infrastructure.database.models.user import PasswordResetToken
from app.infrastructure.database.uow import SqlAlchemyUnitOfWork


def _generate_otp(length: int = 6) -> str:
    """Generate a numeric OTP string."""
    return "".join(str(secrets.randbelow(10)) for _ in range(length))


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

    # Only the newest OTP is valid.
    await uow.password_resets.invalidate_all_for_user(user.id)

    otp = _generate_otp()
    token = PasswordResetToken(
        token_hash=token_digest("otp", user.id, otp),
        user_id=user.id,
        expires_at=datetime.now(UTC) + timedelta(minutes=OTP_TTL_MINUTES),
    )
    await uow.password_resets.create(token)

    app_name = get_settings().APP_NAME
    job = BackgroundJob(
        type="email.send",  # handled by app.infrastructure.jobs.handlers
        payload={
            "to": email,
            "subject": f"{app_name} password reset code",
            "body_text": (
                f"Your {app_name} password reset code is {otp}. "
                f"It expires in {OTP_TTL_MINUTES} minutes. "
                "If you did not request this, you can ignore this email."
            ),
        },
        status="PENDING",
        available_at=datetime.now(UTC),
    )
    uow.session.add(job)
    await uow.commit()
