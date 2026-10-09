"""Background job handlers keyed by job type string."""

from __future__ import annotations

from typing import Any

import structlog

logger = structlog.stdlib.get_logger(__name__)


async def handle_email_send(payload: dict[str, Any]) -> None:
    from app.infrastructure.email.smtp import send_email

    await send_email(
        to=payload["to"],
        subject=payload["subject"],
        body_text=payload["body_text"],
        body_html=payload.get("body_html"),
    )


async def handle_notification_create(payload: dict[str, Any]) -> None:
    """Persist an in-app notification from a background job."""
    from app.infrastructure.database.models.notification import Notification
    from app.infrastructure.database.session import async_session_factory

    async with async_session_factory() as session:
        notif = Notification(
            user_id=payload["user_id"],
            title=payload["title"],
            body=payload.get("body"),
            channel=payload.get("channel", "IN_APP"),
            link=payload.get("link"),
        )
        session.add(notif)
        await session.commit()
    await logger.ainfo("notification_created", user_id=payload["user_id"])


async def handle_sms_send(payload: dict[str, Any]) -> None:
    """SMS handler – no-op stub, logs the intent."""
    await logger.ainfo(
        "sms_stub",
        phone=payload.get("phone"),
        message=payload.get("message", "")[:80],
        note="SMS provider not integrated – logged only.",
    )


HANDLER_MAP: dict[str, Any] = {
    "email.send": handle_email_send,
    "notification.create": handle_notification_create,
    "sms.send": handle_sms_send,
}
