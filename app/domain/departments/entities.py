"""Department domain entity."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class DepartmentEntity:
    id: str
    name: str
    code: str
    parent_id: str | None = None
    head_employee_id: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    deleted_at: datetime | None = None
