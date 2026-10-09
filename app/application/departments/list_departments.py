"""List departments use case."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from app.infrastructure.database.models.department import Department
from app.infrastructure.database.uow import SqlAlchemyUnitOfWork


@dataclass(frozen=True, slots=True)
class ListDepartmentsResult:
    items: Sequence[Department]
    total: int
    offset: int
    limit: int


async def list_departments(
    uow: SqlAlchemyUnitOfWork,
    *,
    offset: int = 0,
    limit: int = 50,
    search: str | None = None,
) -> ListDepartmentsResult:
    limit = min(limit, 100)
    items = await uow.departments.list_all(offset=offset, limit=limit, search=search)
    total = await uow.departments.count(search=search)
    return ListDepartmentsResult(items=items, total=total, offset=offset, limit=limit)
