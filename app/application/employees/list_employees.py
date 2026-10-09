"""List employees use case with pagination, search, and filtering."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from app.infrastructure.database.models.employee import Employee
from app.infrastructure.database.uow import SqlAlchemyUnitOfWork


@dataclass(frozen=True, slots=True)
class ListEmployeesResult:
    items: Sequence[Employee]
    total: int
    offset: int
    limit: int


async def list_employees(
    uow: SqlAlchemyUnitOfWork,
    *,
    offset: int = 0,
    limit: int = 50,
    search: str | None = None,
    department_id: str | None = None,
    status: str | None = None,
) -> ListEmployeesResult:
    limit = min(limit, 100)
    items = await uow.employees.list_all(
        offset=offset,
        limit=limit,
        search=search,
        department_id=department_id,
        status=status,
    )
    total = await uow.employees.count(
        search=search,
        department_id=department_id,
        status=status,
    )
    return ListEmployeesResult(items=items, total=total, offset=offset, limit=limit)
