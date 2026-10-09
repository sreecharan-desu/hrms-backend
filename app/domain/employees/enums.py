"""Employee domain enums – pure Python, no ORM dependency."""

from __future__ import annotations

from enum import StrEnum


class EmploymentStatus(StrEnum):
    ACTIVE = "ACTIVE"
    PROBATION = "PROBATION"
    NOTICE_PERIOD = "NOTICE_PERIOD"
    RESIGNED = "RESIGNED"
    TERMINATED = "TERMINATED"
    RETIRED = "RETIRED"
