"""Recruitment endpoints – /api/v1/jobs/*, /api/v1/applications/*, /api/v1/interviews/*."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.application.recruitment.use_cases import (
    CreateApplicationInput,
    CreateFeedbackInput,
    CreateInterviewInput,
    CreateJobInput,
    MoveStageInput,
    UpdateApplicationInput,
    UpdateInterviewInput,
    UpdateJobInput,
    close_job,
    create_application,
    create_interview,
    create_interview_feedback,
    create_job,
    delete_job,
    get_application,
    get_job,
    list_applications,
    list_interviews,
    list_jobs,
    move_application_stage,
    publish_job,
    update_application,
    update_interview,
    update_job,
)
from app.core.dependencies import (
    CurrentUser,
    RequestContext,
    get_request_context,
    get_uow,
    require_permission,
)
from app.core.permissions import P, Role
from app.core.responses import created_response, no_content_response, success_response
from app.infrastructure.database.uow import SqlAlchemyUnitOfWork
from app.presentation.schemas.recruitment import (
    CreateApplicationRequest,
    CreateFeedbackRequest,
    CreateInterviewRequest,
    CreateJobRequest,
    MoveStageRequest,
    UpdateApplicationRequest,
    UpdateInterviewRequest,
    UpdateJobRequest,
)

# ═══════════════════════════════════════════════════════════════════
#  JOBS
# ═══════════════════════════════════════════════════════════════════

jobs_router = APIRouter(prefix="/jobs", tags=["Recruitment"])


@jobs_router.post("")
async def create_job_endpoint(
    body: CreateJobRequest,
    user: Annotated[CurrentUser, Depends(require_permission(P.RECRUITMENT_CREATE))],
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
):
    data = CreateJobInput(
        title=body.title,
        description=body.description,
        department_id=body.department_id,
        location=body.location,
        employment_type=body.employment_type,
        salary_min=str(body.salary_min) if body.salary_min is not None else None,
        salary_max=str(body.salary_max) if body.salary_max is not None else None,
        currency=body.currency,
        positions=body.positions,
        hiring_manager_id=body.hiring_manager_id,
        closes_at=body.closes_at.isoformat() if body.closes_at else None,
    )
    result = await create_job(uow, user, data, ctx)
    return created_response(data=result.__dict__, message="Job created.")


@jobs_router.get("")
async def list_jobs_endpoint(
    _user: Annotated[CurrentUser, Depends(require_permission(P.RECRUITMENT_READ))],
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    status: str | None = Query(None),
    department_id: str | None = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
):
    result = await list_jobs(
        uow, status=status, department_id=department_id, offset=offset, limit=limit
    )
    return success_response(
        data={
            "items": [i.__dict__ for i in result.items],
            "total": result.total,
            "offset": result.offset,
            "limit": result.limit,
        }
    )


@jobs_router.get("/{job_id}")
async def get_job_endpoint(
    job_id: str,
    _user: Annotated[CurrentUser, Depends(require_permission(P.RECRUITMENT_READ))],
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
):
    result = await get_job(uow, job_id)
    return success_response(data=result.__dict__)


@jobs_router.patch("/{job_id}")
async def update_job_endpoint(
    job_id: str,
    body: UpdateJobRequest,
    user: Annotated[CurrentUser, Depends(require_permission(P.RECRUITMENT_UPDATE))],
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
):
    data = UpdateJobInput(
        title=body.title,
        description=body.description,
        department_id=body.department_id,
        location=body.location,
        employment_type=body.employment_type,
        salary_min=str(body.salary_min) if body.salary_min is not None else None,
        salary_max=str(body.salary_max) if body.salary_max is not None else None,
        currency=body.currency,
        positions=body.positions,
        hiring_manager_id=body.hiring_manager_id,
        closes_at=body.closes_at.isoformat() if body.closes_at else None,
    )
    result = await update_job(uow, user, job_id, data, ctx)
    return success_response(data=result.__dict__, message="Job updated.")


@jobs_router.delete("/{job_id}")
async def delete_job_endpoint(
    job_id: str,
    user: Annotated[CurrentUser, Depends(require_permission(P.RECRUITMENT_MANAGE))],
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
):
    await delete_job(uow, user, job_id, ctx)
    return no_content_response()


@jobs_router.post("/{job_id}/publish")
async def publish_job_endpoint(
    job_id: str,
    user: Annotated[CurrentUser, Depends(require_permission(P.RECRUITMENT_MANAGE))],
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
):
    result = await publish_job(uow, user, job_id, ctx)
    return success_response(data=result.__dict__, message="Job published.")


@jobs_router.post("/{job_id}/close")
async def close_job_endpoint(
    job_id: str,
    user: Annotated[CurrentUser, Depends(require_permission(P.RECRUITMENT_MANAGE))],
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
):
    result = await close_job(uow, user, job_id, ctx)
    return success_response(data=result.__dict__, message="Job closed.")


# ═══════════════════════════════════════════════════════════════════
#  APPLICATIONS
# ═══════════════════════════════════════════════════════════════════

applications_router = APIRouter(prefix="/applications", tags=["Recruitment"])


@applications_router.post("")
async def create_application_endpoint(
    body: CreateApplicationRequest,
    user: Annotated[CurrentUser, Depends(require_permission(P.RECRUITMENT_CREATE))],
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
):
    data = CreateApplicationInput(
        job_id=body.job_id,
        candidate_name=body.candidate_name,
        candidate_email=body.candidate_email,
        candidate_phone=body.candidate_phone,
        resume_document_id=body.resume_document_id,
        notes=body.notes,
    )
    result = await create_application(uow, user, data, ctx)
    return created_response(data=result.__dict__, message="Application created.")


@applications_router.get("")
async def list_applications_endpoint(
    _user: Annotated[CurrentUser, Depends(require_permission(P.RECRUITMENT_READ))],
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    job_id: str | None = Query(None),
    stage: str | None = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
):
    result = await list_applications(
        uow, job_id=job_id, stage=stage, offset=offset, limit=limit
    )
    return success_response(
        data={
            "items": [i.__dict__ for i in result.items],
            "total": result.total,
            "offset": result.offset,
            "limit": result.limit,
        }
    )


@applications_router.get("/{application_id}")
async def get_application_endpoint(
    application_id: str,
    _user: Annotated[CurrentUser, Depends(require_permission(P.RECRUITMENT_READ))],
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
):
    result = await get_application(uow, application_id)
    return success_response(data=result.__dict__)


@applications_router.patch("/{application_id}")
async def update_application_endpoint(
    application_id: str,
    body: UpdateApplicationRequest,
    user: Annotated[CurrentUser, Depends(require_permission(P.RECRUITMENT_UPDATE))],
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
):
    data = UpdateApplicationInput(
        candidate_phone=body.candidate_phone,
        resume_document_id=body.resume_document_id,
        notes=body.notes,
    )
    result = await update_application(uow, user, application_id, data, ctx)
    return success_response(data=result.__dict__, message="Application updated.")


@applications_router.post("/{application_id}/move-stage")
async def move_stage_endpoint(
    application_id: str,
    body: MoveStageRequest,
    user: Annotated[CurrentUser, Depends(require_permission(P.RECRUITMENT_UPDATE))],
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
):
    data = MoveStageInput(stage=body.stage, note=body.note)
    result = await move_application_stage(uow, user, application_id, data, ctx)
    return success_response(data=result.__dict__, message="Application stage updated.")


# ── Interviews (nested under applications) ───────────────────────────

@applications_router.post("/{application_id}/interviews")
async def create_interview_endpoint(
    application_id: str,
    body: CreateInterviewRequest,
    user: Annotated[CurrentUser, Depends(require_permission(P.RECRUITMENT_CREATE))],
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
):
    data = CreateInterviewInput(
        interviewer_id=body.interviewer_id,
        scheduled_at=body.scheduled_at.isoformat(),
        duration_minutes=body.duration_minutes,
        interview_type=body.interview_type,
        location=body.location,
    )
    result = await create_interview(uow, user, application_id, data, ctx)
    return created_response(data=result.__dict__, message="Interview scheduled.")


@applications_router.get("/{application_id}/interviews")
async def list_interviews_endpoint(
    application_id: str,
    user: Annotated[CurrentUser, Depends(require_permission(P.RECRUITMENT_READ))],
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
):
    # INTERVIEWER role sees only assigned interviews (resource policy)
    if Role.INTERVIEWER in user.roles and P.RECRUITMENT_MANAGE not in user.permissions:
        from app.application.recruitment.use_cases import _interview_to_dto

        raw = await uow.interviews.list_by_interviewer(
            user.id, offset=offset, limit=limit
        )
        return success_response(data=[_interview_to_dto(i).__dict__ for i in raw])

    results = await list_interviews(uow, application_id, offset=offset, limit=limit)
    return success_response(data=[i.__dict__ for i in results])


# ═══════════════════════════════════════════════════════════════════
#  INTERVIEWS (top-level for feedback & update)
# ═══════════════════════════════════════════════════════════════════

interviews_router = APIRouter(prefix="/interviews", tags=["Recruitment"])


@interviews_router.post("/{interview_id}/feedback")
async def create_feedback_endpoint(
    interview_id: str,
    body: CreateFeedbackRequest,
    user: Annotated[CurrentUser, Depends(require_permission(P.RECRUITMENT_READ))],
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
):
    data = CreateFeedbackInput(
        rating=body.rating,
        strengths=body.strengths,
        weaknesses=body.weaknesses,
        recommendation=body.recommendation,
        comments=body.comments,
    )
    result = await create_interview_feedback(uow, user, interview_id, data, ctx)
    return created_response(data=result.__dict__, message="Feedback submitted.")


@interviews_router.patch("/{interview_id}")
async def update_interview_endpoint(
    interview_id: str,
    body: UpdateInterviewRequest,
    user: Annotated[CurrentUser, Depends(require_permission(P.RECRUITMENT_UPDATE))],
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
):
    data = UpdateInterviewInput(
        scheduled_at=body.scheduled_at.isoformat() if body.scheduled_at else None,
        duration_minutes=body.duration_minutes,
        interview_type=body.interview_type,
        location=body.location,
        status=body.status,
    )
    result = await update_interview(uow, user, interview_id, data, ctx)
    return success_response(data=result.__dict__, message="Interview updated.")
