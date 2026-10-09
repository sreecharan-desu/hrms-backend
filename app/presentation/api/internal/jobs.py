"""Internal job drain endpoint – called by Vercel cron or manually."""

from __future__ import annotations

from fastapi import APIRouter, Header, Request

from app.core.config import get_settings
from app.core.exceptions import AuthError
from app.core.responses import success_response

router = APIRouter(prefix="/internal", tags=["internal"], include_in_schema=False)


def _verify_cron_secret(
    authorization: str | None = None,
    x_cron_secret: str | None = None,
) -> None:
    """Accept CRON_SECRET via ``Authorization: Bearer <token>`` or ``X-Cron-Secret`` header."""
    settings = get_settings()
    if not settings.CRON_SECRET:
        raise AuthError("CRON_SECRET not configured.")

    token = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:]
    if token is None:
        token = x_cron_secret

    if token != settings.CRON_SECRET:
        raise AuthError("Invalid cron secret.")


@router.post("/jobs/drain")
async def drain_jobs_endpoint(
    request: Request,
    authorization: str | None = Header(None),
    x_cron_secret: str | None = Header(None, alias="X-Cron-Secret"),
):
    _verify_cron_secret(authorization, x_cron_secret)

    from app.infrastructure.jobs.drain import drain_jobs

    processed = await drain_jobs()
    return success_response(data={"processed": processed}, message="Drain complete.")
