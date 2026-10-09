"""Concrete SQLAlchemy performance repositories."""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.models.performance import (
    PerformanceCycle,
    PerformanceGoal,
    PerformanceReview,
)


class SqlPerformanceCycleRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, cycle_id: str) -> PerformanceCycle | None:
        result = await self._session.execute(
            select(PerformanceCycle).where(PerformanceCycle.id == cycle_id)
        )
        return result.scalars().first()

    async def list_all(
        self,
        *,
        status: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> Sequence[PerformanceCycle]:
        stmt = select(PerformanceCycle)
        if status is not None:
            stmt = stmt.where(PerformanceCycle.status == status)
        stmt = stmt.order_by(PerformanceCycle.start_date.desc()).offset(offset).limit(limit)
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def count_all(self, *, status: str | None = None) -> int:
        stmt = select(func.count(PerformanceCycle.id))
        if status is not None:
            stmt = stmt.where(PerformanceCycle.status == status)
        result = await self._session.execute(stmt)
        return result.scalar_one()

    async def create(self, cycle: PerformanceCycle) -> PerformanceCycle:
        self._session.add(cycle)
        await self._session.flush()
        return cycle


class SqlPerformanceReviewRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, review_id: str) -> PerformanceReview | None:
        result = await self._session.execute(
            select(PerformanceReview).where(PerformanceReview.id == review_id)
        )
        return result.scalars().first()

    async def get_for_update(self, review_id: str) -> PerformanceReview | None:
        result = await self._session.execute(
            select(PerformanceReview)
            .where(PerformanceReview.id == review_id)
            .with_for_update()
        )
        return result.scalars().first()

    async def list_filtered(
        self,
        *,
        cycle_id: str | None = None,
        employee_id: str | None = None,
        status: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> Sequence[PerformanceReview]:
        stmt = select(PerformanceReview)
        if cycle_id is not None:
            stmt = stmt.where(PerformanceReview.cycle_id == cycle_id)
        if employee_id is not None:
            stmt = stmt.where(PerformanceReview.employee_id == employee_id)
        if status is not None:
            stmt = stmt.where(PerformanceReview.status == status)
        stmt = stmt.order_by(PerformanceReview.created_at.desc()).offset(offset).limit(limit)
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def count_filtered(
        self,
        *,
        cycle_id: str | None = None,
        employee_id: str | None = None,
        status: str | None = None,
    ) -> int:
        stmt = select(func.count(PerformanceReview.id))
        if cycle_id is not None:
            stmt = stmt.where(PerformanceReview.cycle_id == cycle_id)
        if employee_id is not None:
            stmt = stmt.where(PerformanceReview.employee_id == employee_id)
        if status is not None:
            stmt = stmt.where(PerformanceReview.status == status)
        result = await self._session.execute(stmt)
        return result.scalar_one()

    async def create(self, review: PerformanceReview) -> PerformanceReview:
        self._session.add(review)
        await self._session.flush()
        return review

    async def update(self, _review: PerformanceReview) -> PerformanceReview:
        await self._session.flush()
        return _review


class SqlPerformanceGoalRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_by_review(self, review_id: str) -> Sequence[PerformanceGoal]:
        result = await self._session.execute(
            select(PerformanceGoal)
            .where(PerformanceGoal.review_id == review_id)
            .order_by(PerformanceGoal.created_at.asc())
        )
        return result.scalars().all()

    async def create(self, goal: PerformanceGoal) -> PerformanceGoal:
        self._session.add(goal)
        await self._session.flush()
        return goal
