"""Performance Pydantic schemas."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field


class CreateCycleRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    start_date: date
    end_date: date
    status: str = Field("ACTIVE", max_length=20)


class GoalInput(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = Field(None, max_length=2000)
    weight: Decimal | None = Field(None, ge=0, le=100)
    target_date: date | None = None
    status: str = Field("OPEN", max_length=20)
    achievement: Decimal | None = Field(None, ge=0, le=100)


class CreateReviewRequest(BaseModel):
    cycle_id: str
    employee_id: str
    reviewer_id: str | None = None
    self_rating: Decimal | None = Field(None, ge=0, le=5)
    manager_rating: Decimal | None = Field(None, ge=0, le=5)
    self_comments: str | None = Field(None, max_length=5000)
    manager_comments: str | None = Field(None, max_length=5000)
    goals: list[GoalInput] | None = None
