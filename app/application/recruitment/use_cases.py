"""Recruitment use cases – jobs, applications, interviews, feedback."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from app.application.common.audit import record_audit
from app.core.dependencies import CurrentUser, RequestContext
from app.core.exceptions import AppError, NotFoundError, ValidationAppError
from app.domain.recruitment.enums import ApplicationStage, JobStatus
from app.infrastructure.database.models.recruitment import (
    Interview,
    InterviewFeedback,
    Job,
    JobApplication,
)
from app.infrastructure.database.uow import SqlAlchemyUnitOfWork

# ── Custom errors ────────────────────────────────────────────────────

class ApplicationInvalidStageTransitionError(AppError):
    code = "APPLICATION_INVALID_STAGE_TRANSITION"
    message = "Invalid application stage transition."
    status_code = 422


class ApplicationNotInterviewableError(AppError):
    code = "APPLICATION_NOT_INTERVIEWABLE"
    message = "Application is not in an interviewable stage."
    status_code = 422


_INTERVIEWABLE_STAGES: frozenset[str] = frozenset({
    ApplicationStage.INTERVIEW,
    ApplicationStage.TECHNICAL,
    ApplicationStage.HR,
    ApplicationStage.OFFER,
})


# ── Job DTOs ─────────────────────────────────────────────────────────

@dataclass(frozen=True, slots=True)
class JobDTO:
    id: str
    title: str
    description: str | None
    department_id: str | None
    location: str | None
    employment_type: str | None
    salary_min: str | None
    salary_max: str | None
    currency: str
    positions: int
    status: str
    hiring_manager_id: str | None
    closes_at: str | None
    created_at: str
    updated_at: str


def _job_to_dto(j: Job) -> JobDTO:
    return JobDTO(
        id=j.id,
        title=j.title,
        description=j.description,
        department_id=j.department_id,
        location=j.location,
        employment_type=j.employment_type,
        salary_min=str(j.salary_min) if j.salary_min is not None else None,
        salary_max=str(j.salary_max) if j.salary_max is not None else None,
        currency=j.currency,
        positions=j.positions,
        status=j.status,
        hiring_manager_id=j.hiring_manager_id,
        closes_at=j.closes_at.isoformat() if j.closes_at else None,
        created_at=j.created_at.isoformat() if j.created_at else "",
        updated_at=j.updated_at.isoformat() if j.updated_at else "",
    )


@dataclass(frozen=True, slots=True)
class ListJobResult:
    items: list[JobDTO]
    total: int
    offset: int
    limit: int


# ── Application DTOs ─────────────────────────────────────────────────

@dataclass(frozen=True, slots=True)
class ApplicationDTO:
    id: str
    job_id: str
    candidate_name: str
    candidate_email: str
    candidate_phone: str | None
    resume_document_id: str | None
    stage: str
    notes: str | None
    created_at: str
    updated_at: str


def _app_to_dto(a: JobApplication) -> ApplicationDTO:
    return ApplicationDTO(
        id=a.id,
        job_id=a.job_id,
        candidate_name=a.candidate_name,
        candidate_email=a.candidate_email,
        candidate_phone=a.candidate_phone,
        resume_document_id=a.resume_document_id,
        stage=a.stage,
        notes=a.notes,
        created_at=a.created_at.isoformat() if a.created_at else "",
        updated_at=a.updated_at.isoformat() if a.updated_at else "",
    )


@dataclass(frozen=True, slots=True)
class ListApplicationResult:
    items: list[ApplicationDTO]
    total: int
    offset: int
    limit: int


# ── Interview DTOs ───────────────────────────────────────────────────

@dataclass(frozen=True, slots=True)
class InterviewDTO:
    id: str
    application_id: str
    interviewer_id: str | None
    scheduled_at: str
    duration_minutes: int
    interview_type: str | None
    location: str | None
    status: str
    created_at: str
    updated_at: str


def _interview_to_dto(i: Interview) -> InterviewDTO:
    return InterviewDTO(
        id=i.id,
        application_id=i.application_id,
        interviewer_id=i.interviewer_id,
        scheduled_at=i.scheduled_at.isoformat(),
        duration_minutes=i.duration_minutes,
        interview_type=i.interview_type,
        location=i.location,
        status=i.status,
        created_at=i.created_at.isoformat() if i.created_at else "",
        updated_at=i.updated_at.isoformat() if i.updated_at else "",
    )


@dataclass(frozen=True, slots=True)
class FeedbackDTO:
    id: str
    interview_id: str
    evaluator_id: str | None
    rating: int | None
    strengths: str | None
    weaknesses: str | None
    recommendation: str | None
    comments: str | None
    created_at: str
    updated_at: str


def _feedback_to_dto(f: InterviewFeedback) -> FeedbackDTO:
    return FeedbackDTO(
        id=f.id,
        interview_id=f.interview_id,
        evaluator_id=f.evaluator_id,
        rating=f.rating,
        strengths=f.strengths,
        weaknesses=f.weaknesses,
        recommendation=f.recommendation,
        comments=f.comments,
        created_at=f.created_at.isoformat() if f.created_at else "",
        updated_at=f.updated_at.isoformat() if f.updated_at else "",
    )


# ═══════════════════════════════════════════════════════════════════
#  JOBS
# ═══════════════════════════════════════════════════════════════════

@dataclass(frozen=True, slots=True)
class CreateJobInput:
    title: str
    description: str | None = None
    department_id: str | None = None
    location: str | None = None
    employment_type: str | None = None
    salary_min: str | None = None
    salary_max: str | None = None
    currency: str = "INR"
    positions: int = 1
    hiring_manager_id: str | None = None
    closes_at: str | None = None


async def create_job(
    uow: SqlAlchemyUnitOfWork,
    user: CurrentUser,
    data: CreateJobInput,
    ctx: RequestContext,
) -> JobDTO:
    from datetime import date as date_cls
    from decimal import Decimal

    job = Job(
        title=data.title,
        description=data.description,
        department_id=data.department_id,
        location=data.location,
        employment_type=data.employment_type,
        salary_min=Decimal(data.salary_min) if data.salary_min else None,
        salary_max=Decimal(data.salary_max) if data.salary_max else None,
        currency=data.currency,
        positions=data.positions,
        status=JobStatus.DRAFT,
        hiring_manager_id=data.hiring_manager_id,
        closes_at=date_cls.fromisoformat(data.closes_at) if data.closes_at else None,
    )
    await uow.jobs.create(job)
    await record_audit(
        uow.session,
        actor_id=user.id,
        action="job.create",
        entity_type="Job",
        entity_id=job.id,
        new_values={"title": data.title, "status": JobStatus.DRAFT},
        ip_address=ctx.ip,
        user_agent=ctx.user_agent,
        request_id=ctx.request_id,
    )
    await uow.commit()
    return _job_to_dto(job)


async def list_jobs(
    uow: SqlAlchemyUnitOfWork,
    *,
    status: str | None = None,
    department_id: str | None = None,
    offset: int = 0,
    limit: int = 50,
) -> ListJobResult:
    items = await uow.jobs.list_filtered(
        status=status, department_id=department_id, offset=offset, limit=limit
    )
    total = await uow.jobs.count_filtered(status=status, department_id=department_id)
    return ListJobResult(
        items=[_job_to_dto(j) for j in items],
        total=total,
        offset=offset,
        limit=limit,
    )


async def get_job(uow: SqlAlchemyUnitOfWork, job_id: str) -> JobDTO:
    job = await uow.jobs.get_by_id(job_id)
    if job is None:
        raise NotFoundError("Job not found.")
    return _job_to_dto(job)


@dataclass(frozen=True, slots=True)
class UpdateJobInput:
    title: str | None = None
    description: str | None = None
    department_id: str | None = None
    location: str | None = None
    employment_type: str | None = None
    salary_min: str | None = None
    salary_max: str | None = None
    currency: str | None = None
    positions: int | None = None
    hiring_manager_id: str | None = None
    closes_at: str | None = None


async def update_job(
    uow: SqlAlchemyUnitOfWork,
    user: CurrentUser,
    job_id: str,
    data: UpdateJobInput,
    ctx: RequestContext,
) -> JobDTO:
    from datetime import date as date_cls
    from decimal import Decimal

    job = await uow.jobs.get_by_id(job_id)
    if job is None:
        raise NotFoundError("Job not found.")

    old_values: dict[str, Any] = {}
    new_values: dict[str, Any] = {}

    for field in (
        "title", "description", "department_id", "location",
        "employment_type", "currency", "positions", "hiring_manager_id",
    ):
        val = getattr(data, field)
        if val is not None:
            old_values[field] = getattr(job, field)
            setattr(job, field, val)
            new_values[field] = val

    if data.salary_min is not None:
        old_values["salary_min"] = str(job.salary_min) if job.salary_min else None
        job.salary_min = Decimal(data.salary_min)
        new_values["salary_min"] = data.salary_min
    if data.salary_max is not None:
        old_values["salary_max"] = str(job.salary_max) if job.salary_max else None
        job.salary_max = Decimal(data.salary_max)
        new_values["salary_max"] = data.salary_max
    if data.closes_at is not None:
        old_values["closes_at"] = job.closes_at.isoformat() if job.closes_at else None
        job.closes_at = date_cls.fromisoformat(data.closes_at)
        new_values["closes_at"] = data.closes_at

    await uow.jobs.update(job)
    if new_values:
        await record_audit(
            uow.session,
            actor_id=user.id,
            action="job.update",
            entity_type="Job",
            entity_id=job.id,
            old_values=old_values,
            new_values=new_values,
            ip_address=ctx.ip,
            user_agent=ctx.user_agent,
            request_id=ctx.request_id,
        )
    await uow.commit()
    return _job_to_dto(job)


async def delete_job(
    uow: SqlAlchemyUnitOfWork,
    user: CurrentUser,
    job_id: str,
    ctx: RequestContext,
) -> None:
    job = await uow.jobs.get_by_id(job_id)
    if job is None:
        raise NotFoundError("Job not found.")
    await uow.jobs.soft_delete(job, deleted_by=user.id, deleted_at=datetime.now(UTC))
    await record_audit(
        uow.session,
        actor_id=user.id,
        action="job.delete",
        entity_type="Job",
        entity_id=job.id,
        old_values={"status": job.status},
        ip_address=ctx.ip,
        user_agent=ctx.user_agent,
        request_id=ctx.request_id,
    )
    await uow.commit()


async def publish_job(
    uow: SqlAlchemyUnitOfWork,
    user: CurrentUser,
    job_id: str,
    ctx: RequestContext,
) -> JobDTO:
    job = await uow.jobs.get_by_id(job_id)
    if job is None:
        raise NotFoundError("Job not found.")
    if job.status not in (JobStatus.DRAFT, JobStatus.ON_HOLD):
        raise ValidationAppError(
            f"Cannot publish a job with status {job.status}."
        )
    old_status = job.status
    job.status = JobStatus.OPEN
    await uow.jobs.update(job)
    await record_audit(
        uow.session,
        actor_id=user.id,
        action="job.publish",
        entity_type="Job",
        entity_id=job.id,
        old_values={"status": old_status},
        new_values={"status": JobStatus.OPEN},
        ip_address=ctx.ip,
        user_agent=ctx.user_agent,
        request_id=ctx.request_id,
    )
    await uow.commit()
    return _job_to_dto(job)


async def close_job(
    uow: SqlAlchemyUnitOfWork,
    user: CurrentUser,
    job_id: str,
    ctx: RequestContext,
) -> JobDTO:
    job = await uow.jobs.get_by_id(job_id)
    if job is None:
        raise NotFoundError("Job not found.")
    if job.status == JobStatus.CLOSED:
        raise ValidationAppError("Job is already closed.")
    old_status = job.status
    job.status = JobStatus.CLOSED
    await uow.jobs.update(job)
    await record_audit(
        uow.session,
        actor_id=user.id,
        action="job.close",
        entity_type="Job",
        entity_id=job.id,
        old_values={"status": old_status},
        new_values={"status": JobStatus.CLOSED},
        ip_address=ctx.ip,
        user_agent=ctx.user_agent,
        request_id=ctx.request_id,
    )
    await uow.commit()
    return _job_to_dto(job)


# ═══════════════════════════════════════════════════════════════════
#  APPLICATIONS
# ═══════════════════════════════════════════════════════════════════

@dataclass(frozen=True, slots=True)
class CreateApplicationInput:
    job_id: str
    candidate_name: str
    candidate_email: str
    candidate_phone: str | None = None
    resume_document_id: str | None = None
    notes: str | None = None


async def create_application(
    uow: SqlAlchemyUnitOfWork,
    user: CurrentUser,
    data: CreateApplicationInput,
    ctx: RequestContext,
) -> ApplicationDTO:
    job = await uow.jobs.get_by_id(data.job_id)
    if job is None:
        raise NotFoundError("Job not found.")
    if job.status != JobStatus.OPEN:
        raise ValidationAppError("Cannot apply to a job that is not open.")

    application = JobApplication(
        job_id=data.job_id,
        candidate_name=data.candidate_name,
        candidate_email=data.candidate_email,
        candidate_phone=data.candidate_phone,
        resume_document_id=data.resume_document_id,
        notes=data.notes,
        stage=ApplicationStage.APPLIED,
    )
    await uow.job_applications.create(application)
    await record_audit(
        uow.session,
        actor_id=user.id,
        action="application.create",
        entity_type="JobApplication",
        entity_id=application.id,
        new_values={
            "job_id": data.job_id,
            "candidate_name": data.candidate_name,
            "stage": ApplicationStage.APPLIED,
        },
        ip_address=ctx.ip,
        user_agent=ctx.user_agent,
        request_id=ctx.request_id,
    )
    await uow.commit()
    return _app_to_dto(application)


async def list_applications(
    uow: SqlAlchemyUnitOfWork,
    *,
    job_id: str | None = None,
    stage: str | None = None,
    offset: int = 0,
    limit: int = 50,
) -> ListApplicationResult:
    items = await uow.job_applications.list_filtered(
        job_id=job_id, stage=stage, offset=offset, limit=limit
    )
    total = await uow.job_applications.count_filtered(job_id=job_id, stage=stage)
    return ListApplicationResult(
        items=[_app_to_dto(a) for a in items],
        total=total,
        offset=offset,
        limit=limit,
    )


async def get_application(
    uow: SqlAlchemyUnitOfWork, application_id: str
) -> ApplicationDTO:
    app = await uow.job_applications.get_by_id(application_id)
    if app is None:
        raise NotFoundError("Application not found.")
    return _app_to_dto(app)


@dataclass(frozen=True, slots=True)
class UpdateApplicationInput:
    candidate_phone: str | None = None
    resume_document_id: str | None = None
    notes: str | None = None


async def update_application(
    uow: SqlAlchemyUnitOfWork,
    user: CurrentUser,
    application_id: str,
    data: UpdateApplicationInput,
    ctx: RequestContext,
) -> ApplicationDTO:
    app = await uow.job_applications.get_by_id(application_id)
    if app is None:
        raise NotFoundError("Application not found.")

    old_values: dict[str, Any] = {}
    new_values: dict[str, Any] = {}
    for field in ("candidate_phone", "resume_document_id", "notes"):
        val = getattr(data, field)
        if val is not None:
            old_values[field] = getattr(app, field)
            setattr(app, field, val)
            new_values[field] = val

    await uow.job_applications.update(app)
    if new_values:
        await record_audit(
            uow.session,
            actor_id=user.id,
            action="application.update",
            entity_type="JobApplication",
            entity_id=app.id,
            old_values=old_values,
            new_values=new_values,
            ip_address=ctx.ip,
            user_agent=ctx.user_agent,
            request_id=ctx.request_id,
        )
    await uow.commit()
    return _app_to_dto(app)


@dataclass(frozen=True, slots=True)
class MoveStageInput:
    stage: str
    note: str | None = None


async def move_application_stage(
    uow: SqlAlchemyUnitOfWork,
    user: CurrentUser,
    application_id: str,
    data: MoveStageInput,
    ctx: RequestContext,
) -> ApplicationDTO:
    app = await uow.job_applications.get_for_update(application_id)
    if app is None:
        raise NotFoundError("Application not found.")

    from_stage = ApplicationStage(app.stage)
    to_stage = ApplicationStage(data.stage)

    if not ApplicationStage.can_transition(from_stage, to_stage):
        raise ApplicationInvalidStageTransitionError(
            f"Cannot transition from {from_stage} to {to_stage}."
        )

    app.stage = to_stage
    if data.note:
        existing = app.notes or ""
        app.notes = f"{existing}\n[{to_stage}] {data.note}".strip()

    await uow.job_applications.update(app)
    await record_audit(
        uow.session,
        actor_id=user.id,
        action="application.move_stage",
        entity_type="JobApplication",
        entity_id=app.id,
        old_values={"stage": from_stage.value},
        new_values={"stage": to_stage.value},
        ip_address=ctx.ip,
        user_agent=ctx.user_agent,
        request_id=ctx.request_id,
    )
    await uow.commit()
    return _app_to_dto(app)


# ═══════════════════════════════════════════════════════════════════
#  INTERVIEWS
# ═══════════════════════════════════════════════════════════════════

@dataclass(frozen=True, slots=True)
class CreateInterviewInput:
    interviewer_id: str | None = None
    scheduled_at: str = ""
    duration_minutes: int = 60
    interview_type: str | None = None
    location: str | None = None


async def create_interview(
    uow: SqlAlchemyUnitOfWork,
    user: CurrentUser,
    application_id: str,
    data: CreateInterviewInput,
    ctx: RequestContext,
) -> InterviewDTO:
    app = await uow.job_applications.get_by_id(application_id)
    if app is None:
        raise NotFoundError("Application not found.")

    if app.stage not in _INTERVIEWABLE_STAGES:
        raise ApplicationNotInterviewableError(
            f"Application stage '{app.stage}' is not interviewable."
        )

    interview = Interview(
        application_id=application_id,
        interviewer_id=data.interviewer_id,
        scheduled_at=datetime.fromisoformat(data.scheduled_at),
        duration_minutes=data.duration_minutes,
        interview_type=data.interview_type,
        location=data.location,
        status="SCHEDULED",
    )
    await uow.interviews.create(interview)
    await record_audit(
        uow.session,
        actor_id=user.id,
        action="interview.create",
        entity_type="Interview",
        entity_id=interview.id,
        new_values={
            "application_id": application_id,
            "scheduled_at": data.scheduled_at,
        },
        ip_address=ctx.ip,
        user_agent=ctx.user_agent,
        request_id=ctx.request_id,
    )
    await uow.commit()
    return _interview_to_dto(interview)


async def list_interviews(
    uow: SqlAlchemyUnitOfWork,
    application_id: str,
    *,
    offset: int = 0,
    limit: int = 50,
) -> list[InterviewDTO]:
    items = await uow.interviews.list_by_application(
        application_id, offset=offset, limit=limit
    )
    return [_interview_to_dto(i) for i in items]


@dataclass(frozen=True, slots=True)
class UpdateInterviewInput:
    scheduled_at: str | None = None
    duration_minutes: int | None = None
    interview_type: str | None = None
    location: str | None = None
    status: str | None = None


async def update_interview(
    uow: SqlAlchemyUnitOfWork,
    user: CurrentUser,
    interview_id: str,
    data: UpdateInterviewInput,
    ctx: RequestContext,
) -> InterviewDTO:
    interview = await uow.interviews.get_by_id(interview_id)
    if interview is None:
        raise NotFoundError("Interview not found.")

    old_values: dict[str, Any] = {}
    new_values: dict[str, Any] = {}
    if data.scheduled_at is not None:
        old_values["scheduled_at"] = interview.scheduled_at.isoformat()
        interview.scheduled_at = datetime.fromisoformat(data.scheduled_at)
        new_values["scheduled_at"] = data.scheduled_at
    if data.duration_minutes is not None:
        old_values["duration_minutes"] = interview.duration_minutes
        interview.duration_minutes = data.duration_minutes
        new_values["duration_minutes"] = data.duration_minutes
    if data.interview_type is not None:
        old_values["interview_type"] = interview.interview_type
        interview.interview_type = data.interview_type
        new_values["interview_type"] = data.interview_type
    if data.location is not None:
        old_values["location"] = interview.location
        interview.location = data.location
        new_values["location"] = data.location
    if data.status is not None:
        old_values["status"] = interview.status
        interview.status = data.status
        new_values["status"] = data.status

    await uow.interviews.update(interview)
    if new_values:
        await record_audit(
            uow.session,
            actor_id=user.id,
            action="interview.update",
            entity_type="Interview",
            entity_id=interview.id,
            old_values=old_values,
            new_values=new_values,
            ip_address=ctx.ip,
            user_agent=ctx.user_agent,
            request_id=ctx.request_id,
        )
    await uow.commit()
    return _interview_to_dto(interview)


# ── Feedback ─────────────────────────────────────────────────────────

@dataclass(frozen=True, slots=True)
class CreateFeedbackInput:
    rating: int | None = None
    strengths: str | None = None
    weaknesses: str | None = None
    recommendation: str | None = None
    comments: str | None = None


async def create_interview_feedback(
    uow: SqlAlchemyUnitOfWork,
    user: CurrentUser,
    interview_id: str,
    data: CreateFeedbackInput,
    ctx: RequestContext,
) -> FeedbackDTO:
    interview = await uow.interviews.get_by_id(interview_id)
    if interview is None:
        raise NotFoundError("Interview not found.")

    feedback = InterviewFeedback(
        interview_id=interview_id,
        evaluator_id=user.id,
        rating=data.rating,
        strengths=data.strengths,
        weaknesses=data.weaknesses,
        recommendation=data.recommendation,
        comments=data.comments,
    )
    await uow.interview_feedbacks.create(feedback)
    await record_audit(
        uow.session,
        actor_id=user.id,
        action="interview.feedback",
        entity_type="InterviewFeedback",
        entity_id=feedback.id,
        new_values={
            "interview_id": interview_id,
            "rating": data.rating,
            "recommendation": data.recommendation,
        },
        ip_address=ctx.ip,
        user_agent=ctx.user_agent,
        request_id=ctx.request_id,
    )
    await uow.commit()
    return _feedback_to_dto(feedback)
