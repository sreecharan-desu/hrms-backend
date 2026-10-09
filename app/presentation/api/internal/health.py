"""Internal health-check router (excluded from public OpenAPI docs)."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/internal", tags=["internal"], include_in_schema=False)


@router.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}
