"""Unit tests for employee manager cycle detection."""

from __future__ import annotations

import pytest

from app.core.exceptions import ValidationAppError


class FakeEmployee:
    """Minimal stand-in for an Employee ORM instance."""

    def __init__(self, id: str, manager_id: str | None = None):
        self.id = id
        self.manager_id = manager_id
        self.deleted_at = None


class FakeEmployeeRepo:
    """In-memory repo used to test cycle detection logic."""

    def __init__(self, employees: list[FakeEmployee]):
        self._by_id = {e.id: e for e in employees}

    async def get_by_id(self, employee_id: str):
        return self._by_id.get(employee_id)


class FakeUoW:
    def __init__(self, employees: list[FakeEmployee]):
        self.employees = FakeEmployeeRepo(employees)


@pytest.mark.asyncio
async def test_no_cycle_in_chain():
    """Setting manager when no cycle exists should succeed."""
    from app.application.employees.update_employee import _check_manager_cycle

    employees = [
        FakeEmployee("A"),
        FakeEmployee("B", manager_id=None),
        FakeEmployee("C", manager_id="B"),
    ]
    uow = FakeUoW(employees)

    # C -> B -> (no manager) — setting A's manager to C should be fine
    await _check_manager_cycle(uow, "A", "C")


@pytest.mark.asyncio
async def test_direct_self_manager_raises():
    """An employee cannot be their own manager."""
    from app.application.employees.update_employee import _check_manager_cycle

    employees = [FakeEmployee("A")]
    uow = FakeUoW(employees)

    with pytest.raises(ValidationAppError, match="cycle"):
        await _check_manager_cycle(uow, "A", "A")


@pytest.mark.asyncio
async def test_transitive_cycle_raises():
    """A -> B -> C — setting C's manager to A would create a cycle."""
    from app.application.employees.update_employee import _check_manager_cycle

    employees = [
        FakeEmployee("A", manager_id=None),
        FakeEmployee("B", manager_id="A"),
        FakeEmployee("C", manager_id="B"),
    ]
    uow = FakeUoW(employees)

    with pytest.raises(ValidationAppError, match="cycle"):
        await _check_manager_cycle(uow, "A", "C")
