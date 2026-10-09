"""Reporting endpoints – /api/v1/reports/*."""

from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.core.dependencies import (
    CurrentUser,
    get_uow,
    require_permission,
)
from app.core.permissions import P
from app.core.responses import success_response
from app.infrastructure.database.uow import SqlAlchemyUnitOfWork

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.get("/headcount")
async def headcount_report(
    _user: Annotated[CurrentUser, Depends(require_permission(P.EMPLOYEE_READ))],
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
):
    """Active employee count grouped by department."""
    from sqlalchemy import func, select

    from app.infrastructure.database.models.department import Department
    from app.infrastructure.database.models.employee import Employee

    stmt = (
        select(
            Department.id.label("department_id"),
            Department.name.label("department_name"),
            func.count(Employee.id).label("headcount"),
        )
        .outerjoin(Employee, Employee.department_id == Department.id)
        .where(Employee.deleted_at.is_(None))
        .where(Employee.status == "ACTIVE")
        .group_by(Department.id, Department.name)
        .order_by(Department.name)
    )
    result = await uow.session.execute(stmt)
    rows = [
        {
            "department_id": r.department_id,
            "department_name": r.department_name,
            "headcount": r.headcount,
        }
        for r in result
    ]
    total = sum(r["headcount"] for r in rows)
    return success_response(data={"departments": rows, "total": total})


@router.get("/attendance-summary")
async def attendance_summary_report(
    _user: Annotated[CurrentUser, Depends(require_permission(P.ATTENDANCE_READ))],
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    date_from: date = Query(..., alias="from"),
    date_to: date = Query(..., alias="to"),
):
    """Attendance status counts within a date range."""
    from sqlalchemy import func, select

    from app.infrastructure.database.models.attendance import Attendance

    stmt = (
        select(
            Attendance.status,
            func.count(Attendance.id).label("count"),
        )
        .where(Attendance.work_date >= date_from)
        .where(Attendance.work_date <= date_to)
        .group_by(Attendance.status)
    )
    result = await uow.session.execute(stmt)
    rows = {r.status: r.count for r in result}
    return success_response(
        data={
            "from": date_from.isoformat(),
            "to": date_to.isoformat(),
            "statuses": rows,
            "total": sum(rows.values()),
        }
    )


@router.get("/leave-usage")
async def leave_usage_report(
    _user: Annotated[CurrentUser, Depends(require_permission(P.LEAVE_READ))],
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
):
    """Leave usage aggregated by leave type."""
    from sqlalchemy import func, select

    from app.infrastructure.database.models.leave import LeaveBalance, LeaveType

    stmt = (
        select(
            LeaveType.id.label("leave_type_id"),
            LeaveType.name.label("leave_type_name"),
            func.coalesce(func.sum(LeaveBalance.total_days), 0).label("total_allocated"),
            func.coalesce(func.sum(LeaveBalance.used_days), 0).label("total_used"),
            func.coalesce(func.sum(LeaveBalance.pending_days), 0).label("total_pending"),
        )
        .outerjoin(LeaveBalance, LeaveBalance.leave_type_id == LeaveType.id)
        .group_by(LeaveType.id, LeaveType.name)
        .order_by(LeaveType.name)
    )
    result = await uow.session.execute(stmt)
    rows = [
        {
            "leave_type_id": r.leave_type_id,
            "leave_type_name": r.leave_type_name,
            "total_allocated": str(r.total_allocated),
            "total_used": str(r.total_used),
            "total_pending": str(r.total_pending),
        }
        for r in result
    ]
    return success_response(data=rows)
