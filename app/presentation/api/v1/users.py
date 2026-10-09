"""User admin endpoints – /api/v1/users/*."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.core.dependencies import CurrentUser, get_uow, require_permission
from app.core.permissions import P
from app.core.responses import success_response
from app.infrastructure.database.uow import SqlAlchemyUnitOfWork
from app.presentation.schemas.users import AssignRolesRequest

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("")
async def list_users_endpoint(
    _user: Annotated[CurrentUser, Depends(require_permission(P.ADMIN_MANAGE))],
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
):
    from app.application.users.list_users import list_users

    result = await list_users(uow, offset=offset, limit=limit)
    return success_response(
        data={
            "items": [
                {
                    "id": u.id,
                    "email": u.email,
                    "status": u.status,
                    "roles": u.roles,
                    "created_at": u.created_at,
                    "updated_at": u.updated_at,
                }
                for u in result.items
            ],
            "total": result.total,
            "offset": result.offset,
            "limit": result.limit,
        }
    )


@router.get("/{user_id}")
async def get_user_endpoint(
    user_id: str,
    _user: Annotated[CurrentUser, Depends(require_permission(P.ADMIN_MANAGE))],
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
):
    from app.application.users.get_user import get_user

    result = await get_user(user_id, uow)
    return success_response(
        data={
            "id": result.id,
            "email": result.email,
            "status": result.status,
            "roles": result.roles,
            "created_at": result.created_at,
            "updated_at": result.updated_at,
        }
    )


@router.put("/{user_id}/roles")
async def assign_roles_endpoint(
    user_id: str,
    body: AssignRolesRequest,
    _user: Annotated[CurrentUser, Depends(require_permission(P.ADMIN_MANAGE))],
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
):
    from app.application.users.assign_roles import assign_roles

    final_roles = await assign_roles(user_id, body.role_names, uow)
    return success_response(
        data={"user_id": user_id, "roles": final_roles},
        message="Roles updated.",
    )
