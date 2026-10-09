"""Assign roles to user use case."""

from __future__ import annotations

from app.core.exceptions import NotFoundError, ValidationAppError
from app.core.permissions import ALL_ROLES
from app.infrastructure.cache.redis import invalidate_user_permissions
from app.infrastructure.database.uow import SqlAlchemyUnitOfWork


async def assign_roles(
    user_id: str,
    role_names: list[str],
    uow: SqlAlchemyUnitOfWork,
) -> list[str]:
    """Replace the user's roles with the given list. Returns the final role names."""
    user = await uow.users.get_by_id(user_id)
    if user is None:
        raise NotFoundError("User not found.")

    invalid = set(role_names) - ALL_ROLES
    if invalid:
        raise ValidationAppError(f"Invalid roles: {', '.join(sorted(invalid))}")

    roles = []
    for name in role_names:
        role = await uow.roles.get_by_name(name)
        if role is None:
            raise NotFoundError(f"Role '{name}' does not exist in the database. Run the seed first.")
        roles.append(role)

    user.roles = roles
    await uow.commit()
    await invalidate_user_permissions(user_id)
    return [r.name for r in user.roles]
