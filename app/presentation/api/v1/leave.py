"""Leave endpoints – /api/v1/leaves/*."""

from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.application.leave.use_cases import (
    ApplyLeaveInput,
    apply_leave,
    approve_leave,
    cancel_leave,
    get_leave,
    get_my_balances,
    list_leave_types,
    list_leaves,
    reject_leave,
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
from app.presentation.schemas.leave import (
    ApplyLeaveRequest,
    RejectLeaveRequest,
    ReviewLeaveRequest,
)

router = APIRouter(prefix="/leaves", tags=["Leave"])


@router.post("")
async def apply_leave_endpoint(
    body: ApplyLeaveRequest,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
):
    data = ApplyLeaveInput(
        employee_id=user.id,
        leave_type_id=body.leave_type_id,
        start_date=body.start_date.isoformat(),
        end_date=body.end_date.isoformat(),
        days=body.days,
        reason=body.reason,
    )
    result = await apply_leave(uow, user, data, ctx)
    return created_response(data=result.__dict__, message="Leave request submitted.")


@router.get("")
async def list_leaves_endpoint(
    user: Annotated[CurrentUser, Depends(get_current_user)],
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    employee_id: str | None = Query(None),
    status: str | None = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
):
    eid = employee_id
    if eid is not None and eid != user.id and P.LEAVE_READ not in user.permissions:
        from app.core.exceptions import ForbiddenError

        raise ForbiddenError("You can only view your own leave requests.")
    if eid is None and P.LEAVE_READ not in user.permissions:
        eid = user.id

    result = await list_leaves(
        uow, employee_id=eid, status=status, offset=offset, limit=limit
    )
    return success_response(
        data={
            "items": [i.__dict__ for i in result.items],
            "total": result.total,
            "offset": result.offset,
            "limit": result.limit,
        }
    )


@router.get("/balances/me")
async def my_balances_endpoint(
    user: Annotated[CurrentUser, Depends(get_current_user)],
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    year: int = Query(default_factory=lambda: date.today().year),
):
    balances = await get_my_balances(uow, user.id, year)
    return success_response(data=[b.__dict__ for b in balances])


@router.get("/{leave_id}")
async def get_leave_endpoint(
    leave_id: str,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
):
    result = await get_leave(uow, leave_id)
    if result.employee_id != user.id and P.LEAVE_READ not in user.permissions:
        from app.core.exceptions import ForbiddenError

        raise ForbiddenError("You can only view your own leave requests.")
    return success_response(data=result.__dict__)


@router.post("/{leave_id}/approve")
async def approve_leave_endpoint(
    leave_id: str,
    user: Annotated[CurrentUser, Depends(require_permission(P.LEAVE_APPROVE))],
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
    body: ReviewLeaveRequest | None = None,
):
    comment = body.comment if body else None
    result = await approve_leave(uow, user, leave_id, ctx, comment=comment)
    return success_response(data=result.__dict__, message="Leave request approved.")


@router.post("/{leave_id}/reject")
async def reject_leave_endpoint(
    leave_id: str,
    body: RejectLeaveRequest,
    user: Annotated[CurrentUser, Depends(require_permission(P.LEAVE_REJECT))],
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
):
    result = await reject_leave(uow, user, leave_id, body.reason, ctx)
    return success_response(data=result.__dict__, message="Leave request rejected.")


@router.post("/{leave_id}/cancel")
async def cancel_leave_endpoint(
    leave_id: str,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
):
    result = await cancel_leave(uow, user, leave_id, ctx)
    return success_response(data=result.__dict__, message="Leave request cancelled.")


# ── Leave types (read-only) ─────────────────────────────────────────

leave_types_router = APIRouter(prefix="/leave-types", tags=["Leave"])


@leave_types_router.get("")
async def list_leave_types_endpoint(
    _user: Annotated[CurrentUser, Depends(get_current_user)],
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
):
    types = await list_leave_types(uow)
    return success_response(data=[t.__dict__ for t in types])
