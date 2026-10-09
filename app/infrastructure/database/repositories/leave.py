"""Concrete SQLAlchemy leave repositories."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.leave.enums import LeaveRequestStatus
from app.infrastructure.database.models.leave import (
    LeaveBalance,
    LeaveRequest,
    LeaveType,
)


class SqlLeaveTypeRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, leave_type_id: str) -> LeaveType | None:
        result = await self._session.execute(
            select(LeaveType).where(LeaveType.id == leave_type_id)
        )
        return result.scalars().first()

    async def list_active(self) -> Sequence[LeaveType]:
        result = await self._session.execute(
            select(LeaveType)
            .where(LeaveType.is_active.is_(True))
            .order_by(LeaveType.name)
        )
        return result.scalars().all()


class SqlLeaveBalanceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(
        self, employee_id: str, leave_type_id: str, year: int
    ) -> LeaveBalance | None:
        result = await self._session.execute(
            select(LeaveBalance).where(
                and_(
                    LeaveBalance.employee_id == employee_id,
                    LeaveBalance.leave_type_id == leave_type_id,
                    LeaveBalance.year == year,
                )
            )
        )
        return result.scalars().first()

    async def get_for_update(
        self, employee_id: str, leave_type_id: str, year: int
    ) -> LeaveBalance | None:
        result = await self._session.execute(
            select(LeaveBalance)
            .where(
                and_(
                    LeaveBalance.employee_id == employee_id,
                    LeaveBalance.leave_type_id == leave_type_id,
                    LeaveBalance.year == year,
                )
            )
            .with_for_update()
        )
        return result.scalars().first()

    async def list_by_employee(
        self, employee_id: str, year: int
    ) -> Sequence[LeaveBalance]:
        result = await self._session.execute(
            select(LeaveBalance).where(
                and_(
                    LeaveBalance.employee_id == employee_id,
                    LeaveBalance.year == year,
                )
            )
        )
        return result.scalars().all()

    async def create(self, balance: LeaveBalance) -> LeaveBalance:
        self._session.add(balance)
        await self._session.flush()
        return balance

    async def update(self, balance: LeaveBalance) -> LeaveBalance:
        await self._session.flush()
        return balance


class SqlLeaveRequestRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, request_id: str) -> LeaveRequest | None:
        result = await self._session.execute(
            select(LeaveRequest).where(LeaveRequest.id == request_id)
        )
        return result.scalars().first()

    async def get_for_update(self, request_id: str) -> LeaveRequest | None:
        result = await self._session.execute(
            select(LeaveRequest)
            .where(LeaveRequest.id == request_id)
            .with_for_update()
        )
        return result.scalars().first()

    async def has_overlap(
        self,
        employee_id: str,
        start_date: date,
        end_date: date,
        *,
        exclude_id: str | None = None,
    ) -> bool:
        stmt = select(func.count(LeaveRequest.id)).where(
            and_(
                LeaveRequest.employee_id == employee_id,
                LeaveRequest.start_date <= end_date,
                LeaveRequest.end_date >= start_date,
                LeaveRequest.status.in_([
                    LeaveRequestStatus.PENDING,
                    LeaveRequestStatus.APPROVED,
                ]),
            )
        )
        if exclude_id is not None:
            stmt = stmt.where(LeaveRequest.id != exclude_id)
        result = await self._session.execute(stmt)
        return result.scalar_one() > 0

    async def list_filtered(
        self,
        *,
        employee_id: str | None = None,
        status: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> Sequence[LeaveRequest]:
        stmt = select(LeaveRequest)
        if employee_id is not None:
            stmt = stmt.where(LeaveRequest.employee_id == employee_id)
        if status is not None:
            stmt = stmt.where(LeaveRequest.status == status)
        stmt = stmt.order_by(LeaveRequest.created_at.desc()).offset(offset).limit(limit)
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def count_filtered(
        self,
        *,
        employee_id: str | None = None,
        status: str | None = None,
    ) -> int:
        stmt = select(func.count(LeaveRequest.id))
        if employee_id is not None:
            stmt = stmt.where(LeaveRequest.employee_id == employee_id)
        if status is not None:
            stmt = stmt.where(LeaveRequest.status == status)
        result = await self._session.execute(stmt)
        return result.scalar_one()

    async def create(self, request: LeaveRequest) -> LeaveRequest:
        self._session.add(request)
        await self._session.flush()
        return request

    async def update(self, request: LeaveRequest) -> LeaveRequest:
        await self._session.flush()
        return request
