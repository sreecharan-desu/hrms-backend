"""Unit tests for department parent cycle detection."""

from __future__ import annotations

import pytest

from app.core.exceptions import ValidationAppError


class FakeDepartment:
    def __init__(self, id: str, parent_id: str | None = None):
        self.id = id
        self.parent_id = parent_id
        self.deleted_at = None


class FakeDepartmentRepo:
    def __init__(self, departments: list[FakeDepartment]):
        self._by_id = {d.id: d for d in departments}

    async def get_by_id(self, department_id: str):
        return self._by_id.get(department_id)


class FakeUoW:
    def __init__(self, departments: list[FakeDepartment]):
        self.departments = FakeDepartmentRepo(departments)


@pytest.mark.asyncio
async def test_no_parent_cycle():
    from app.application.departments.update_department import _check_parent_cycle

    depts = [
        FakeDepartment("A"),
        FakeDepartment("B", parent_id=None),
    ]
    uow = FakeUoW(depts)
    await _check_parent_cycle(uow, "A", "B")


@pytest.mark.asyncio
async def test_direct_self_parent_raises():
    from app.application.departments.update_department import _check_parent_cycle

    depts = [FakeDepartment("A")]
    uow = FakeUoW(depts)

    with pytest.raises(ValidationAppError, match="cycle"):
        await _check_parent_cycle(uow, "A", "A")


@pytest.mark.asyncio
async def test_transitive_parent_cycle_raises():
    from app.application.departments.update_department import _check_parent_cycle

    depts = [
        FakeDepartment("A"),
        FakeDepartment("B", parent_id="A"),
        FakeDepartment("C", parent_id="B"),
    ]
    uow = FakeUoW(depts)

    with pytest.raises(ValidationAppError, match="cycle"):
        await _check_parent_cycle(uow, "A", "C")
