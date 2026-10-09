"""Shared audit-log helper – writes an AuditLog row inside the caller's session."""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import RequestContext
from app.infrastructure.database.models.audit import AuditLog
from app.infrastructure.database.uow import SqlAlchemyUnitOfWork


async def record_audit(
    session: AsyncSession,
    *,
    actor_id: str | None,
    action: str,
    entity_type: str,
    entity_id: str,
    old_values: dict[str, Any] | None = None,
    new_values: dict[str, Any] | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
    request_id: str | None = None,
) -> AuditLog:
    """Insert an audit row inside the given session (no commit)."""
    log = AuditLog(
        actor_id=actor_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        old_values=old_values,
        new_values=new_values,
        ip_address=ip_address,
        user_agent=user_agent,
        request_id=request_id,
    )
    session.add(log)
    await session.flush()
    return log


async def write_audit(
    uow: SqlAlchemyUnitOfWork,
    *,
    actor_id: str | None,
    action: str,
    entity_type: str,
    entity_id: str,
    old: dict[str, Any] | None = None,
    new: dict[str, Any] | None = None,
    request_context: RequestContext | None = None,
) -> AuditLog:
    """Convenience wrapper: insert audit row via UoW session."""
    return await record_audit(
        uow.session,
        actor_id=actor_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        old_values=old,
        new_values=new,
        ip_address=request_context.ip if request_context else None,
        user_agent=request_context.user_agent if request_context else None,
        request_id=request_context.request_id if request_context else None,
    )
