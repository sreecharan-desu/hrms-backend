"""Attendance endpoints – /api/v1/attendance/*."""

from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.application.attendance.use_cases import (
    ManualAttendanceInput,
    UpdateAttendanceInput,
    check_in,
    check_out,
    create_manual_attendance,
    get_employee_attendance,
    list_attendance,
    update_attendance,
)
from app.core.dependencies import (
    CurrentUser,
    RequestContext,
    get_current_user,
    get_request_context,
    get_uow,
    require_permission,
)
from app.core.permissions import P
from app.core.responses import created_response, success_response
from app.infrastructure.database.uow import SqlAlchemyUnitOfWork
from app.presentation.schemas.attendance import (
    ManualAttendanceRequest,
    UpdateAttendanceRequest,
)

router = APIRouter(prefix="/attendance", tags=["Attendance"])


@router.post("/check-in")
async def check_in_endpoint(
    user: Annotated[CurrentUser, Depends(get_current_user)],
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
    employee_id: str | None = Query(None, description="Defaults to current user's ID"),
):
    eid = employee_id or user.id
    result = await check_in(uow, user, eid, ctx)
    return created_response(data=result.__dict__, message="Checked in successfully.")


@router.post("/check-out")
async def check_out_endpoint(
    user: Annotated[CurrentUser, Depends(get_current_user)],
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
    employee_id: str | None = Query(None),
):
    eid = employee_id or user.id
    result = await check_out(uow, user, eid, ctx)
    return success_response(data=result.__dict__, message="Checked out successfully.")


@router.get("")
async def list_attendance_endpoint(
    user: Annotated[CurrentUser, Depends(require_permission(P.ATTENDANCE_READ))],
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    employee_id: str | None = Query(None),
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
):
    result = await list_attendance(
        uow,
        employee_id=employee_id,
        date_from=date_from,
        date_to=date_to,
        offset=offset,
        limit=limit,
    )
    return success_response(
        data={
            "items": [i.__dict__ for i in result.items],
            "total": result.total,
            "offset": result.offset,
            "limit": result.limit,
        }
    )


@router.get("/{employee_id}")
async def get_employee_attendance_endpoint(
    employee_id: str,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
):
    if employee_id != user.id and P.ATTENDANCE_READ not in user.permissions:
        from app.core.exceptions import ForbiddenError

        raise ForbiddenError("You can only view your own attendance.")

    result = await get_employee_attendance(
        uow,
        employee_id,
        date_from=date_from,
        date_to=date_to,
        offset=offset,
        limit=limit,
    )
    return success_response(
        data={
            "items": [i.__dict__ for i in result.items],
            "total": result.total,
            "offset": result.offset,
            "limit": result.limit,
        }
    )


@router.post("/manual")
async def manual_attendance_endpoint(
    body: ManualAttendanceRequest,
    user: Annotated[CurrentUser, Depends(require_permission(P.ATTENDANCE_UPDATE))],
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
):
    data = ManualAttendanceInput(
        employee_id=body.employee_id,
        work_date=body.work_date,
        check_in=body.check_in,
        check_out=body.check_out,
        status=body.status,
        remarks=body.remarks,
    )
    result = await create_manual_attendance(uow, user, data, ctx)
    return created_response(data=result.__dict__, message="Manual attendance recorded.")


@router.patch("/{attendance_id}")
async def update_attendance_endpoint(
    attendance_id: str,
    body: UpdateAttendanceRequest,
    user: Annotated[CurrentUser, Depends(require_permission(P.ATTENDANCE_UPDATE))],
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
):
    data = UpdateAttendanceInput(
        check_in=body.check_in,
        check_out=body.check_out,
        status=body.status,
        remarks=body.remarks,
    )
    result = await update_attendance(uow, user, attendance_id, data, ctx)
    return success_response(data=result.__dict__, message="Attendance updated.")
