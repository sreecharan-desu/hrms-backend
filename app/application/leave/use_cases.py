"""Leave use cases – apply, list, approve, reject, cancel, types, balances."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

from app.application.common.audit import record_audit
from app.core.dependencies import CurrentUser, RequestContext
from app.core.exceptions import (
    AppError,
    ConflictError,
    NotFoundError,
    ValidationAppError,
)
from app.domain.leave.enums import LeaveRequestStatus
from app.infrastructure.database.models.jobs import BackgroundJob
from app.infrastructure.database.models.leave import LeaveRequest
from app.infrastructure.database.uow import SqlAlchemyUnitOfWork

# ── Custom errors ────────────────────────────────────────────────────

class LeaveInsufficientBalanceError(AppError):
    code = "LEAVE_INSUFFICIENT_BALANCE"
    message = "Insufficient leave balance."
    status_code = 422


class LeaveInvalidStatusError(AppError):
    code = "LEAVE_INVALID_STATUS"
    message = "Invalid leave status transition."
    status_code = 422


# ── DTOs ─────────────────────────────────────────────────────────────

@dataclass(frozen=True, slots=True)
class LeaveRequestDTO:
    id: str
    employee_id: str
    leave_type_id: str
    start_date: str
    end_date: str
    days: str
    reason: str | None
    status: str
    reviewed_by: str | None
    reviewed_at: str | None
    review_comment: str | None
    created_at: str
    updated_at: str


def _to_dto(r: LeaveRequest) -> LeaveRequestDTO:
    return LeaveRequestDTO(
        id=r.id,
        employee_id=r.employee_id,
        leave_type_id=r.leave_type_id,
        start_date=r.start_date.isoformat(),
        end_date=r.end_date.isoformat(),
        days=str(r.days),
        reason=r.reason,
        status=r.status,
        reviewed_by=r.reviewed_by,
        reviewed_at=r.reviewed_at.isoformat() if r.reviewed_at else None,
        review_comment=r.review_comment,
        created_at=r.created_at.isoformat() if r.created_at else "",
        updated_at=r.updated_at.isoformat() if r.updated_at else "",
    )


@dataclass(frozen=True, slots=True)
class ListLeaveResult:
    items: list[LeaveRequestDTO]
    total: int
    offset: int
    limit: int


@dataclass(frozen=True, slots=True)
class LeaveTypeDTO:
    id: str
    name: str
    code: str
    description: str | None
    max_days_per_year: str
    is_paid: bool


@dataclass(frozen=True, slots=True)
class LeaveBalanceDTO:
    id: str
    employee_id: str
    leave_type_id: str
    year: int
    total_days: str
    used_days: str
    pending_days: str
    remaining_days: str


# ── Apply for leave ──────────────────────────────────────────────────

@dataclass(frozen=True, slots=True)
class ApplyLeaveInput:
    employee_id: str
    leave_type_id: str
    start_date: str  # ISO date
    end_date: str
    days: Decimal
    reason: str | None = None


async def apply_leave(
    uow: SqlAlchemyUnitOfWork,
    user: CurrentUser,
    data: ApplyLeaveInput,
    ctx: RequestContext,
) -> LeaveRequestDTO:
    from datetime import date as date_cls

    start = date_cls.fromisoformat(data.start_date)
    end = date_cls.fromisoformat(data.end_date)

    if start > end:
        raise ValidationAppError("start_date must be before or equal to end_date.")

    leave_type = await uow.leave_types.get_by_id(data.leave_type_id)
    if leave_type is None:
        raise NotFoundError("Leave type not found.")

    overlap = await uow.leave_requests.has_overlap(data.employee_id, start, end)
    if overlap:
        raise ConflictError("Overlapping leave request exists for this period.")

    year = start.year
    balance = await uow.leave_balances.get(data.employee_id, data.leave_type_id, year)
    if balance is None:
        raise LeaveInsufficientBalanceError("No leave balance allocated for this type/year.")

    available = balance.total_days - balance.used_days - balance.pending_days
    if data.days > available:
        raise LeaveInsufficientBalanceError(
            f"Insufficient balance: {available} days available, {data.days} requested."
        )

    balance.pending_days += data.days
    await uow.leave_balances.update(balance)

    request = LeaveRequest(
        employee_id=data.employee_id,
        leave_type_id=data.leave_type_id,
        start_date=start,
        end_date=end,
        days=data.days,
        reason=data.reason,
        status=LeaveRequestStatus.PENDING,
    )
    await uow.leave_requests.create(request)

    await record_audit(
        uow.session,
        actor_id=user.id,
        action="leave.apply",
        entity_type="LeaveRequest",
        entity_id=request.id,
        new_values={
            "employee_id": data.employee_id,
            "leave_type_id": data.leave_type_id,
            "start_date": data.start_date,
            "end_date": data.end_date,
            "days": str(data.days),
        },
        ip_address=ctx.ip,
        user_agent=ctx.user_agent,
        request_id=ctx.request_id,
    )
    await uow.commit()
    return _to_dto(request)


# ── Approve ──────────────────────────────────────────────────────────

async def approve_leave(
    uow: SqlAlchemyUnitOfWork,
    user: CurrentUser,
    request_id: str,
    ctx: RequestContext,
    comment: str | None = None,
) -> LeaveRequestDTO:
    request = await uow.leave_requests.get_for_update(request_id)
    if request is None:
        raise NotFoundError("Leave request not found.")

    from_status = LeaveRequestStatus(request.status)
    to_status = LeaveRequestStatus.APPROVED

    if not LeaveRequestStatus.can_transition(from_status, to_status):
        raise LeaveInvalidStatusError(
            f"Cannot transition from {from_status} to {to_status}."
        )

    balance = await uow.leave_balances.get_for_update(
        request.employee_id, request.leave_type_id, request.start_date.year
    )
    if balance is None:
        raise LeaveInsufficientBalanceError("Leave balance record not found.")

    available = balance.total_days - balance.used_days
    if request.days > available:
        raise LeaveInsufficientBalanceError(
            f"Insufficient balance: {available} available, {request.days} required."
        )

    balance.pending_days -= request.days
    balance.used_days += request.days
    await uow.leave_balances.update(balance)

    now_utc = datetime.now(UTC)
    request.status = to_status
    request.reviewed_by = user.id
    request.reviewed_at = now_utc
    request.review_comment = comment
    await uow.leave_requests.update(request)

    await record_audit(
        uow.session,
        actor_id=user.id,
        action="leave.approve",
        entity_type="LeaveRequest",
        entity_id=request.id,
        old_values={"status": from_status.value},
        new_values={"status": to_status.value, "reviewed_by": user.id},
        ip_address=ctx.ip,
        user_agent=ctx.user_agent,
        request_id=ctx.request_id,
    )

    job = BackgroundJob(
        type="leave.approved_notification",
        payload={
            "leave_request_id": request.id,
            "employee_id": request.employee_id,
            "approved_by": user.id,
        },
        status="PENDING",
        available_at=now_utc,
    )
    uow.session.add(job)
    await uow.session.flush()

    await uow.commit()
    return _to_dto(request)


# ── Reject ───────────────────────────────────────────────────────────

async def reject_leave(
    uow: SqlAlchemyUnitOfWork,
    user: CurrentUser,
    request_id: str,
    reason: str,
    ctx: RequestContext,
) -> LeaveRequestDTO:
    request = await uow.leave_requests.get_for_update(request_id)
    if request is None:
        raise NotFoundError("Leave request not found.")

    from_status = LeaveRequestStatus(request.status)
    to_status = LeaveRequestStatus.REJECTED

    if not LeaveRequestStatus.can_transition(from_status, to_status):
        raise LeaveInvalidStatusError(
            f"Cannot transition from {from_status} to {to_status}."
        )

    if from_status == LeaveRequestStatus.PENDING:
        balance = await uow.leave_balances.get_for_update(
            request.employee_id, request.leave_type_id, request.start_date.year
        )
        if balance is not None:
            balance.pending_days -= request.days
            await uow.leave_balances.update(balance)

    now_utc = datetime.now(UTC)
    request.status = to_status
    request.reviewed_by = user.id
    request.reviewed_at = now_utc
    request.review_comment = reason
    await uow.leave_requests.update(request)

    await record_audit(
        uow.session,
        actor_id=user.id,
        action="leave.reject",
        entity_type="LeaveRequest",
        entity_id=request.id,
        old_values={"status": from_status.value},
        new_values={"status": to_status.value, "review_comment": reason},
        ip_address=ctx.ip,
        user_agent=ctx.user_agent,
        request_id=ctx.request_id,
    )
    await uow.commit()
    return _to_dto(request)


# ── Cancel ───────────────────────────────────────────────────────────

async def cancel_leave(
    uow: SqlAlchemyUnitOfWork,
    user: CurrentUser,
    request_id: str,
    ctx: RequestContext,
) -> LeaveRequestDTO:
    request = await uow.leave_requests.get_for_update(request_id)
    if request is None:
        raise NotFoundError("Leave request not found.")

    from_status = LeaveRequestStatus(request.status)
    to_status = LeaveRequestStatus.CANCELLED

    if not LeaveRequestStatus.can_transition(from_status, to_status):
        raise LeaveInvalidStatusError(
            f"Cannot transition from {from_status} to {to_status}."
        )

    balance = await uow.leave_balances.get_for_update(
        request.employee_id, request.leave_type_id, request.start_date.year
    )
    if balance is not None:
        if from_status == LeaveRequestStatus.APPROVED:
            balance.used_days -= request.days
        elif from_status == LeaveRequestStatus.PENDING:
            balance.pending_days -= request.days
        await uow.leave_balances.update(balance)

    request.status = to_status
    await uow.leave_requests.update(request)

    await record_audit(
        uow.session,
        actor_id=user.id,
        action="leave.cancel",
        entity_type="LeaveRequest",
        entity_id=request.id,
        old_values={"status": from_status.value},
        new_values={"status": to_status.value},
        ip_address=ctx.ip,
        user_agent=ctx.user_agent,
        request_id=ctx.request_id,
    )
    await uow.commit()
    return _to_dto(request)


# ── List leaves ──────────────────────────────────────────────────────

async def list_leaves(
    uow: SqlAlchemyUnitOfWork,
    *,
    employee_id: str | None = None,
    status: str | None = None,
    offset: int = 0,
    limit: int = 50,
) -> ListLeaveResult:
    items = await uow.leave_requests.list_filtered(
        employee_id=employee_id, status=status, offset=offset, limit=limit
    )
    total = await uow.leave_requests.count_filtered(
        employee_id=employee_id, status=status
    )
    return ListLeaveResult(
        items=[_to_dto(r) for r in items],
        total=total,
        offset=offset,
        limit=limit,
    )


# ── Get single leave request ────────────────────────────────────────

async def get_leave(
    uow: SqlAlchemyUnitOfWork,
    request_id: str,
) -> LeaveRequestDTO:
    request = await uow.leave_requests.get_by_id(request_id)
    if request is None:
        raise NotFoundError("Leave request not found.")
    return _to_dto(request)


# ── List leave types ────────────────────────────────────────────────

async def list_leave_types(
    uow: SqlAlchemyUnitOfWork,
) -> list[LeaveTypeDTO]:
    types = await uow.leave_types.list_active()
    return [
        LeaveTypeDTO(
            id=t.id,
            name=t.name,
            code=t.code,
            description=t.description,
            max_days_per_year=str(t.max_days_per_year),
            is_paid=t.is_paid,
        )
        for t in types
    ]


# ── My balances ─────────────────────────────────────────────────────

async def get_my_balances(
    uow: SqlAlchemyUnitOfWork,
    employee_id: str,
    year: int,
) -> list[LeaveBalanceDTO]:
    balances = await uow.leave_balances.list_by_employee(employee_id, year)
    return [
        LeaveBalanceDTO(
            id=b.id,
            employee_id=b.employee_id,
            leave_type_id=b.leave_type_id,
            year=b.year,
            total_days=str(b.total_days),
            used_days=str(b.used_days),
            pending_days=str(b.pending_days),
            remaining_days=str(b.total_days - b.used_days - b.pending_days),
        )
        for b in balances
    ]
