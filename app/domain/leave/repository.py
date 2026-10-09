"""Abstract repository protocols for the leave aggregate."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date
from typing import Protocol

from app.infrastructure.database.models.leave import (
    LeaveBalance,
    LeaveRequest,
    LeaveType,
)


class LeaveTypeRepository(Protocol):
    async def get_by_id(self, leave_type_id: str) -> LeaveType | None: ...
    async def list_active(self) -> Sequence[LeaveType]: ...


class LeaveBalanceRepository(Protocol):
    async def get(
        self, employee_id: str, leave_type_id: str, year: int
    ) -> LeaveBalance | None: ...
    async def get_for_update(
        self, employee_id: str, leave_type_id: str, year: int
    ) -> LeaveBalance | None: ...
    async def list_by_employee(
        self, employee_id: str, year: int
    ) -> Sequence[LeaveBalance]: ...
    async def create(self, balance: LeaveBalance) -> LeaveBalance: ...
    async def update(self, balance: LeaveBalance) -> LeaveBalance: ...


class LeaveRequestRepository(Protocol):
    async def get_by_id(self, request_id: str) -> LeaveRequest | None: ...
    async def get_for_update(self, request_id: str) -> LeaveRequest | None: ...
    async def has_overlap(
        self,
        employee_id: str,
        start_date: date,
        end_date: date,
        *,
        exclude_id: str | None = None,
    ) -> bool: ...
    async def list_filtered(
        self,
        *,
        employee_id: str | None = None,
        status: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> Sequence[LeaveRequest]: ...
    async def count_filtered(
        self,
        *,
        employee_id: str | None = None,
        status: str | None = None,
    ) -> int: ...
    async def create(self, request: LeaveRequest) -> LeaveRequest: ...
    async def update(self, request: LeaveRequest) -> LeaveRequest: ...
