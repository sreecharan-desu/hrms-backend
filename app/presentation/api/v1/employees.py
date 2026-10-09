"""Employee endpoints – /api/v1/employees/*."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.application.common.policies import can_view_compensation, can_view_employee
from app.core.dependencies import (
    CurrentUser,
    RequestContext,
    get_current_user,
    get_request_context,
    get_uow,
    require_permission,
)
from app.core.exceptions import ForbiddenError
from app.core.permissions import P
from app.core.responses import created_response, success_response
from app.infrastructure.database.uow import SqlAlchemyUnitOfWork
from app.presentation.schemas.employees import (
    CreateEmployeeRequest,
    UpdateCompensationRequest,
    UpdateEmployeeRequest,
)

router = APIRouter(prefix="/employees", tags=["Employees"])


# ── Helpers ──────────────────────────────────────────────────────────

def _employee_dict(emp, *, include_compensation: bool = False):
    """Serialise an Employee ORM instance to a response dict."""
    data = {
        "id": emp.id,
        "employee_code": emp.employee_code,
        "first_name": emp.first_name,
        "last_name": emp.last_name,
        "email": emp.email,
        "phone": emp.phone,
        "date_of_birth": emp.date_of_birth.isoformat() if emp.date_of_birth else None,
        "joining_date": emp.joining_date.isoformat() if emp.joining_date else None,
        "status": emp.status,
        "department_id": emp.department_id,
        "designation": emp.designation,
        "manager_id": emp.manager_id,
        "location": emp.location,
        "emergency_contact": emp.emergency_contact,
        "profile": emp.profile,
        "user_id": emp.user_id,
        "created_at": emp.created_at.isoformat() if emp.created_at else None,
        "updated_at": emp.updated_at.isoformat() if emp.updated_at else None,
    }
    if include_compensation and emp.compensation:
        data["compensation"] = {
            "id": emp.compensation.id,
            "employee_id": emp.compensation.employee_id,
            "salary": str(emp.compensation.salary),
            "currency": emp.compensation.currency,
            "effective_from": (
                emp.compensation.effective_from.isoformat()
                if emp.compensation.effective_from
                else None
            ),
        }
    return data


async def _resolve_actor_employee(actor: CurrentUser, uow: SqlAlchemyUnitOfWork):
    """Return the Employee record linked to the current actor, or None."""
    return await uow.employees.get_by_user_id(actor.id)


def _can_access_employee(actor: CurrentUser, emp, *, actor_employee=None) -> bool:
    """Resource-level check: broad perm, self, or direct manager."""
    if P.EMPLOYEE_READ in actor.permissions:
        return True
    if can_view_employee(actor, emp.user_id):
        return True
    return bool(actor_employee and emp.manager_id == actor_employee.id)


# ── POST /employees ──────────────────────────────────────────────────

@router.post("", summary="Create employee")
async def create_employee_endpoint(
    body: CreateEmployeeRequest,
    user: Annotated[CurrentUser, Depends(require_permission(P.EMPLOYEE_CREATE))],
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
):
    from app.application.employees.create_employee import CreateEmployeeInput, create_employee

    inp = CreateEmployeeInput(
        employee_code=body.employee_code,
        first_name=body.first_name,
        last_name=body.last_name,
        email=body.email,
        joining_date=body.joining_date,
        phone=body.phone,
        date_of_birth=body.date_of_birth,
        status=body.status,
        department_id=body.department_id,
        designation=body.designation,
        manager_id=body.manager_id,
        location=body.location,
        emergency_contact=body.emergency_contact,
        profile=body.profile,
        user_id=body.user_id,
    )
    employee = await create_employee(inp, uow, actor_id=user.id, ctx=ctx)
    return created_response(data=_employee_dict(employee), message="Employee created.")


# ── GET /employees ───────────────────────────────────────────────────

@router.get("", summary="List employees")
async def list_employees_endpoint(
    user: Annotated[CurrentUser, Depends(get_current_user)],
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    search: str | None = Query(None),
    department_id: str | None = Query(None),
    status: str | None = Query(None),
):
    from app.application.employees.list_employees import list_employees

    if P.EMPLOYEE_READ not in user.permissions:
        raise ForbiddenError("Missing required permission: employee.read")

    result = await list_employees(
        uow,
        offset=offset,
        limit=limit,
        search=search,
        department_id=department_id,
        status=status,
    )

    # Resource-level filtering for EMPLOYEE / MANAGER roles
    actor_employee = await _resolve_actor_employee(user, uow)
    has_broad = any(
        r in user.roles for r in ("SUPER_ADMIN", "HR_ADMIN", "HR_MANAGER", "HR_EXECUTIVE")
    )

    if has_broad:
        items = [_employee_dict(e) for e in result.items]
    else:
        items = [
            _employee_dict(e)
            for e in result.items
            if _can_access_employee(user, e, actor_employee=actor_employee)
        ]

    return success_response(
        data={
            "items": items,
            "total": result.total if has_broad else len(items),
            "offset": result.offset,
            "limit": result.limit,
        }
    )


# ── GET /employees/{employee_id} ─────────────────────────────────────

@router.get("/{employee_id}", summary="Get employee")
async def get_employee_endpoint(
    employee_id: str,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
):
    from app.application.employees.get_employee import get_employee

    employee = await get_employee(employee_id, uow)

    actor_employee = await _resolve_actor_employee(user, uow)
    if not _can_access_employee(user, employee, actor_employee=actor_employee):
        raise ForbiddenError("You do not have access to this employee record.")

    include_comp = can_view_compensation(user, employee.user_id)
    return success_response(
        data=_employee_dict(employee, include_compensation=include_comp)
    )


# ── PATCH /employees/{employee_id} ──────────────────────────────────

@router.patch("/{employee_id}", summary="Update employee")
async def update_employee_endpoint(
    employee_id: str,
    body: UpdateEmployeeRequest,
    user: Annotated[CurrentUser, Depends(require_permission(P.EMPLOYEE_UPDATE))],
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
):
    from app.application.employees.update_employee import update_employee

    updates = body.model_dump(exclude_unset=True)
    employee = await update_employee(
        employee_id, updates, uow, actor_id=user.id, ctx=ctx
    )
    return success_response(data=_employee_dict(employee), message="Employee updated.")


# ── DELETE /employees/{employee_id} ──────────────────────────────────

@router.delete("/{employee_id}", summary="Soft-delete employee")
async def delete_employee_endpoint(
    employee_id: str,
    user: Annotated[CurrentUser, Depends(require_permission(P.EMPLOYEE_DELETE))],
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
):
    from app.application.employees.delete_employee import soft_delete_employee

    await soft_delete_employee(employee_id, uow, actor_id=user.id, ctx=ctx)
    return success_response(message="Employee deleted.")


# ── PATCH /employees/{employee_id}/compensation ─────────────────────

@router.patch("/{employee_id}/compensation", summary="Update compensation")
async def update_compensation_endpoint(
    employee_id: str,
    body: UpdateCompensationRequest,
    user: Annotated[CurrentUser, Depends(require_permission(P.EMPLOYEE_COMPENSATION_UPDATE))],
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
):
    from app.application.employees.update_compensation import (
        CompensationInput,
        update_compensation,
    )

    inp = CompensationInput(
        salary=body.salary,
        currency=body.currency,
        effective_from=body.effective_from,
    )
    comp = await update_compensation(employee_id, inp, uow, actor_id=user.id, ctx=ctx)
    return success_response(
        data={
            "id": comp.id,
            "employee_id": comp.employee_id,
            "salary": str(comp.salary),
            "currency": comp.currency,
            "effective_from": (
                comp.effective_from.isoformat() if comp.effective_from else None
            ),
        },
        message="Compensation updated.",
    )


# ── Nested reads ─────────────────────────────────────────────────────

@router.get("/{employee_id}/attendance", summary="Employee attendance records")
async def employee_attendance_endpoint(
    employee_id: str,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
):
    from app.application.employees.nested_reads import get_employee_attendance

    result = await get_employee_attendance(employee_id, uow, offset=offset, limit=limit)
    return success_response(
        data={
            "items": result.items,
            "total": result.total,
            "offset": result.offset,
            "limit": result.limit,
        }
    )


@router.get("/{employee_id}/leave", summary="Employee leave requests")
async def employee_leave_endpoint(
    employee_id: str,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
):
    from app.application.employees.nested_reads import get_employee_leave

    result = await get_employee_leave(employee_id, uow, offset=offset, limit=limit)
    return success_response(
        data={
            "items": result.items,
            "total": result.total,
            "offset": result.offset,
            "limit": result.limit,
        }
    )


@router.get("/{employee_id}/documents", summary="Employee documents")
async def employee_documents_endpoint(
    employee_id: str,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
):
    from app.application.employees.nested_reads import get_employee_documents

    result = await get_employee_documents(employee_id, uow, offset=offset, limit=limit)
    return success_response(
        data={
            "items": result.items,
            "total": result.total,
            "offset": result.offset,
            "limit": result.limit,
        }
    )


@router.get("/{employee_id}/performance", summary="Employee performance reviews")
async def employee_performance_endpoint(
    employee_id: str,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
):
    from app.application.employees.nested_reads import get_employee_performance

    result = await get_employee_performance(employee_id, uow, offset=offset, limit=limit)
    return success_response(
        data={
            "items": result.items,
            "total": result.total,
            "offset": result.offset,
            "limit": result.limit,
        }
    )
