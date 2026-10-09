"""List users use case."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.infrastructure.database.uow import SqlAlchemyUnitOfWork


@dataclass(frozen=True, slots=True)
class UserDTO:
    id: str
    email: str
    status: str
    roles: list[str] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""


@dataclass(frozen=True, slots=True)
class ListUsersResult:
    items: list[UserDTO]
    total: int
    offset: int
    limit: int


async def list_users(
    uow: SqlAlchemyUnitOfWork,
    *,
    offset: int = 0,
    limit: int = 50,
) -> ListUsersResult:
    users = await uow.users.list_all(offset=offset, limit=limit)
    total = await uow.users.count()
    items = [
        UserDTO(
            id=u.id,
            email=u.email,
            status=u.status,
            roles=[r.name for r in u.roles],
            created_at=u.created_at.isoformat() if u.created_at else "",
            updated_at=u.updated_at.isoformat() if u.updated_at else "",
        )
        for u in users
    ]
    return ListUsersResult(items=items, total=total, offset=offset, limit=limit)
