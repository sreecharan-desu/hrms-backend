"""Department endpoints – /api/v1/departments/*."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.core.dependencies import (
    CurrentUser,
    RequestContext,
    get_request_context,
    get_uow,
    require_permission,
)
from app.core.permissions import P
from app.core.responses import created_response, success_response
from app.infrastructure.database.uow import SqlAlchemyUnitOfWork
from app.presentation.schemas.departments import (
    CreateDepartmentRequest,
    UpdateDepartmentRequest,
)

router = APIRouter(prefix="/departments", tags=["Departments"])


def _department_dict(dept):
    return {
        "id": dept.id,
        "name": dept.name,
        "code": dept.code,
        "parent_id": dept.parent_id,
        "head_employee_id": dept.head_employee_id,
        "created_at": dept.created_at.isoformat() if dept.created_at else None,
        "updated_at": dept.updated_at.isoformat() if dept.updated_at else None,
    }


# ── POST /departments ───────────────────────────────────────────────

@router.post("", summary="Create department")
async def create_department_endpoint(
    body: CreateDepartmentRequest,
    user: Annotated[CurrentUser, Depends(require_permission(P.DEPARTMENT_CREATE))],
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
):
    from app.application.departments.create_department import (
        CreateDepartmentInput,
        create_department,
    )

    inp = CreateDepartmentInput(
        name=body.name,
        code=body.code,
        parent_id=body.parent_id,
        head_employee_id=body.head_employee_id,
    )
    department = await create_department(inp, uow, actor_id=user.id, ctx=ctx)
    return created_response(data=_department_dict(department), message="Department created.")


# ── GET /departments ─────────────────────────────────────────────────

@router.get("", summary="List departments")
async def list_departments_endpoint(
    _user: Annotated[CurrentUser, Depends(require_permission(P.DEPARTMENT_READ))],
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    search: str | None = Query(None),
):
    from app.application.departments.list_departments import list_departments

    result = await list_departments(uow, offset=offset, limit=limit, search=search)
    return success_response(
        data={
            "items": [_department_dict(d) for d in result.items],
            "total": result.total,
            "offset": result.offset,
            "limit": result.limit,
        }
    )


# ── GET /departments/{department_id} ─────────────────────────────────

@router.get("/{department_id}", summary="Get department")
async def get_department_endpoint(
    department_id: str,
    _user: Annotated[CurrentUser, Depends(require_permission(P.DEPARTMENT_READ))],
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
):
    from app.application.departments.get_department import get_department

    department = await get_department(department_id, uow)
    return success_response(data=_department_dict(department))


# ── PATCH /departments/{department_id} ───────────────────────────────

@router.patch("/{department_id}", summary="Update department")
async def update_department_endpoint(
    department_id: str,
    body: UpdateDepartmentRequest,
    user: Annotated[CurrentUser, Depends(require_permission(P.DEPARTMENT_UPDATE))],
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
):
    from app.application.departments.update_department import update_department

    updates = body.model_dump(exclude_unset=True)
    department = await update_department(
        department_id, updates, uow, actor_id=user.id, ctx=ctx
    )
    return success_response(data=_department_dict(department), message="Department updated.")


# ── DELETE /departments/{department_id} ──────────────────────────────

@router.delete("/{department_id}", summary="Soft-delete department")
async def delete_department_endpoint(
    department_id: str,
    user: Annotated[CurrentUser, Depends(require_permission(P.DEPARTMENT_DELETE))],
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
):
    from app.application.departments.delete_department import soft_delete_department

    await soft_delete_department(department_id, uow, actor_id=user.id, ctx=ctx)
    return success_response(message="Department deleted.")


# ── GET /departments/{department_id}/children ────────────────────────

@router.get("/{department_id}/children", summary="Get child departments")
async def get_children_endpoint(
    department_id: str,
    _user: Annotated[CurrentUser, Depends(require_permission(P.DEPARTMENT_READ))],
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
):
    from app.application.departments.get_children import get_department_children

    children = await get_department_children(department_id, uow)
    return success_response(data=[_department_dict(c) for c in children])
