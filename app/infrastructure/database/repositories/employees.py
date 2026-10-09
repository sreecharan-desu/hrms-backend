"""Concrete SQLAlchemy employee repositories."""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.infrastructure.database.models.employee import Employee, EmployeeCompensation


class SqlEmployeeRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _base_query(self):
        return select(Employee).options(selectinload(Employee.compensation))

    def _active_filter(self):
        return Employee.deleted_at.is_(None)

    async def get_by_id(self, employee_id: str) -> Employee | None:
        result = await self._session.execute(
            self._base_query().where(
                Employee.id == employee_id,
                self._active_filter(),
            )
        )
        return result.scalars().first()

    async def get_by_email(self, email: str) -> Employee | None:
        result = await self._session.execute(
            self._base_query().where(
                Employee.email == email,
                self._active_filter(),
            )
        )
        return result.scalars().first()

    async def get_by_employee_code(self, code: str) -> Employee | None:
        result = await self._session.execute(
            self._base_query().where(
                Employee.employee_code == code,
                self._active_filter(),
            )
        )
        return result.scalars().first()

    async def get_by_user_id(self, user_id: str) -> Employee | None:
        result = await self._session.execute(
            self._base_query().where(
                Employee.user_id == user_id,
                self._active_filter(),
            )
        )
        return result.scalars().first()

    def _apply_filters(self, stmt, *, search: str | None, department_id: str | None, status: str | None):
        stmt = stmt.where(self._active_filter())
        if search:
            pattern = f"%{search}%"
            stmt = stmt.where(
                or_(
                    Employee.first_name.ilike(pattern),
                    Employee.last_name.ilike(pattern),
                    Employee.email.ilike(pattern),
                    Employee.employee_code.ilike(pattern),
                )
            )
        if department_id:
            stmt = stmt.where(Employee.department_id == department_id)
        if status:
            stmt = stmt.where(Employee.status == status)
        return stmt

    async def list_all(
        self,
        *,
        offset: int = 0,
        limit: int = 50,
        search: str | None = None,
        department_id: str | None = None,
        status: str | None = None,
    ) -> Sequence[Employee]:
        stmt = self._apply_filters(
            self._base_query(),
            search=search,
            department_id=department_id,
            status=status,
        )
        stmt = stmt.order_by(Employee.created_at.desc()).offset(offset).limit(limit)
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def count(
        self,
        *,
        search: str | None = None,
        department_id: str | None = None,
        status: str | None = None,
    ) -> int:
        stmt = self._apply_filters(
            select(func.count(Employee.id)),
            search=search,
            department_id=department_id,
            status=status,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one()

    async def create(self, employee: Employee) -> Employee:
        self._session.add(employee)
        await self._session.flush()
        return employee

    async def update(self, employee: Employee) -> Employee:
        await self._session.flush()
        return employee

    async def get_direct_reports(self, manager_id: str) -> Sequence[Employee]:
        result = await self._session.execute(
            self._base_query().where(
                Employee.manager_id == manager_id,
                self._active_filter(),
            )
        )
        return result.scalars().all()

    async def get_by_id_include_deleted(self, employee_id: str) -> Employee | None:
        """Used for manager cycle detection – includes soft-deleted rows."""
        result = await self._session.execute(
            self._base_query().where(Employee.id == employee_id)
        )
        return result.scalars().first()


class SqlEmployeeCompensationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_employee_id(self, employee_id: str) -> EmployeeCompensation | None:
        result = await self._session.execute(
            select(EmployeeCompensation).where(
                EmployeeCompensation.employee_id == employee_id
            )
        )
        return result.scalars().first()

    async def upsert(self, comp: EmployeeCompensation) -> EmployeeCompensation:
        existing = await self.get_by_employee_id(comp.employee_id)
        if existing:
            existing.salary = comp.salary
            existing.currency = comp.currency
            existing.effective_from = comp.effective_from
        else:
            self._session.add(comp)
        await self._session.flush()
        return existing or comp
