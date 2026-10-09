"""Me use case – return current user profile with roles and permissions."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.core.exceptions import AuthError
from app.infrastructure.cache.redis import (
    cache_user_permissions,
    get_cached_permissions,
)
from app.infrastructure.database.uow import SqlAlchemyUnitOfWork


@dataclass(frozen=True, slots=True)
class MeResult:
    id: str
    email: str
    status: str
    roles: list[str] = field(default_factory=list)
    permissions: list[str] = field(default_factory=list)


async def get_me(
    user_id: str,
    uow: SqlAlchemyUnitOfWork,
) -> MeResult:
    """Return user profile, roles, and aggregated permissions."""
    user = await uow.users.get_by_id(user_id)
    if user is None:
        raise AuthError("User not found.")

    role_names = [r.name for r in user.roles]

    # Try cached permissions first
    cached = await get_cached_permissions(user_id)
    if cached is not None:
        perms = sorted(cached)
    else:
        from app.core.permissions import ROLE_PERMISSIONS

        perm_set: set[str] = set()
        for rname in role_names:
            perm_set |= ROLE_PERMISSIONS.get(rname, frozenset())
        perms = sorted(perm_set)
        await cache_user_permissions(user_id, perm_set)

    return MeResult(
        id=user.id,
        email=user.email,
        status=user.status,
        roles=role_names,
        permissions=perms,
    )
