"""HRMF application factory and ASGI entry-point."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.exceptions import AppError
from app.core.logging import setup_logging
from app.core.middleware import RequestIDMiddleware, TimingMiddleware
from app.core.responses import ORJSONResponse, error_response


def create_app() -> FastAPI:
    settings = get_settings()

    setup_logging(
        json=settings.is_production,
        level="INFO" if settings.is_production else "DEBUG",
    )

    show_docs = settings.docs_enabled

    application = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        docs_url="/docs" if show_docs else None,
        redoc_url="/redoc" if show_docs else None,
        openapi_url="/openapi.json" if show_docs else None,
        default_response_class=ORJSONResponse,
    )

    # ── Middleware (order matters – outermost first) ──────────────
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.add_middleware(TimingMiddleware)
    application.add_middleware(RequestIDMiddleware)

    # ── Exception handlers ───────────────────────────────────────
    @application.exception_handler(AppError)
    async def _app_error_handler(request: Request, exc: AppError) -> ORJSONResponse:
        return error_response(
            code=exc.code,
            message=exc.message,
            status_code=exc.status_code,
        )

    @application.exception_handler(RequestValidationError)
    async def _validation_error_handler(
        request: Request,
        exc: RequestValidationError,
    ) -> ORJSONResponse:
        if settings.is_production:
            return error_response(
                code="VALIDATION_ERROR",
                message="Request validation failed.",
                status_code=422,
            )
        details = []
        for err in exc.errors():
            loc = err.get("loc", ())
            field = ".".join(str(p) for p in loc[1:]) if len(loc) > 1 else str(loc[0]) if loc else "unknown"
            details.append({"field": field, "message": err.get("msg", "")})
        return ORJSONResponse(
            content={
                "success": False,
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Request validation failed.",
                    "details": details,
                },
            },
            status_code=422,
        )

    @application.exception_handler(Exception)
    async def _unhandled_error_handler(request: Request, exc: Exception) -> ORJSONResponse:
        import structlog

        logger = structlog.stdlib.get_logger("unhandled")
        await logger.aerror("unhandled_exception", exc_info=exc)
        message = "Internal server error." if settings.is_production else str(exc)
        return error_response(
            code="INTERNAL_ERROR",
            message=message,
            status_code=500,
        )

    # ── Routers ──────────────────────────────────────────────────
    from app.presentation.api.internal.admin import router as admin_router
    from app.presentation.api.internal.health import router as health_router
    from app.presentation.api.internal.jobs import router as jobs_router
    from app.presentation.api.internal.ready import router as ready_router
    from app.presentation.api.v1.attendance import router as attendance_router
    from app.presentation.api.v1.audit import router as audit_router
    from app.presentation.api.v1.auth import router as auth_router
    from app.presentation.api.v1.departments import router as departments_router
    from app.presentation.api.v1.documents import router as documents_router
    from app.presentation.api.v1.employees import router as employees_router
    from app.presentation.api.v1.leave import leave_types_router
    from app.presentation.api.v1.leave import router as leave_router
    from app.presentation.api.v1.notifications import router as notifications_router
    from app.presentation.api.v1.performance import router as performance_router
    from app.presentation.api.v1.recruitment import (
        applications_router as recruitment_applications_router,
    )
    from app.presentation.api.v1.recruitment import (
        interviews_router as recruitment_interviews_router,
    )
    from app.presentation.api.v1.recruitment import (
        jobs_router as recruitment_jobs_router,
    )
    from app.presentation.api.v1.reports import router as reports_router
    from app.presentation.api.v1.users import router as users_router

    application.include_router(health_router)
    application.include_router(jobs_router)
    application.include_router(ready_router)
    application.include_router(admin_router)
    application.include_router(auth_router, prefix="/api/v1")
    application.include_router(users_router, prefix="/api/v1")
    application.include_router(employees_router, prefix="/api/v1")
    application.include_router(departments_router, prefix="/api/v1")
    application.include_router(attendance_router, prefix="/api/v1")
    application.include_router(leave_router, prefix="/api/v1")
    application.include_router(leave_types_router, prefix="/api/v1")
    application.include_router(documents_router, prefix="/api/v1")
    application.include_router(notifications_router, prefix="/api/v1")
    application.include_router(audit_router, prefix="/api/v1")
    application.include_router(recruitment_jobs_router, prefix="/api/v1")
    application.include_router(recruitment_applications_router, prefix="/api/v1")
    application.include_router(recruitment_interviews_router, prefix="/api/v1")
    application.include_router(performance_router, prefix="/api/v1")
    application.include_router(reports_router, prefix="/api/v1")

    # ── Shutdown hook for Redis cleanup ──────────────────────────
    @application.on_event("shutdown")
    async def _shutdown() -> None:
        from app.infrastructure.cache.redis import close_redis

        await close_redis()

    return application


app = create_app()
