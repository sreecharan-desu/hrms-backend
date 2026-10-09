"""User domain entity – lightweight dataclass used by application layer."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from app.domain.users.enums import UserStatus


@dataclass(frozen=True, slots=True)
class UserEntity:
    """Read-only snapshot of a user aggregate for use-case logic."""

    id: str
    email: str
    status: UserStatus
    roles: list[str] = field(default_factory=list)
    permissions: frozenset[str] = field(default_factory=frozenset)
    created_at: datetime | None = None
    updated_at: datetime | None = None
