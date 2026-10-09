"""Get child departments use case."""

from __future__ import annotations

from collections.abc import Sequence

from app.core.exceptions import NotFoundError
from app.infrastructure.database.models.department import Department
from app.infrastructure.database.uow import SqlAlchemyUnitOfWork


async def get_department_children(
    department_id: str,
    uow: SqlAlchemyUnitOfWork,
) -> Sequence[Department]:
    department = await uow.departments.get_by_id(department_id)
    if department is None:
        raise NotFoundError("Department not found.")
    return await uow.departments.get_children(department_id)
