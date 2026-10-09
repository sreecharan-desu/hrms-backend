"""Performance domain enums – pure Python, no ORM dependency."""

from __future__ import annotations

from enum import StrEnum


class ReviewStatus(StrEnum):
    DRAFT = "DRAFT"
    SELF_REVIEW = "SELF_REVIEW"
    MANAGER_REVIEW = "MANAGER_REVIEW"
    CALIBRATION = "CALIBRATION"
    COMPLETED = "COMPLETED"
