"""Recruitment domain enums – pure Python, no ORM dependency."""

from __future__ import annotations

from enum import StrEnum

_STAGE_ORDER: list[str] = [
    "APPLIED",
    "SCREENING",
    "INTERVIEW",
    "TECHNICAL",
    "HR",
    "OFFER",
    "HIRED",
]

_TERMINAL_STAGES: frozenset[str] = frozenset({"REJECTED", "HIRED"})


class JobStatus(StrEnum):
    DRAFT = "DRAFT"
    OPEN = "OPEN"
    ON_HOLD = "ON_HOLD"
    CLOSED = "CLOSED"
    CANCELLED = "CANCELLED"


class ApplicationStage(StrEnum):
    APPLIED = "APPLIED"
    SCREENING = "SCREENING"
    INTERVIEW = "INTERVIEW"
    TECHNICAL = "TECHNICAL"
    HR = "HR"
    OFFER = "OFFER"
    HIRED = "HIRED"
    REJECTED = "REJECTED"

    @staticmethod
    def can_transition(from_stage: ApplicationStage, to_stage: ApplicationStage) -> bool:
        """Return True if *from_stage* → *to_stage* is a valid transition.

        Rules:
        - Forward movement along APPLIED→…→HIRED is allowed.
        - REJECTED is reachable from any non-terminal stage.
        - No exit from REJECTED or HIRED.
        """
        if from_stage.value in _TERMINAL_STAGES:
            return False

        if to_stage == ApplicationStage.REJECTED:
            return True

        if from_stage.value in _STAGE_ORDER and to_stage.value in _STAGE_ORDER:
            return _STAGE_ORDER.index(to_stage.value) == _STAGE_ORDER.index(from_stage.value) + 1

        return False
