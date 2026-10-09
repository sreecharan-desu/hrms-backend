"""Unit tests for LeaveRequestStatus.can_transition – all legal and illegal transitions."""

import pytest

from app.domain.leave.enums import LeaveRequestStatus

_ALL_STATUSES = list(LeaveRequestStatus)


class TestLegalTransitions:
    """Verify every transition in the state machine is accepted."""

    @pytest.mark.parametrize(
        "from_s, to_s",
        [
            (LeaveRequestStatus.PENDING, LeaveRequestStatus.APPROVED),
            (LeaveRequestStatus.PENDING, LeaveRequestStatus.REJECTED),
            (LeaveRequestStatus.PENDING, LeaveRequestStatus.CANCELLED),
            (LeaveRequestStatus.APPROVED, LeaveRequestStatus.COMPLETED),
            (LeaveRequestStatus.APPROVED, LeaveRequestStatus.CANCELLED),
        ],
    )
    def test_allowed(self, from_s: LeaveRequestStatus, to_s: LeaveRequestStatus) -> None:
        assert LeaveRequestStatus.can_transition(from_s, to_s) is True


class TestIllegalTransitions:
    """Verify every non-allowed transition is rejected."""

    @pytest.mark.parametrize(
        "from_s, to_s",
        [
            # PENDING cannot go to COMPLETED directly
            (LeaveRequestStatus.PENDING, LeaveRequestStatus.COMPLETED),
            # PENDING self-loop
            (LeaveRequestStatus.PENDING, LeaveRequestStatus.PENDING),
            # APPROVED cannot go back to PENDING or REJECTED
            (LeaveRequestStatus.APPROVED, LeaveRequestStatus.PENDING),
            (LeaveRequestStatus.APPROVED, LeaveRequestStatus.REJECTED),
            (LeaveRequestStatus.APPROVED, LeaveRequestStatus.APPROVED),
            # REJECTED is terminal
            (LeaveRequestStatus.REJECTED, LeaveRequestStatus.PENDING),
            (LeaveRequestStatus.REJECTED, LeaveRequestStatus.APPROVED),
            (LeaveRequestStatus.REJECTED, LeaveRequestStatus.CANCELLED),
            (LeaveRequestStatus.REJECTED, LeaveRequestStatus.COMPLETED),
            (LeaveRequestStatus.REJECTED, LeaveRequestStatus.REJECTED),
            # CANCELLED is terminal
            (LeaveRequestStatus.CANCELLED, LeaveRequestStatus.PENDING),
            (LeaveRequestStatus.CANCELLED, LeaveRequestStatus.APPROVED),
            (LeaveRequestStatus.CANCELLED, LeaveRequestStatus.REJECTED),
            (LeaveRequestStatus.CANCELLED, LeaveRequestStatus.COMPLETED),
            (LeaveRequestStatus.CANCELLED, LeaveRequestStatus.CANCELLED),
            # COMPLETED is terminal – cannot cancel
            (LeaveRequestStatus.COMPLETED, LeaveRequestStatus.PENDING),
            (LeaveRequestStatus.COMPLETED, LeaveRequestStatus.APPROVED),
            (LeaveRequestStatus.COMPLETED, LeaveRequestStatus.REJECTED),
            (LeaveRequestStatus.COMPLETED, LeaveRequestStatus.CANCELLED),
            (LeaveRequestStatus.COMPLETED, LeaveRequestStatus.COMPLETED),
        ],
    )
    def test_blocked(self, from_s: LeaveRequestStatus, to_s: LeaveRequestStatus) -> None:
        assert LeaveRequestStatus.can_transition(from_s, to_s) is False


class TestTerminalStatesHaveNoOutgoing:
    """Terminal states must reject every outgoing transition."""

    @pytest.mark.parametrize("terminal", [
        LeaveRequestStatus.REJECTED,
        LeaveRequestStatus.CANCELLED,
        LeaveRequestStatus.COMPLETED,
    ])
    def test_no_exit(self, terminal: LeaveRequestStatus) -> None:
        for target in _ALL_STATUSES:
            assert LeaveRequestStatus.can_transition(terminal, target) is False


class TestExhaustive:
    """Every (from, to) pair is either explicitly legal or explicitly illegal."""

    LEGAL = {
        (LeaveRequestStatus.PENDING, LeaveRequestStatus.APPROVED),
        (LeaveRequestStatus.PENDING, LeaveRequestStatus.REJECTED),
        (LeaveRequestStatus.PENDING, LeaveRequestStatus.CANCELLED),
        (LeaveRequestStatus.APPROVED, LeaveRequestStatus.COMPLETED),
        (LeaveRequestStatus.APPROVED, LeaveRequestStatus.CANCELLED),
    }

    def test_full_matrix(self) -> None:
        for from_s in _ALL_STATUSES:
            for to_s in _ALL_STATUSES:
                expected = (from_s, to_s) in self.LEGAL
                actual = LeaveRequestStatus.can_transition(from_s, to_s)
                assert actual is expected, (
                    f"can_transition({from_s}, {to_s}) "
                    f"returned {actual}, expected {expected}"
                )
