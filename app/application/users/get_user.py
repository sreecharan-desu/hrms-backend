"""Get single user use case."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.core.exceptions import NotFoundError
from app.infrastructure.database.uow import SqlAlchemyUnitOfWork


@dataclass(frozen=True, slots=True)
class UserDetail:
    id: str
    email: str
    status: str
    roles: list[str] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""


async def get_user(
    user_id: str,
    uow: SqlAlchemyUnitOfWork,
) -> UserDetail:
    user = await uow.users.get_by_id(user_id)
    if user is None:
        raise NotFoundError("User not found.")
    return UserDetail(
        id=user.id,
        email=user.email,
        status=user.status,
        roles=[r.name for r in user.roles],
        created_at=user.created_at.isoformat() if user.created_at else "",
        updated_at=user.updated_at.isoformat() if user.updated_at else "",
    )
