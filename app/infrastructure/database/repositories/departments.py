"""Concrete SQLAlchemy department repository."""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.models.department import Department
from app.infrastructure.database.models.employee import Employee


class SqlDepartmentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _active_filter(self):
        return Department.deleted_at.is_(None)

    async def get_by_id(self, department_id: str) -> Department | None:
        result = await self._session.execute(
            select(Department).where(
                Department.id == department_id,
                self._active_filter(),
            )
        )
        return result.scalars().first()

    async def get_by_code(self, code: str) -> Department | None:
        result = await self._session.execute(
            select(Department).where(
                Department.code == code,
                self._active_filter(),
            )
        )
        return result.scalars().first()

    async def list_all(
        self,
        *,
        offset: int = 0,
        limit: int = 50,
        search: str | None = None,
    ) -> Sequence[Department]:
        stmt = select(Department).where(self._active_filter())
        if search:
            pattern = f"%{search}%"
            stmt = stmt.where(
                or_(
                    Department.name.ilike(pattern),
                    Department.code.ilike(pattern),
                )
            )
        stmt = stmt.order_by(Department.created_at.desc()).offset(offset).limit(limit)
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def count(self, *, search: str | None = None) -> int:
        stmt = select(func.count(Department.id)).where(self._active_filter())
        if search:
            pattern = f"%{search}%"
            stmt = stmt.where(
                or_(
                    Department.name.ilike(pattern),
                    Department.code.ilike(pattern),
                )
            )
        result = await self._session.execute(stmt)
        return result.scalar_one()

    async def create(self, department: Department) -> Department:
        self._session.add(department)
        await self._session.flush()
        return department

    async def update(self, department: Department) -> Department:
        await self._session.flush()
        return department

    async def get_children(self, parent_id: str) -> Sequence[Department]:
        result = await self._session.execute(
            select(Department).where(
                Department.parent_id == parent_id,
                self._active_filter(),
            ).order_by(Department.name)
        )
        return result.scalars().all()

    async def has_active_employees(self, department_id: str) -> bool:
        result = await self._session.execute(
            select(func.count(Employee.id)).where(
                Employee.department_id == department_id,
                Employee.deleted_at.is_(None),
            )
        )
        return result.scalar_one() > 0
