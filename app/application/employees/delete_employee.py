"""Soft-delete employee use case."""

from __future__ import annotations

from datetime import UTC, datetime

from app.application.common.audit import write_audit
from app.core.dependencies import RequestContext
from app.core.exceptions import NotFoundError
from app.infrastructure.database.uow import SqlAlchemyUnitOfWork


async def soft_delete_employee(
    employee_id: str,
    uow: SqlAlchemyUnitOfWork,
    *,
    actor_id: str,
    ctx: RequestContext | None = None,
) -> None:
    employee = await uow.employees.get_by_id(employee_id)
    if employee is None:
        raise NotFoundError("Employee not found.")

    employee.deleted_at = datetime.now(UTC)
    employee.deleted_by = actor_id

    await uow.employees.update(employee)

    await write_audit(
        uow,
        actor_id=actor_id,
        action="employee.deleted",
        entity_type="employee",
        entity_id=employee.id,
        old={"employee_code": employee.employee_code, "email": employee.email},
        request_context=ctx,
    )

    await uow.commit()
