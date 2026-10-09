"""Leave Pydantic schemas."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field


class ApplyLeaveRequest(BaseModel):
    leave_type_id: str
    start_date: date
    end_date: date
    days: Decimal = Field(gt=0)
    reason: str | None = Field(None, max_length=1000)


class ReviewLeaveRequest(BaseModel):
    comment: str | None = Field(None, max_length=1000)


class RejectLeaveRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=1000)
