"""Internal admin endpoints – cache management."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.dependencies import CurrentUser, require_internal_token, require_permission
from app.core.permissions import P
from app.core.responses import success_response
from app.infrastructure.cache.redis import get_redis

router = APIRouter(prefix="/internal", tags=["internal"], include_in_schema=False)


@router.post("/admin/cache/clear")
async def clear_permission_cache(
    _guard: Annotated[None, Depends(require_internal_token)],
    _admin: Annotated[CurrentUser, Depends(require_permission(P.ADMIN_MANAGE))],
):
    """Clear all cached user permissions from Redis."""
    r = await get_redis()
    cleared = 0
    if r is not None:
        cursor = "0"
        while cursor:
            cursor, keys = await r.scan(
                cursor=cursor, match="user:*:permissions", count=200
            )
            if keys:
                await r.delete(*keys)
                cleared += len(keys)
            if cursor == 0 or cursor == "0":
                break

    return success_response(data={"cleared": cleared}, message="Permission cache cleared.")
