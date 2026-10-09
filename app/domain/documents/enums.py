"""Document domain enums – pure Python, no ORM dependency."""

from __future__ import annotations

from enum import StrEnum


class DocumentStatus(StrEnum):
    PENDING = "PENDING"
    AVAILABLE = "AVAILABLE"
    DELETED = "DELETED"
