"""Performance endpoints – /api/v1/performance/*."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.application.performance.use_cases import (
    CreateCycleInput,
    CreateReviewInput,
    approve_review,
    create_cycle,
    create_review,
    get_review,
    list_cycles,
    list_reviews,
    submit_review,
)
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
from app.presentation.schemas.performance import CreateCycleRequest, CreateReviewRequest

router = APIRouter(prefix="/performance", tags=["Performance"])


# ── Cycles ───────────────────────────────────────────────────────────

@router.post("/cycles")
async def create_cycle_endpoint(
    body: CreateCycleRequest,
    user: Annotated[CurrentUser, Depends(require_permission(P.PERFORMANCE_CREATE))],
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
):
    data = CreateCycleInput(
        name=body.name,
        start_date=body.start_date.isoformat(),
        end_date=body.end_date.isoformat(),
        status=body.status,
    )
    result = await create_cycle(uow, user, data, ctx)
    return created_response(data=result.__dict__, message="Performance cycle created.")


@router.get("/cycles")
async def list_cycles_endpoint(
    _user: Annotated[CurrentUser, Depends(require_permission(P.PERFORMANCE_READ))],
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    status: str | None = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
):
    result = await list_cycles(uow, status=status, offset=offset, limit=limit)
    return success_response(
        data={
            "items": [i.__dict__ for i in result.items],
            "total": result.total,
            "offset": result.offset,
            "limit": result.limit,
        }
    )


# ── Reviews ──────────────────────────────────────────────────────────

@router.post("/reviews")
async def create_review_endpoint(
    body: CreateReviewRequest,
    user: Annotated[CurrentUser, Depends(require_permission(P.PERFORMANCE_CREATE))],
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
):
    data = CreateReviewInput(
        cycle_id=body.cycle_id,
        employee_id=body.employee_id,
        reviewer_id=body.reviewer_id,
        self_rating=str(body.self_rating) if body.self_rating is not None else None,
        manager_rating=str(body.manager_rating) if body.manager_rating is not None else None,
        self_comments=body.self_comments,
        manager_comments=body.manager_comments,
        goals=[g.model_dump() for g in body.goals] if body.goals else None,
    )
    result = await create_review(uow, user, data, ctx)
    return created_response(data=result.__dict__, message="Performance review created.")


@router.get("/reviews")
async def list_reviews_endpoint(
    _user: Annotated[CurrentUser, Depends(require_permission(P.PERFORMANCE_READ))],
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    cycle_id: str | None = Query(None),
    employee_id: str | None = Query(None),
    status: str | None = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
):
    result = await list_reviews(
        uow,
        cycle_id=cycle_id,
        employee_id=employee_id,
        status=status,
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


@router.get("/reviews/{review_id}")
async def get_review_endpoint(
    review_id: str,
    _user: Annotated[CurrentUser, Depends(require_permission(P.PERFORMANCE_READ))],
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
):
    result = await get_review(uow, review_id)
    return success_response(data=result.__dict__)


@router.post("/reviews/{review_id}/submit")
async def submit_review_endpoint(
    review_id: str,
    user: Annotated[CurrentUser, Depends(require_permission(P.PERFORMANCE_CREATE))],
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
):
    result = await submit_review(uow, user, review_id, ctx)
    return success_response(data=result.__dict__, message="Review submitted for approval.")


@router.post("/reviews/{review_id}/approve")
async def approve_review_endpoint(
    review_id: str,
    user: Annotated[CurrentUser, Depends(require_permission(P.PERFORMANCE_EVALUATE))],
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
):
    result = await approve_review(uow, user, review_id, ctx)
    return success_response(data=result.__dict__, message="Review approved.")
