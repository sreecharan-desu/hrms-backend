"""Abstract repository protocols for the attendance aggregate."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date
from typing import Protocol

from app.infrastructure.database.models.attendance import Attendance


class AttendanceRepository(Protocol):
    async def get_by_id(self, attendance_id: str) -> Attendance | None: ...
    async def get_by_employee_and_date(
        self, employee_id: str, work_date: date
    ) -> Attendance | None: ...
    async def list_filtered(
        self,
        *,
        employee_id: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> Sequence[Attendance]: ...
    async def count_filtered(
        self,
        *,
        employee_id: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> int: ...
    async def create(self, attendance: Attendance) -> Attendance: ...
    async def update(self, attendance: Attendance) -> Attendance: ...
