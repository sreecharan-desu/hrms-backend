"""Leave domain enums – pure Python, no ORM dependency."""

from __future__ import annotations

from enum import StrEnum

_LEAVE_TRANSITIONS: dict[str, frozenset[str]] = {
    "PENDING": frozenset({"APPROVED", "REJECTED", "CANCELLED"}),
    "APPROVED": frozenset({"COMPLETED", "CANCELLED"}),
    "REJECTED": frozenset(),
    "CANCELLED": frozenset(),
    "COMPLETED": frozenset(),
}


class LeaveRequestStatus(StrEnum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"
    COMPLETED = "COMPLETED"

    @staticmethod
    def can_transition(from_status: LeaveRequestStatus, to_status: LeaveRequestStatus) -> bool:
        """Return True if *from_status* → *to_status* is a valid transition."""
        allowed = _LEAVE_TRANSITIONS.get(from_status.value, frozenset())
        return to_status.value in allowed
