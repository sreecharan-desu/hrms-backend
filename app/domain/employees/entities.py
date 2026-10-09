"""Employee domain entities – lightweight dataclasses for use-case logic."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class EmployeeEntity:
    id: str
    employee_code: str
    first_name: str
    last_name: str
    email: str
    phone: str | None = None
    date_of_birth: date | None = None
    joining_date: date | None = None
    status: str = "ACTIVE"
    department_id: str | None = None
    designation: str | None = None
    manager_id: str | None = None
    location: str | None = None
    emergency_contact: dict | None = None
    profile: dict | None = None
    user_id: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    deleted_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class CompensationEntity:
    id: str
    employee_id: str
    salary: Decimal
    currency: str = "INR"
    effective_from: date | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
