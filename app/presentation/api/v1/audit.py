"""Audit log endpoints – /api/v1/audit-logs."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select

from app.core.dependencies import CurrentUser, get_uow, require_permission
from app.core.permissions import P
from app.core.responses import success_response
from app.infrastructure.database.models.audit import AuditLog
from app.infrastructure.database.uow import SqlAlchemyUnitOfWork

router = APIRouter(prefix="/audit-logs", tags=["Audit"])


@router.get("", summary="List audit logs")
async def list_audit_logs_endpoint(
    _user: Annotated[CurrentUser, Depends(require_permission(P.AUDIT_READ))],
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    entity_type: str | None = Query(None),
    actor_id: str | None = Query(None),
    action: str | None = Query(None),
):
    base = select(AuditLog)
    count_base = select(func.count(AuditLog.id))

    if entity_type:
        base = base.where(AuditLog.entity_type == entity_type)
        count_base = count_base.where(AuditLog.entity_type == entity_type)
    if actor_id:
        base = base.where(AuditLog.actor_id == actor_id)
        count_base = count_base.where(AuditLog.actor_id == actor_id)
    if action:
        base = base.where(AuditLog.action == action)
        count_base = count_base.where(AuditLog.action == action)

    total = (await uow.session.execute(count_base)).scalar_one()
    rows = (
        await uow.session.execute(
            base.order_by(AuditLog.created_at.desc()).offset(offset).limit(limit)
        )
    ).scalars().all()

    items = [
        {
            "id": r.id,
            "actor_id": r.actor_id,
            "action": r.action,
            "entity_type": r.entity_type,
            "entity_id": r.entity_id,
            "old_values": r.old_values,
            "new_values": r.new_values,
            "ip_address": r.ip_address,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]
    return success_response(
        data={
            "items": items,
            "total": total,
            "offset": offset,
            "limit": limit,
        }
    )
