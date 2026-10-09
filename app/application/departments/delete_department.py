"""Soft-delete department use case."""

from __future__ import annotations

from datetime import UTC, datetime

from app.application.common.audit import write_audit
from app.core.dependencies import RequestContext
from app.core.exceptions import ConflictError, NotFoundError
from app.infrastructure.database.uow import SqlAlchemyUnitOfWork


async def soft_delete_department(
    department_id: str,
    uow: SqlAlchemyUnitOfWork,
    *,
    actor_id: str,
    ctx: RequestContext | None = None,
) -> None:
    department = await uow.departments.get_by_id(department_id)
    if department is None:
        raise NotFoundError("Department not found.")

    if await uow.departments.has_active_employees(department_id):
        raise ConflictError(
            "Cannot delete department with active employees. "
            "Reassign or remove employees first."
        )

    department.deleted_at = datetime.now(UTC)
    department.deleted_by = actor_id

    await uow.departments.update(department)

    await write_audit(
        uow,
        actor_id=actor_id,
        action="department.deleted",
        entity_type="department",
        entity_id=department.id,
        old={"name": department.name, "code": department.code},
        request_context=ctx,
    )

    await uow.commit()
