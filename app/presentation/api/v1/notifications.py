"""Notification endpoints – /api/v1/notifications/*."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.application.notifications.use_cases import list_notifications, mark_all_read, mark_read
from app.core.dependencies import CurrentUser, get_current_user, get_uow
from app.core.responses import success_response
from app.infrastructure.database.uow import SqlAlchemyUnitOfWork

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("", summary="List my notifications")
async def list_notifications_endpoint(
    user: Annotated[CurrentUser, Depends(get_current_user)],
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
):
    result = await list_notifications(uow, user.id, offset=offset, limit=limit)
    return success_response(
        data={
            "items": result.items,
            "total": result.total,
            "offset": result.offset,
            "limit": result.limit,
        }
    )


@router.post("/{notification_id}/read", summary="Mark notification as read")
async def mark_read_endpoint(
    notification_id: str,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
):
    data = await mark_read(uow, user.id, notification_id)
    return success_response(data=data, message="Notification marked as read.")


@router.post("/read-all", summary="Mark all notifications as read")
async def mark_all_read_endpoint(
    user: Annotated[CurrentUser, Depends(get_current_user)],
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
):
    count = await mark_all_read(uow, user.id)
    return success_response(data={"updated": count}, message="All notifications marked as read.")
