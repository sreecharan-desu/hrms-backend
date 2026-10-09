"""Nested resource reads for an employee: attendance, leave, documents, performance.

These query the ORM models directly.  If the underlying repos/models are
not yet wired up the functions return empty paginated results with the
correct shape.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.infrastructure.database.models.attendance import Attendance
from app.infrastructure.database.models.document import Document
from app.infrastructure.database.models.employee import Employee
from app.infrastructure.database.models.leave import LeaveRequest
from app.infrastructure.database.models.performance import PerformanceReview
from app.infrastructure.database.uow import SqlAlchemyUnitOfWork


@dataclass(frozen=True, slots=True)
class PaginatedNested:
    items: list[dict[str, Any]]
    total: int
    offset: int
    limit: int


async def _ensure_employee(session: AsyncSession, employee_id: str) -> None:
    result = await session.execute(
        select(Employee.id).where(Employee.id == employee_id, Employee.deleted_at.is_(None))
    )
    if result.scalars().first() is None:
        raise NotFoundError("Employee not found.")


async def get_employee_attendance(
    employee_id: str,
    uow: SqlAlchemyUnitOfWork,
    *,
    offset: int = 0,
    limit: int = 50,
) -> PaginatedNested:
    await _ensure_employee(uow.session, employee_id)

    count_q = select(func.count(Attendance.id)).where(Attendance.employee_id == employee_id)
    total = (await uow.session.execute(count_q)).scalar_one()

    rows_q = (
        select(Attendance)
        .where(Attendance.employee_id == employee_id)
        .order_by(Attendance.work_date.desc())
        .offset(offset)
        .limit(limit)
    )
    rows = (await uow.session.execute(rows_q)).scalars().all()
    items = [
        {
            "id": r.id,
            "work_date": r.work_date.isoformat() if r.work_date else None,
            "check_in": r.check_in.isoformat() if r.check_in else None,
            "check_out": r.check_out.isoformat() if r.check_out else None,
            "status": r.status,
            "source": r.source,
        }
        for r in rows
    ]
    return PaginatedNested(items=items, total=total, offset=offset, limit=limit)


async def get_employee_leave(
    employee_id: str,
    uow: SqlAlchemyUnitOfWork,
    *,
    offset: int = 0,
    limit: int = 50,
) -> PaginatedNested:
    await _ensure_employee(uow.session, employee_id)

    count_q = select(func.count(LeaveRequest.id)).where(
        LeaveRequest.employee_id == employee_id
    )
    total = (await uow.session.execute(count_q)).scalar_one()

    rows_q = (
        select(LeaveRequest)
        .where(LeaveRequest.employee_id == employee_id)
        .order_by(LeaveRequest.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    rows = (await uow.session.execute(rows_q)).scalars().all()
    items = [
        {
            "id": r.id,
            "leave_type_id": r.leave_type_id,
            "start_date": r.start_date.isoformat() if r.start_date else None,
            "end_date": r.end_date.isoformat() if r.end_date else None,
            "days": str(r.days),
            "status": r.status,
            "reason": r.reason,
        }
        for r in rows
    ]
    return PaginatedNested(items=items, total=total, offset=offset, limit=limit)


async def get_employee_documents(
    employee_id: str,
    uow: SqlAlchemyUnitOfWork,
    *,
    offset: int = 0,
    limit: int = 50,
) -> PaginatedNested:
    await _ensure_employee(uow.session, employee_id)

    count_q = select(func.count(Document.id)).where(Document.employee_id == employee_id)
    total = (await uow.session.execute(count_q)).scalar_one()

    rows_q = (
        select(Document)
        .where(Document.employee_id == employee_id)
        .order_by(Document.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    rows = (await uow.session.execute(rows_q)).scalars().all()
    items = [
        {
            "id": r.id,
            "filename": r.filename,
            "content_type": r.content_type,
            "size_bytes": r.size_bytes,
            "status": r.status,
        }
        for r in rows
    ]
    return PaginatedNested(items=items, total=total, offset=offset, limit=limit)


async def get_employee_performance(
    employee_id: str,
    uow: SqlAlchemyUnitOfWork,
    *,
    offset: int = 0,
    limit: int = 50,
) -> PaginatedNested:
    await _ensure_employee(uow.session, employee_id)

    count_q = select(func.count(PerformanceReview.id)).where(
        PerformanceReview.employee_id == employee_id
    )
    total = (await uow.session.execute(count_q)).scalar_one()

    rows_q = (
        select(PerformanceReview)
        .where(PerformanceReview.employee_id == employee_id)
        .order_by(PerformanceReview.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    rows = (await uow.session.execute(rows_q)).scalars().all()
    items = [
        {
            "id": r.id,
            "cycle_id": r.cycle_id,
            "status": r.status,
            "self_rating": str(r.self_rating) if r.self_rating else None,
            "manager_rating": str(r.manager_rating) if r.manager_rating else None,
            "final_rating": str(r.final_rating) if r.final_rating else None,
        }
        for r in rows
    ]
    return PaginatedNested(items=items, total=total, offset=offset, limit=limit)
