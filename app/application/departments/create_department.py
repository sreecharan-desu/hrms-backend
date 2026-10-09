"""Create department use case."""

from __future__ import annotations

from dataclasses import dataclass

from app.application.common.audit import write_audit
from app.core.dependencies import RequestContext
from app.core.exceptions import ConflictError, NotFoundError
from app.infrastructure.database.models.department import Department
from app.infrastructure.database.uow import SqlAlchemyUnitOfWork


@dataclass(frozen=True, slots=True)
class CreateDepartmentInput:
    name: str
    code: str
    parent_id: str | None = None
    head_employee_id: str | None = None


async def create_department(
    data: CreateDepartmentInput,
    uow: SqlAlchemyUnitOfWork,
    *,
    actor_id: str,
    ctx: RequestContext | None = None,
) -> Department:
    existing = await uow.departments.get_by_code(data.code)
    if existing:
        raise ConflictError("A department with this code already exists.")

    if data.parent_id:
        parent = await uow.departments.get_by_id(data.parent_id)
        if parent is None:
            raise NotFoundError("Parent department not found.")

    if data.head_employee_id:
        head = await uow.employees.get_by_id(data.head_employee_id)
        if head is None:
            raise NotFoundError("Head employee not found.")

    department = Department(
        name=data.name,
        code=data.code,
        parent_id=data.parent_id,
        head_employee_id=data.head_employee_id,
    )

    department = await uow.departments.create(department)

    await write_audit(
        uow,
        actor_id=actor_id,
        action="department.created",
        entity_type="department",
        entity_id=department.id,
        new={"name": department.name, "code": department.code},
        request_context=ctx,
    )

    await uow.commit()
    department = await uow.departments.get_by_id(department.id)  # type: ignore[assignment]
    return department
