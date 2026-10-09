"""Internal readiness probe – checks Postgres and Redis."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import text

from app.core.dependencies import require_internal_token
from app.infrastructure.cache.redis import get_redis
from app.infrastructure.database.session import async_session_factory

router = APIRouter(prefix="/internal", tags=["internal"], include_in_schema=False)


@router.get("/ready")
async def readiness_check(
    _guard: Annotated[None, Depends(require_internal_token)],
):
    checks: dict[str, str] = {}

    # Postgres
    try:
        async with async_session_factory() as session:
            await session.execute(text("SELECT 1"))
        checks["postgres"] = "ok"
    except Exception as exc:
        checks["postgres"] = f"error: {exc}"

    # Redis
    try:
        r = await get_redis()
        if r is not None:
            await r.ping()
            checks["redis"] = "ok"
        else:
            checks["redis"] = "unavailable"
    except Exception as exc:
        checks["redis"] = f"error: {exc}"

    all_ok = all(v == "ok" for v in checks.values())
    status_code = 200 if all_ok else 503

    from app.core.responses import ORJSONResponse

    return ORJSONResponse(
        content={
            "success": all_ok,
            "data": {"checks": checks},
            "message": "ready" if all_ok else "degraded",
        },
        status_code=status_code,
    )
