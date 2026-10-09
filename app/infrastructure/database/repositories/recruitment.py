"""Concrete SQLAlchemy recruitment repositories."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.models.recruitment import (
    Interview,
    InterviewFeedback,
    Job,
    JobApplication,
)


class SqlJobRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, job_id: str) -> Job | None:
        result = await self._session.execute(
            select(Job).where(and_(Job.id == job_id, Job.deleted_at.is_(None)))
        )
        return result.scalars().first()

    async def list_filtered(
        self,
        *,
        status: str | None = None,
        department_id: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> Sequence[Job]:
        stmt = select(Job).where(Job.deleted_at.is_(None))
        if status is not None:
            stmt = stmt.where(Job.status == status)
        if department_id is not None:
            stmt = stmt.where(Job.department_id == department_id)
        stmt = stmt.order_by(Job.created_at.desc()).offset(offset).limit(limit)
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def count_filtered(
        self,
        *,
        status: str | None = None,
        department_id: str | None = None,
    ) -> int:
        stmt = select(func.count(Job.id)).where(Job.deleted_at.is_(None))
        if status is not None:
            stmt = stmt.where(Job.status == status)
        if department_id is not None:
            stmt = stmt.where(Job.department_id == department_id)
        result = await self._session.execute(stmt)
        return result.scalar_one()

    async def create(self, job: Job) -> Job:
        self._session.add(job)
        await self._session.flush()
        return job

    async def update(self, _job: Job) -> Job:
        await self._session.flush()
        return _job

    async def soft_delete(self, job: Job, *, deleted_by: str, deleted_at: datetime) -> None:
        job.deleted_at = deleted_at
        job.deleted_by = deleted_by
        await self._session.flush()


class SqlJobApplicationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, application_id: str) -> JobApplication | None:
        result = await self._session.execute(
            select(JobApplication).where(JobApplication.id == application_id)
        )
        return result.scalars().first()

    async def get_for_update(self, application_id: str) -> JobApplication | None:
        result = await self._session.execute(
            select(JobApplication)
            .where(JobApplication.id == application_id)
            .with_for_update()
        )
        return result.scalars().first()

    async def list_filtered(
        self,
        *,
        job_id: str | None = None,
        stage: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> Sequence[JobApplication]:
        stmt = select(JobApplication)
        if job_id is not None:
            stmt = stmt.where(JobApplication.job_id == job_id)
        if stage is not None:
            stmt = stmt.where(JobApplication.stage == stage)
        stmt = stmt.order_by(JobApplication.created_at.desc()).offset(offset).limit(limit)
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def count_filtered(
        self,
        *,
        job_id: str | None = None,
        stage: str | None = None,
    ) -> int:
        stmt = select(func.count(JobApplication.id))
        if job_id is not None:
            stmt = stmt.where(JobApplication.job_id == job_id)
        if stage is not None:
            stmt = stmt.where(JobApplication.stage == stage)
        result = await self._session.execute(stmt)
        return result.scalar_one()

    async def create(self, application: JobApplication) -> JobApplication:
        self._session.add(application)
        await self._session.flush()
        return application

    async def update(self, _application: JobApplication) -> JobApplication:
        await self._session.flush()
        return _application


class SqlInterviewRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, interview_id: str) -> Interview | None:
        result = await self._session.execute(
            select(Interview).where(Interview.id == interview_id)
        )
        return result.scalars().first()

    async def list_by_application(
        self,
        application_id: str,
        *,
        offset: int = 0,
        limit: int = 50,
    ) -> Sequence[Interview]:
        stmt = (
            select(Interview)
            .where(Interview.application_id == application_id)
            .order_by(Interview.scheduled_at.asc())
            .offset(offset)
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def list_by_interviewer(
        self,
        interviewer_id: str,
        *,
        offset: int = 0,
        limit: int = 50,
    ) -> Sequence[Interview]:
        stmt = (
            select(Interview)
            .where(Interview.interviewer_id == interviewer_id)
            .order_by(Interview.scheduled_at.asc())
            .offset(offset)
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def create(self, interview: Interview) -> Interview:
        self._session.add(interview)
        await self._session.flush()
        return interview

    async def update(self, _interview: Interview) -> Interview:
        await self._session.flush()
        return _interview


class SqlInterviewFeedbackRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_interview(self, interview_id: str) -> Sequence[InterviewFeedback]:
        result = await self._session.execute(
            select(InterviewFeedback).where(
                InterviewFeedback.interview_id == interview_id
            )
        )
        return result.scalars().all()

    async def create(self, feedback: InterviewFeedback) -> InterviewFeedback:
        self._session.add(feedback)
        await self._session.flush()
        return feedback
