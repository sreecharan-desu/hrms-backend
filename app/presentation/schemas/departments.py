"""Department Pydantic schemas for request/response."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class CreateDepartmentRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    code: str = Field(..., min_length=1, max_length=30)
    parent_id: str | None = None
    head_employee_id: str | None = None


class UpdateDepartmentRequest(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=120)
    code: str | None = Field(None, min_length=1, max_length=30)
    parent_id: str | None = None
    head_employee_id: str | None = None


class DepartmentOut(BaseModel):
    id: str
    name: str
    code: str
    parent_id: str | None = None
    head_employee_id: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
