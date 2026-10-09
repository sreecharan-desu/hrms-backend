"""Recruitment Pydantic schemas."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field

# ── Jobs ─────────────────────────────────────────────────────────────

class CreateJobRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = Field(None, max_length=5000)
    department_id: str | None = None
    location: str | None = Field(None, max_length=120)
    employment_type: str | None = Field(None, max_length=30)
    salary_min: Decimal | None = Field(None, ge=0)
    salary_max: Decimal | None = Field(None, ge=0)
    currency: str = Field("INR", max_length=3)
    positions: int = Field(1, ge=1)
    hiring_manager_id: str | None = None
    closes_at: date | None = None


class UpdateJobRequest(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=200)
    description: str | None = Field(None, max_length=5000)
    department_id: str | None = None
    location: str | None = Field(None, max_length=120)
    employment_type: str | None = Field(None, max_length=30)
    salary_min: Decimal | None = Field(None, ge=0)
    salary_max: Decimal | None = Field(None, ge=0)
    currency: str | None = Field(None, max_length=3)
    positions: int | None = Field(None, ge=1)
    hiring_manager_id: str | None = None
    closes_at: date | None = None


# ── Applications ─────────────────────────────────────────────────────

class CreateApplicationRequest(BaseModel):
    job_id: str
    candidate_name: str = Field(min_length=1, max_length=200)
    candidate_email: str = Field(min_length=1, max_length=255)
    candidate_phone: str | None = Field(None, max_length=20)
    resume_document_id: str | None = None
    notes: str | None = Field(None, max_length=2000)


class UpdateApplicationRequest(BaseModel):
    candidate_phone: str | None = Field(None, max_length=20)
    resume_document_id: str | None = None
    notes: str | None = Field(None, max_length=2000)


class MoveStageRequest(BaseModel):
    stage: str = Field(min_length=1, max_length=20)
    note: str | None = Field(None, max_length=2000)


# ── Interviews ───────────────────────────────────────────────────────

class CreateInterviewRequest(BaseModel):
    interviewer_id: str | None = None
    scheduled_at: datetime
    duration_minutes: int = Field(60, ge=15, le=480)
    interview_type: str | None = Field(None, max_length=30)
    location: str | None = Field(None, max_length=255)


class UpdateInterviewRequest(BaseModel):
    scheduled_at: datetime | None = None
    duration_minutes: int | None = Field(None, ge=15, le=480)
    interview_type: str | None = Field(None, max_length=30)
    location: str | None = Field(None, max_length=255)
    status: str | None = Field(None, max_length=20)


class CreateFeedbackRequest(BaseModel):
    rating: int | None = Field(None, ge=1, le=5)
    strengths: str | None = Field(None, max_length=2000)
    weaknesses: str | None = Field(None, max_length=2000)
    recommendation: str | None = Field(None, max_length=30)
    comments: str | None = Field(None, max_length=2000)
