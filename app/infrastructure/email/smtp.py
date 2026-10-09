"""SMTP email sending – logs in dev when SMTP_HOST is empty."""

from __future__ import annotations

import smtplib
from email.message import EmailMessage

import structlog

from app.core.config import get_settings

logger = structlog.stdlib.get_logger(__name__)


async def send_email(
    *,
    to: str,
    subject: str,
    body_text: str,
    body_html: str | None = None,
) -> None:
    """Send a single email.  Falls back to logging when SMTP is not configured."""
    settings = get_settings()

    if not settings.SMTP_HOST:
        await logger.ainfo(
            "email_stub",
            to=to,
            subject=subject,
            note="SMTP not configured – email logged only.",
        )
        return

    msg = EmailMessage()
    msg["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body_text)
    if body_html:
        msg.add_alternative(body_html, subtype="html")

    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as server:
            server.starttls()
            if settings.SMTP_USER:
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.send_message(msg)
        await logger.ainfo("email_sent", to=to, subject=subject)
    except Exception:
        await logger.aerror("email_send_failed", to=to, subject=subject, exc_info=True)
        raise
