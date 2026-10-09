"""Recruitment models: Job, JobApplication, Interview, InterviewFeedback."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.domain.recruitment.enums import ApplicationStage, JobStatus
from app.infrastructure.database.models.mixins import (
    SoftDeleteMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)


class Job(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "jobs"
    __table_args__ = (
        Index("ix_jobs_status", "status"),
        Index("ix_jobs_department_id", "department_id"),
        Index("ix_jobs_created_at", "created_at"),
    )

    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    department_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("departments.id", ondelete="SET NULL"),
        nullable=True,
    )
    location: Mapped[str | None] = mapped_column(String(120), nullable=True)
    employment_type: Mapped[str | None] = mapped_column(String(30), nullable=True)
    salary_min: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    salary_max: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="INR")
    positions: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=JobStatus.DRAFT,
    )
    hiring_manager_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("employees.id", ondelete="SET NULL"),
        nullable=True,
    )
    closes_at: Mapped[date | None] = mapped_column(Date, nullable=True)

    applications: Mapped[list[JobApplication]] = relationship(back_populates="job")


class JobApplication(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "job_applications"
    __table_args__ = (
        Index("ix_job_applications_job_id", "job_id"),
        Index("ix_job_applications_stage", "stage"),
        Index("ix_job_applications_created_at", "created_at"),
    )

    job_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
    )
    candidate_name: Mapped[str] = mapped_column(String(200), nullable=False)
    candidate_email: Mapped[str] = mapped_column(String(255), nullable=False)
    candidate_phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    resume_document_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("documents.id", ondelete="SET NULL"),
        nullable=True,
    )
    stage: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=ApplicationStage.APPLIED,
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    job: Mapped[Job] = relationship(back_populates="applications")
    interviews: Mapped[list[Interview]] = relationship(back_populates="application")


class Interview(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "interviews"
    __table_args__ = (
        Index("ix_interviews_application_id", "application_id"),
        Index("ix_interviews_interviewer_id", "interviewer_id"),
    )

    application_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("job_applications.id", ondelete="CASCADE"),
        nullable=False,
    )
    interviewer_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("employees.id", ondelete="SET NULL"),
        nullable=True,
    )
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=60)
    interview_type: Mapped[str | None] = mapped_column(String(30), nullable=True)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="SCHEDULED")

    application: Mapped[JobApplication] = relationship(back_populates="interviews")
    feedback: Mapped[list[InterviewFeedback]] = relationship(back_populates="interview")


class InterviewFeedback(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "interview_feedbacks"
    __table_args__ = (Index("ix_interview_feedbacks_interview_id", "interview_id"),)

    interview_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("interviews.id", ondelete="CASCADE"),
        nullable=False,
    )
    evaluator_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("employees.id", ondelete="SET NULL"),
        nullable=True,
    )
    rating: Mapped[int | None] = mapped_column(Integer, nullable=True)
    strengths: Mapped[str | None] = mapped_column(Text, nullable=True)
    weaknesses: Mapped[str | None] = mapped_column(Text, nullable=True)
    recommendation: Mapped[str | None] = mapped_column(String(30), nullable=True)
    comments: Mapped[str | None] = mapped_column(Text, nullable=True)

    interview: Mapped[Interview] = relationship(back_populates="feedback")
