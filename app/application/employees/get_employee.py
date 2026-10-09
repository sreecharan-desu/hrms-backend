"""Get single employee use case."""

from __future__ import annotations

from app.core.exceptions import NotFoundError
from app.infrastructure.database.models.employee import Employee
from app.infrastructure.database.uow import SqlAlchemyUnitOfWork


async def get_employee(
    employee_id: str,
    uow: SqlAlchemyUnitOfWork,
) -> Employee:
    employee = await uow.employees.get_by_id(employee_id)
    if employee is None:
        raise NotFoundError("Employee not found.")
    return employee
