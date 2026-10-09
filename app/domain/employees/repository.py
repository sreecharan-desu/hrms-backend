"""Abstract repository protocols for the employees aggregate."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from app.infrastructure.database.models.employee import Employee, EmployeeCompensation


class EmployeeRepository(Protocol):
    async def get_by_id(self, employee_id: str) -> Employee | None: ...
    async def get_by_email(self, email: str) -> Employee | None: ...
    async def get_by_employee_code(self, code: str) -> Employee | None: ...
    async def get_by_user_id(self, user_id: str) -> Employee | None: ...
    async def list_all(
        self,
        *,
        offset: int = 0,
        limit: int = 50,
        search: str | None = None,
        department_id: str | None = None,
        status: str | None = None,
    ) -> Sequence[Employee]: ...
    async def count(
        self,
        *,
        search: str | None = None,
        department_id: str | None = None,
        status: str | None = None,
    ) -> int: ...
    async def create(self, employee: Employee) -> Employee: ...
    async def update(self, employee: Employee) -> Employee: ...
    async def get_direct_reports(self, manager_id: str) -> Sequence[Employee]: ...


class EmployeeCompensationRepository(Protocol):
    async def get_by_employee_id(self, employee_id: str) -> EmployeeCompensation | None: ...
    async def upsert(self, comp: EmployeeCompensation) -> EmployeeCompensation: ...
