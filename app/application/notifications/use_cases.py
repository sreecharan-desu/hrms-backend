"""Notification use cases – current user's notifications."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select, update

from app.core.exceptions import NotFoundError
from app.infrastructure.database.models.notification import Notification
from app.infrastructure.database.uow import SqlAlchemyUnitOfWork


@dataclass(frozen=True, slots=True)
class PaginatedNotifications:
    items: list[dict[str, Any]]
    total: int
    offset: int
    limit: int


async def list_notifications(
    uow: SqlAlchemyUnitOfWork,
    user_id: str,
    *,
    offset: int = 0,
    limit: int = 50,
) -> PaginatedNotifications:
    """List the current user's notifications (newest first)."""
    count_q = select(func.count(Notification.id)).where(Notification.user_id == user_id)
    total = (await uow.session.execute(count_q)).scalar_one()

    rows_q = (
        select(Notification)
        .where(Notification.user_id == user_id)
        .order_by(Notification.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    rows = (await uow.session.execute(rows_q)).scalars().all()

    items = [
        {
            "id": r.id,
            "title": r.title,
            "body": r.body,
            "channel": r.channel,
            "is_read": r.is_read,
            "read_at": r.read_at.isoformat() if r.read_at else None,
            "link": r.link,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]
    return PaginatedNotifications(items=items, total=total, offset=offset, limit=limit)


async def mark_read(
    uow: SqlAlchemyUnitOfWork,
    user_id: str,
    notification_id: str,
) -> dict[str, Any]:
    """Mark a single notification as read (owned by current user)."""
    stmt = select(Notification).where(
        Notification.id == notification_id,
        Notification.user_id == user_id,
    )
    result = await uow.session.execute(stmt)
    notif = result.scalars().first()
    if notif is None:
        raise NotFoundError("Notification not found.")

    if not notif.is_read:
        notif.is_read = True
        notif.read_at = datetime.now(UTC)

    await uow.commit()
    return {
        "id": notif.id,
        "is_read": notif.is_read,
        "read_at": notif.read_at.isoformat() if notif.read_at else None,
    }


async def mark_all_read(
    uow: SqlAlchemyUnitOfWork,
    user_id: str,
) -> int:
    """Mark all unread notifications as read for the current user. Returns count updated."""
    now = datetime.now(UTC)
    stmt = (
        update(Notification)
        .where(
            Notification.user_id == user_id,
            Notification.is_read.is_(False),
        )
        .values(is_read=True, read_at=now)
    )
    result = await uow.session.execute(stmt)
    await uow.commit()
    return result.rowcount  # type: ignore[return-value]
