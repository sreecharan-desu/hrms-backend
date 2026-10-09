"""Employee Pydantic schemas for request/response."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, EmailStr, Field


class CreateEmployeeRequest(BaseModel):
    employee_code: str = Field(..., min_length=1, max_length=30)
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    joining_date: date
    phone: str | None = Field(None, max_length=20)
    date_of_birth: date | None = None
    status: str = Field("ACTIVE", max_length=20)
    department_id: str | None = None
    designation: str | None = Field(None, max_length=120)
    manager_id: str | None = None
    location: str | None = Field(None, max_length=120)
    emergency_contact: dict | None = None
    profile: dict | None = None
    user_id: str | None = None


class UpdateEmployeeRequest(BaseModel):
    first_name: str | None = Field(None, min_length=1, max_length=100)
    last_name: str | None = Field(None, min_length=1, max_length=100)
    email: EmailStr | None = None
    phone: str | None = Field(None, max_length=20)
    date_of_birth: date | None = None
    joining_date: date | None = None
    status: str | None = Field(None, max_length=20)
    department_id: str | None = None
    designation: str | None = Field(None, max_length=120)
    manager_id: str | None = None
    location: str | None = Field(None, max_length=120)
    emergency_contact: dict | None = None
    profile: dict | None = None
    user_id: str | None = None


class EmployeeOut(BaseModel):
    id: str
    employee_code: str
    first_name: str
    last_name: str
    email: str
    phone: str | None = None
    date_of_birth: date | None = None
    joining_date: date | None = None
    status: str
    department_id: str | None = None
    designation: str | None = None
    manager_id: str | None = None
    location: str | None = None
    emergency_contact: dict | None = None
    profile: dict | None = None
    user_id: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class CompensationOut(BaseModel):
    id: str
    employee_id: str
    salary: Decimal
    currency: str
    effective_from: date | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class EmployeeWithCompensationOut(EmployeeOut):
    compensation: CompensationOut | None = None


class UpdateCompensationRequest(BaseModel):
    salary: Decimal = Field(..., gt=0)
    currency: str = Field("INR", min_length=3, max_length=3)
    effective_from: date | None = None
