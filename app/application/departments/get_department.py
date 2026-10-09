"""Get single department use case."""

from __future__ import annotations

from app.core.exceptions import NotFoundError
from app.infrastructure.database.models.department import Department
from app.infrastructure.database.uow import SqlAlchemyUnitOfWork


async def get_department(
    department_id: str,
    uow: SqlAlchemyUnitOfWork,
) -> Department:
    department = await uow.departments.get_by_id(department_id)
    if department is None:
        raise NotFoundError("Department not found.")
    return department
