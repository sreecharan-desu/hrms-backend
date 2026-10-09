"""Attendance use cases – check-in, check-out, list, manual entry, update."""

from __future__ import annotations

import zoneinfo
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any

from app.application.common.audit import record_audit
from app.core.config import get_settings
from app.core.dependencies import CurrentUser, RequestContext
from app.core.exceptions import ConflictError, NotFoundError
from app.domain.attendance.enums import AttendanceSource, AttendanceStatus
from app.infrastructure.database.models.attendance import Attendance
from app.infrastructure.database.uow import SqlAlchemyUnitOfWork


def _today_in_app_tz() -> date:
    tz = zoneinfo.ZoneInfo(get_settings().APP_TIMEZONE)
    return datetime.now(tz).date()


# ── DTOs ─────────────────────────────────────────────────────────────

@dataclass(frozen=True, slots=True)
class AttendanceDTO:
    id: str
    employee_id: str
    work_date: str
    check_in: str | None
    check_out: str | None
    status: str
    source: str
    remarks: str | None
    created_at: str
    updated_at: str


def _to_dto(a: Attendance) -> AttendanceDTO:
    return AttendanceDTO(
        id=a.id,
        employee_id=a.employee_id,
        work_date=a.work_date.isoformat(),
        check_in=a.check_in.isoformat() if a.check_in else None,
        check_out=a.check_out.isoformat() if a.check_out else None,
        status=a.status,
        source=a.source,
        remarks=a.remarks,
        created_at=a.created_at.isoformat() if a.created_at else "",
        updated_at=a.updated_at.isoformat() if a.updated_at else "",
    )


@dataclass(frozen=True, slots=True)
class ListAttendanceResult:
    items: list[AttendanceDTO]
    total: int
    offset: int
    limit: int


# ── Check-in ─────────────────────────────────────────────────────────

async def check_in(
    uow: SqlAlchemyUnitOfWork,
    user: CurrentUser,
    employee_id: str,
    ctx: RequestContext,
) -> AttendanceDTO:
    work_date = _today_in_app_tz()
    existing = await uow.attendances.get_by_employee_and_date(employee_id, work_date)
    if existing is not None:
        raise ConflictError("Check-in already recorded for today.")

    now_utc = datetime.now(UTC)
    attendance = Attendance(
        employee_id=employee_id,
        work_date=work_date,
        check_in=now_utc,
        status=AttendanceStatus.PRESENT,
        source=AttendanceSource.SELF,
    )
    await uow.attendances.create(attendance)
    await record_audit(
        uow.session,
        actor_id=user.id,
        action="attendance.check_in",
        entity_type="Attendance",
        entity_id=attendance.id,
        new_values={"employee_id": employee_id, "work_date": work_date.isoformat()},
        ip_address=ctx.ip,
        user_agent=ctx.user_agent,
        request_id=ctx.request_id,
    )
    await uow.commit()
    return _to_dto(attendance)


# ── Check-out ────────────────────────────────────────────────────────

async def check_out(
    uow: SqlAlchemyUnitOfWork,
    user: CurrentUser,
    employee_id: str,
    ctx: RequestContext,
) -> AttendanceDTO:
    work_date = _today_in_app_tz()
    attendance = await uow.attendances.get_by_employee_and_date(employee_id, work_date)
    if attendance is None or attendance.check_in is None:
        raise NotFoundError("No open check-in found for today.")
    if attendance.check_out is not None:
        raise ConflictError("Already checked out for today.")

    attendance.check_out = datetime.now(UTC)
    await uow.attendances.update(attendance)
    await record_audit(
        uow.session,
        actor_id=user.id,
        action="attendance.check_out",
        entity_type="Attendance",
        entity_id=attendance.id,
        new_values={"check_out": attendance.check_out.isoformat()},
        ip_address=ctx.ip,
        user_agent=ctx.user_agent,
        request_id=ctx.request_id,
    )
    await uow.commit()
    return _to_dto(attendance)


# ── List attendance ──────────────────────────────────────────────────

async def list_attendance(
    uow: SqlAlchemyUnitOfWork,
    *,
    employee_id: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    offset: int = 0,
    limit: int = 50,
) -> ListAttendanceResult:
    items = await uow.attendances.list_filtered(
        employee_id=employee_id,
        date_from=date_from,
        date_to=date_to,
        offset=offset,
        limit=limit,
    )
    total = await uow.attendances.count_filtered(
        employee_id=employee_id,
        date_from=date_from,
        date_to=date_to,
    )
    return ListAttendanceResult(
        items=[_to_dto(a) for a in items],
        total=total,
        offset=offset,
        limit=limit,
    )


# ── Get by employee ─────────────────────────────────────────────────

async def get_employee_attendance(
    uow: SqlAlchemyUnitOfWork,
    employee_id: str,
    *,
    date_from: date | None = None,
    date_to: date | None = None,
    offset: int = 0,
    limit: int = 50,
) -> ListAttendanceResult:
    return await list_attendance(
        uow,
        employee_id=employee_id,
        date_from=date_from,
        date_to=date_to,
        offset=offset,
        limit=limit,
    )


# ── Manual entry (requires attendance.update) ────────────────────────

@dataclass(frozen=True, slots=True)
class ManualAttendanceInput:
    employee_id: str
    work_date: date
    check_in: datetime | None = None
    check_out: datetime | None = None
    status: str = AttendanceStatus.PRESENT
    remarks: str | None = None


async def create_manual_attendance(
    uow: SqlAlchemyUnitOfWork,
    user: CurrentUser,
    data: ManualAttendanceInput,
    ctx: RequestContext,
) -> AttendanceDTO:
    existing = await uow.attendances.get_by_employee_and_date(
        data.employee_id, data.work_date
    )
    if existing is not None:
        raise ConflictError("Attendance record already exists for this date.")

    attendance = Attendance(
        employee_id=data.employee_id,
        work_date=data.work_date,
        check_in=data.check_in,
        check_out=data.check_out,
        status=data.status,
        source=AttendanceSource.MANUAL,
        remarks=data.remarks,
    )
    await uow.attendances.create(attendance)
    await record_audit(
        uow.session,
        actor_id=user.id,
        action="attendance.manual_create",
        entity_type="Attendance",
        entity_id=attendance.id,
        new_values={
            "employee_id": data.employee_id,
            "work_date": data.work_date.isoformat(),
            "status": data.status,
        },
        ip_address=ctx.ip,
        user_agent=ctx.user_agent,
        request_id=ctx.request_id,
    )
    await uow.commit()
    return _to_dto(attendance)


# ── Update attendance ────────────────────────────────────────────────

@dataclass(frozen=True, slots=True)
class UpdateAttendanceInput:
    check_in: datetime | None = None
    check_out: datetime | None = None
    status: str | None = None
    remarks: str | None = None


async def update_attendance(
    uow: SqlAlchemyUnitOfWork,
    user: CurrentUser,
    attendance_id: str,
    data: UpdateAttendanceInput,
    ctx: RequestContext,
) -> AttendanceDTO:
    attendance = await uow.attendances.get_by_id(attendance_id)
    if attendance is None:
        raise NotFoundError("Attendance record not found.")

    old_values: dict[str, Any] = {}
    new_values: dict[str, Any] = {}

    if data.check_in is not None:
        old_values["check_in"] = attendance.check_in.isoformat() if attendance.check_in else None
        attendance.check_in = data.check_in
        new_values["check_in"] = data.check_in.isoformat()
    if data.check_out is not None:
        old_values["check_out"] = (
            attendance.check_out.isoformat() if attendance.check_out else None
        )
        attendance.check_out = data.check_out
        new_values["check_out"] = data.check_out.isoformat()
    if data.status is not None:
        old_values["status"] = attendance.status
        attendance.status = data.status
        new_values["status"] = data.status
    if data.remarks is not None:
        old_values["remarks"] = attendance.remarks
        attendance.remarks = data.remarks
        new_values["remarks"] = data.remarks

    await uow.attendances.update(attendance)
    await record_audit(
        uow.session,
        actor_id=user.id,
        action="attendance.update",
        entity_type="Attendance",
        entity_id=attendance.id,
        old_values=old_values,
        new_values=new_values,
        ip_address=ctx.ip,
        user_agent=ctx.user_agent,
        request_id=ctx.request_id,
    )
    await uow.commit()
    return _to_dto(attendance)
