"""Update employee (PATCH) use case."""

from __future__ import annotations

from typing import Any

from app.application.common.audit import write_audit
from app.core.dependencies import RequestContext
from app.core.exceptions import ConflictError, NotFoundError, ValidationAppError
from app.infrastructure.database.models.employee import Employee
from app.infrastructure.database.uow import SqlAlchemyUnitOfWork

ALLOWED_FIELDS = {
    "first_name",
    "last_name",
    "email",
    "phone",
    "date_of_birth",
    "joining_date",
    "status",
    "department_id",
    "designation",
    "manager_id",
    "location",
    "emergency_contact",
    "profile",
    "user_id",
}


async def _check_manager_cycle(
    uow: SqlAlchemyUnitOfWork,
    employee_id: str,
    new_manager_id: str,
) -> None:
    """Walk the manager chain from new_manager_id upward; error if we hit employee_id."""
    visited: set[str] = set()
    current = new_manager_id
    while current:
        if current == employee_id:
            raise ValidationAppError("Setting this manager would create a cycle.")
        if current in visited:
            break
        visited.add(current)
        mgr = await uow.employees.get_by_id(current)
        current = mgr.manager_id if mgr else None


async def update_employee(
    employee_id: str,
    updates: dict[str, Any],
    uow: SqlAlchemyUnitOfWork,
    *,
    actor_id: str,
    ctx: RequestContext | None = None,
) -> Employee:
    employee = await uow.employees.get_by_id(employee_id)
    if employee is None:
        raise NotFoundError("Employee not found.")

    old_values: dict[str, Any] = {}
    new_values: dict[str, Any] = {}

    for key, value in updates.items():
        if key not in ALLOWED_FIELDS:
            continue
        old_val = getattr(employee, key, None)
        if old_val == value:
            continue

        # Unique email check
        if key == "email":
            dup = await uow.employees.get_by_email(value)
            if dup and dup.id != employee_id:
                raise ConflictError("An employee with this email already exists.")

        # Department must exist
        if key == "department_id" and value is not None:
            dept = await uow.departments.get_by_id(value)
            if dept is None:
                raise NotFoundError("Department not found or has been deleted.")

        # Manager must exist + no cycle
        if key == "manager_id" and value is not None:
            mgr = await uow.employees.get_by_id(value)
            if mgr is None:
                raise NotFoundError("Manager not found.")
            await _check_manager_cycle(uow, employee_id, value)

        old_values[key] = str(old_val) if old_val is not None else None
        new_values[key] = str(value) if value is not None else None
        setattr(employee, key, value)

    if new_values:
        employee = await uow.employees.update(employee)
        await write_audit(
            uow,
            actor_id=actor_id,
            action="employee.updated",
            entity_type="employee",
            entity_id=employee.id,
            old=old_values,
            new=new_values,
            request_context=ctx,
        )
        await uow.commit()
        # Re-fetch to avoid MissingGreenlet on lazy attrs after commit
        employee = await uow.employees.get_by_id(employee_id)  # type: ignore[assignment]

    return employee
