"""Update department (PATCH) use case."""

from __future__ import annotations

from typing import Any

from app.application.common.audit import write_audit
from app.core.dependencies import RequestContext
from app.core.exceptions import ConflictError, NotFoundError, ValidationAppError
from app.infrastructure.database.models.department import Department
from app.infrastructure.database.uow import SqlAlchemyUnitOfWork

ALLOWED_FIELDS = {"name", "code", "parent_id", "head_employee_id"}


async def _check_parent_cycle(
    uow: SqlAlchemyUnitOfWork,
    department_id: str,
    new_parent_id: str,
) -> None:
    """Walk the parent chain upward; error if we hit department_id."""
    visited: set[str] = set()
    current = new_parent_id
    while current:
        if current == department_id:
            raise ValidationAppError("Setting this parent would create a cycle.")
        if current in visited:
            break
        visited.add(current)
        parent = await uow.departments.get_by_id(current)
        current = parent.parent_id if parent else None


async def update_department(
    department_id: str,
    updates: dict[str, Any],
    uow: SqlAlchemyUnitOfWork,
    *,
    actor_id: str,
    ctx: RequestContext | None = None,
) -> Department:
    department = await uow.departments.get_by_id(department_id)
    if department is None:
        raise NotFoundError("Department not found.")

    old_values: dict[str, Any] = {}
    new_values: dict[str, Any] = {}

    for key, value in updates.items():
        if key not in ALLOWED_FIELDS:
            continue
        old_val = getattr(department, key, None)
        if old_val == value:
            continue

        if key == "code" and value is not None:
            dup = await uow.departments.get_by_code(value)
            if dup and dup.id != department_id:
                raise ConflictError("A department with this code already exists.")

        if key == "parent_id" and value is not None:
            parent = await uow.departments.get_by_id(value)
            if parent is None:
                raise NotFoundError("Parent department not found.")
            await _check_parent_cycle(uow, department_id, value)

        if key == "head_employee_id" and value is not None:
            head = await uow.employees.get_by_id(value)
            if head is None:
                raise NotFoundError("Head employee not found.")

        old_values[key] = str(old_val) if old_val is not None else None
        new_values[key] = str(value) if value is not None else None
        setattr(department, key, value)

    if new_values:
        department = await uow.departments.update(department)
        await write_audit(
            uow,
            actor_id=actor_id,
            action="department.updated",
            entity_type="department",
            entity_id=department.id,
            old=old_values,
            new=new_values,
            request_context=ctx,
        )
        await uow.commit()
        department = await uow.departments.get_by_id(department_id)  # type: ignore[assignment]

    return department
