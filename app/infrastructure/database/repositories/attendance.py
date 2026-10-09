"""Concrete SQLAlchemy attendance repository."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.models.attendance import Attendance


class SqlAttendanceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, attendance_id: str) -> Attendance | None:
        result = await self._session.execute(
            select(Attendance).where(Attendance.id == attendance_id)
        )
        return result.scalars().first()

    async def get_by_employee_and_date(
        self, employee_id: str, work_date: date
    ) -> Attendance | None:
        result = await self._session.execute(
            select(Attendance).where(
                and_(
                    Attendance.employee_id == employee_id,
                    Attendance.work_date == work_date,
                )
            )
        )
        return result.scalars().first()

    def _apply_filters(self, stmt, *, employee_id, date_from, date_to):
        if employee_id is not None:
            stmt = stmt.where(Attendance.employee_id == employee_id)
        if date_from is not None:
            stmt = stmt.where(Attendance.work_date >= date_from)
        if date_to is not None:
            stmt = stmt.where(Attendance.work_date <= date_to)
        return stmt

    async def list_filtered(
        self,
        *,
        employee_id: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> Sequence[Attendance]:
        stmt = select(Attendance)
        stmt = self._apply_filters(
            stmt, employee_id=employee_id, date_from=date_from, date_to=date_to
        )
        stmt = stmt.order_by(Attendance.work_date.desc()).offset(offset).limit(limit)
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def count_filtered(
        self,
        *,
        employee_id: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> int:
        stmt = select(func.count(Attendance.id))
        stmt = self._apply_filters(
            stmt, employee_id=employee_id, date_from=date_from, date_to=date_to
        )
        result = await self._session.execute(stmt)
        return result.scalar_one()

    async def create(self, attendance: Attendance) -> Attendance:
        self._session.add(attendance)
        await self._session.flush()
        return attendance

    async def update(self, attendance: Attendance) -> Attendance:
        await self._session.flush()
        return attendance
