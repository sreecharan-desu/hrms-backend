"""User domain enums – pure Python, no ORM dependency."""

from __future__ import annotations

from enum import StrEnum


class UserStatus(StrEnum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    LOCKED = "LOCKED"
    PENDING = "PENDING"
