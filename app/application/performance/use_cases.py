"""Performance use cases – cycles, reviews, goals, submit, approve."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date as date_cls
from decimal import Decimal
from typing import Any

from app.application.common.audit import record_audit
from app.core.dependencies import CurrentUser, RequestContext
from app.core.exceptions import AppError, NotFoundError, ValidationAppError
from app.domain.performance.enums import ReviewStatus
from app.infrastructure.database.models.performance import (
    PerformanceCycle,
    PerformanceGoal,
    PerformanceReview,
)
from app.infrastructure.database.uow import SqlAlchemyUnitOfWork

# ── Custom errors ────────────────────────────────────────────────────

class ReviewImmutableError(AppError):
    code = "REVIEW_IMMUTABLE"
    message = "Approved reviews cannot be modified."
    status_code = 422


# ── Cycle DTOs ───────────────────────────────────────────────────────

@dataclass(frozen=True, slots=True)
class CycleDTO:
    id: str
    name: str
    start_date: str
    end_date: str
    status: str
    created_at: str
    updated_at: str


def _cycle_to_dto(c: PerformanceCycle) -> CycleDTO:
    return CycleDTO(
        id=c.id,
        name=c.name,
        start_date=c.start_date.isoformat(),
        end_date=c.end_date.isoformat(),
        status=c.status,
        created_at=c.created_at.isoformat() if c.created_at else "",
        updated_at=c.updated_at.isoformat() if c.updated_at else "",
    )


@dataclass(frozen=True, slots=True)
class ListCycleResult:
    items: list[CycleDTO]
    total: int
    offset: int
    limit: int


# ── Review DTOs ──────────────────────────────────────────────────────

@dataclass(frozen=True, slots=True)
class GoalDTO:
    id: str
    review_id: str
    title: str
    description: str | None
    weight: str | None
    target_date: str | None
    status: str
    achievement: str | None
    created_at: str
    updated_at: str


def _goal_to_dto(g: PerformanceGoal) -> GoalDTO:
    return GoalDTO(
        id=g.id,
        review_id=g.review_id,
        title=g.title,
        description=g.description,
        weight=str(g.weight) if g.weight is not None else None,
        target_date=g.target_date.isoformat() if g.target_date else None,
        status=g.status,
        achievement=str(g.achievement) if g.achievement is not None else None,
        created_at=g.created_at.isoformat() if g.created_at else "",
        updated_at=g.updated_at.isoformat() if g.updated_at else "",
    )


@dataclass(frozen=True, slots=True)
class ReviewDTO:
    id: str
    cycle_id: str
    employee_id: str
    reviewer_id: str | None
    status: str
    self_rating: str | None
    manager_rating: str | None
    final_rating: str | None
    self_comments: str | None
    manager_comments: str | None
    goals: list[GoalDTO]
    created_at: str
    updated_at: str


def _review_to_dto(r: PerformanceReview, goals: list[GoalDTO] | None = None) -> ReviewDTO:
    return ReviewDTO(
        id=r.id,
        cycle_id=r.cycle_id,
        employee_id=r.employee_id,
        reviewer_id=r.reviewer_id,
        status=r.status,
        self_rating=str(r.self_rating) if r.self_rating is not None else None,
        manager_rating=str(r.manager_rating) if r.manager_rating is not None else None,
        final_rating=str(r.final_rating) if r.final_rating is not None else None,
        self_comments=r.self_comments,
        manager_comments=r.manager_comments,
        goals=goals or [],
        created_at=r.created_at.isoformat() if r.created_at else "",
        updated_at=r.updated_at.isoformat() if r.updated_at else "",
    )


@dataclass(frozen=True, slots=True)
class ListReviewResult:
    items: list[ReviewDTO]
    total: int
    offset: int
    limit: int


# ═══════════════════════════════════════════════════════════════════
#  CYCLES
# ═══════════════════════════════════════════════════════════════════

@dataclass(frozen=True, slots=True)
class CreateCycleInput:
    name: str
    start_date: str
    end_date: str
    status: str = "ACTIVE"


async def create_cycle(
    uow: SqlAlchemyUnitOfWork,
    user: CurrentUser,
    data: CreateCycleInput,
    ctx: RequestContext,
) -> CycleDTO:
    cycle = PerformanceCycle(
        name=data.name,
        start_date=date_cls.fromisoformat(data.start_date),
        end_date=date_cls.fromisoformat(data.end_date),
        status=data.status,
    )
    await uow.performance_cycles.create(cycle)
    await record_audit(
        uow.session,
        actor_id=user.id,
        action="performance_cycle.create",
        entity_type="PerformanceCycle",
        entity_id=cycle.id,
        new_values={"name": data.name},
        ip_address=ctx.ip,
        user_agent=ctx.user_agent,
        request_id=ctx.request_id,
    )
    await uow.commit()
    return _cycle_to_dto(cycle)


async def list_cycles(
    uow: SqlAlchemyUnitOfWork,
    *,
    status: str | None = None,
    offset: int = 0,
    limit: int = 50,
) -> ListCycleResult:
    items = await uow.performance_cycles.list_all(
        status=status, offset=offset, limit=limit
    )
    total = await uow.performance_cycles.count_all(status=status)
    return ListCycleResult(
        items=[_cycle_to_dto(c) for c in items],
        total=total,
        offset=offset,
        limit=limit,
    )


# ═══════════════════════════════════════════════════════════════════
#  REVIEWS
# ═══════════════════════════════════════════════════════════════════

@dataclass(frozen=True, slots=True)
class CreateReviewInput:
    cycle_id: str
    employee_id: str
    reviewer_id: str | None = None
    self_rating: str | None = None
    manager_rating: str | None = None
    self_comments: str | None = None
    manager_comments: str | None = None
    goals: list[dict[str, Any]] | None = None


async def create_review(
    uow: SqlAlchemyUnitOfWork,
    user: CurrentUser,
    data: CreateReviewInput,
    ctx: RequestContext,
) -> ReviewDTO:
    cycle = await uow.performance_cycles.get_by_id(data.cycle_id)
    if cycle is None:
        raise NotFoundError("Performance cycle not found.")

    review = PerformanceReview(
        cycle_id=data.cycle_id,
        employee_id=data.employee_id,
        reviewer_id=data.reviewer_id,
        status=ReviewStatus.DRAFT,
        self_rating=Decimal(data.self_rating) if data.self_rating else None,
        manager_rating=Decimal(data.manager_rating) if data.manager_rating else None,
        self_comments=data.self_comments,
        manager_comments=data.manager_comments,
    )
    await uow.performance_reviews.create(review)

    goal_dtos: list[GoalDTO] = []
    if data.goals:
        for g in data.goals:
            goal = PerformanceGoal(
                review_id=review.id,
                title=g["title"],
                description=g.get("description"),
                weight=Decimal(g["weight"]) if g.get("weight") else None,
                target_date=(
                    date_cls.fromisoformat(g["target_date"])
                    if g.get("target_date")
                    else None
                ),
                status=g.get("status", "OPEN"),
                achievement=Decimal(g["achievement"]) if g.get("achievement") else None,
            )
            await uow.performance_goals.create(goal)
            goal_dtos.append(_goal_to_dto(goal))

    await record_audit(
        uow.session,
        actor_id=user.id,
        action="performance_review.create",
        entity_type="PerformanceReview",
        entity_id=review.id,
        new_values={
            "cycle_id": data.cycle_id,
            "employee_id": data.employee_id,
            "status": ReviewStatus.DRAFT,
        },
        ip_address=ctx.ip,
        user_agent=ctx.user_agent,
        request_id=ctx.request_id,
    )
    await uow.commit()
    return _review_to_dto(review, goal_dtos)


async def list_reviews(
    uow: SqlAlchemyUnitOfWork,
    *,
    cycle_id: str | None = None,
    employee_id: str | None = None,
    status: str | None = None,
    offset: int = 0,
    limit: int = 50,
) -> ListReviewResult:
    items = await uow.performance_reviews.list_filtered(
        cycle_id=cycle_id,
        employee_id=employee_id,
        status=status,
        offset=offset,
        limit=limit,
    )
    total = await uow.performance_reviews.count_filtered(
        cycle_id=cycle_id, employee_id=employee_id, status=status
    )
    return ListReviewResult(
        items=[_review_to_dto(r) for r in items],
        total=total,
        offset=offset,
        limit=limit,
    )


async def get_review(uow: SqlAlchemyUnitOfWork, review_id: str) -> ReviewDTO:
    review = await uow.performance_reviews.get_by_id(review_id)
    if review is None:
        raise NotFoundError("Performance review not found.")
    goals = await uow.performance_goals.list_by_review(review_id)
    return _review_to_dto(review, [_goal_to_dto(g) for g in goals])


async def submit_review(
    uow: SqlAlchemyUnitOfWork,
    user: CurrentUser,
    review_id: str,
    ctx: RequestContext,
) -> ReviewDTO:
    review = await uow.performance_reviews.get_for_update(review_id)
    if review is None:
        raise NotFoundError("Performance review not found.")

    if review.status == ReviewStatus.COMPLETED:
        raise ReviewImmutableError("Approved reviews cannot be modified.")

    if review.status not in (ReviewStatus.DRAFT, ReviewStatus.SELF_REVIEW):
        raise ValidationAppError(
            f"Cannot submit a review with status {review.status}."
        )

    old_status = review.status
    review.status = ReviewStatus.MANAGER_REVIEW
    await uow.performance_reviews.update(review)
    await record_audit(
        uow.session,
        actor_id=user.id,
        action="performance_review.submit",
        entity_type="PerformanceReview",
        entity_id=review.id,
        old_values={"status": old_status},
        new_values={"status": ReviewStatus.MANAGER_REVIEW},
        ip_address=ctx.ip,
        user_agent=ctx.user_agent,
        request_id=ctx.request_id,
    )
    await uow.commit()
    goals = await uow.performance_goals.list_by_review(review_id)
    return _review_to_dto(review, [_goal_to_dto(g) for g in goals])


async def approve_review(
    uow: SqlAlchemyUnitOfWork,
    user: CurrentUser,
    review_id: str,
    ctx: RequestContext,
) -> ReviewDTO:
    review = await uow.performance_reviews.get_for_update(review_id)
    if review is None:
        raise NotFoundError("Performance review not found.")

    if review.status == ReviewStatus.COMPLETED:
        raise ReviewImmutableError("Review is already approved.")

    if review.status not in (ReviewStatus.MANAGER_REVIEW, ReviewStatus.CALIBRATION):
        raise ValidationAppError(
            f"Cannot approve a review with status {review.status}."
        )

    old_status = review.status
    review.status = ReviewStatus.COMPLETED
    await uow.performance_reviews.update(review)
    await record_audit(
        uow.session,
        actor_id=user.id,
        action="performance_review.approve",
        entity_type="PerformanceReview",
        entity_id=review.id,
        old_values={"status": old_status},
        new_values={"status": ReviewStatus.COMPLETED},
        ip_address=ctx.ip,
        user_agent=ctx.user_agent,
        request_id=ctx.request_id,
    )
    await uow.commit()
    goals = await uow.performance_goals.list_by_review(review_id)
    return _review_to_dto(review, [_goal_to_dto(g) for g in goals])
