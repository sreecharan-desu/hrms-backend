"""Exhaustive unit tests for ApplicationStage.can_transition – all legal and illegal transitions."""

import pytest

from app.domain.recruitment.enums import ApplicationStage

_ALL_STAGES = list(ApplicationStage)

_STAGE_ORDER = [
    ApplicationStage.APPLIED,
    ApplicationStage.SCREENING,
    ApplicationStage.INTERVIEW,
    ApplicationStage.TECHNICAL,
    ApplicationStage.HR,
    ApplicationStage.OFFER,
    ApplicationStage.HIRED,
]

_TERMINAL_STAGES = {ApplicationStage.REJECTED, ApplicationStage.HIRED}

# Build the complete set of legal transitions
_LEGAL: set[tuple[ApplicationStage, ApplicationStage]] = set()
# Forward steps along the pipeline
for i in range(len(_STAGE_ORDER) - 1):
    _LEGAL.add((_STAGE_ORDER[i], _STAGE_ORDER[i + 1]))
# Any non-terminal → REJECTED
for stage in _ALL_STAGES:
    if stage not in _TERMINAL_STAGES:
        _LEGAL.add((stage, ApplicationStage.REJECTED))


class TestLegalTransitions:
    """Verify every transition in the state machine is accepted."""

    @pytest.mark.parametrize(
        "from_s, to_s",
        [
            # Forward pipeline transitions
            (ApplicationStage.APPLIED, ApplicationStage.SCREENING),
            (ApplicationStage.SCREENING, ApplicationStage.INTERVIEW),
            (ApplicationStage.INTERVIEW, ApplicationStage.TECHNICAL),
            (ApplicationStage.TECHNICAL, ApplicationStage.HR),
            (ApplicationStage.HR, ApplicationStage.OFFER),
            (ApplicationStage.OFFER, ApplicationStage.HIRED),
            # Any non-terminal → REJECTED
            (ApplicationStage.APPLIED, ApplicationStage.REJECTED),
            (ApplicationStage.SCREENING, ApplicationStage.REJECTED),
            (ApplicationStage.INTERVIEW, ApplicationStage.REJECTED),
            (ApplicationStage.TECHNICAL, ApplicationStage.REJECTED),
            (ApplicationStage.HR, ApplicationStage.REJECTED),
            (ApplicationStage.OFFER, ApplicationStage.REJECTED),
        ],
    )
    def test_allowed(self, from_s: ApplicationStage, to_s: ApplicationStage) -> None:
        assert ApplicationStage.can_transition(from_s, to_s) is True


class TestIllegalTransitions:
    """Verify specific non-allowed transitions are rejected."""

    @pytest.mark.parametrize(
        "from_s, to_s",
        [
            # Self-loops (no stage can transition to itself)
            (ApplicationStage.APPLIED, ApplicationStage.APPLIED),
            (ApplicationStage.SCREENING, ApplicationStage.SCREENING),
            (ApplicationStage.INTERVIEW, ApplicationStage.INTERVIEW),
            (ApplicationStage.TECHNICAL, ApplicationStage.TECHNICAL),
            (ApplicationStage.HR, ApplicationStage.HR),
            (ApplicationStage.OFFER, ApplicationStage.OFFER),
            (ApplicationStage.HIRED, ApplicationStage.HIRED),
            (ApplicationStage.REJECTED, ApplicationStage.REJECTED),
            # Backward jumps
            (ApplicationStage.SCREENING, ApplicationStage.APPLIED),
            (ApplicationStage.INTERVIEW, ApplicationStage.APPLIED),
            (ApplicationStage.INTERVIEW, ApplicationStage.SCREENING),
            (ApplicationStage.TECHNICAL, ApplicationStage.INTERVIEW),
            (ApplicationStage.HR, ApplicationStage.TECHNICAL),
            (ApplicationStage.OFFER, ApplicationStage.HR),
            (ApplicationStage.HIRED, ApplicationStage.OFFER),
            # Skip-forward (only +1 step allowed)
            (ApplicationStage.APPLIED, ApplicationStage.INTERVIEW),
            (ApplicationStage.APPLIED, ApplicationStage.TECHNICAL),
            (ApplicationStage.APPLIED, ApplicationStage.HR),
            (ApplicationStage.APPLIED, ApplicationStage.OFFER),
            (ApplicationStage.APPLIED, ApplicationStage.HIRED),
            (ApplicationStage.SCREENING, ApplicationStage.TECHNICAL),
            (ApplicationStage.SCREENING, ApplicationStage.HR),
            (ApplicationStage.SCREENING, ApplicationStage.OFFER),
            (ApplicationStage.SCREENING, ApplicationStage.HIRED),
            (ApplicationStage.INTERVIEW, ApplicationStage.HR),
            (ApplicationStage.INTERVIEW, ApplicationStage.OFFER),
            (ApplicationStage.INTERVIEW, ApplicationStage.HIRED),
            (ApplicationStage.TECHNICAL, ApplicationStage.OFFER),
            (ApplicationStage.TECHNICAL, ApplicationStage.HIRED),
            (ApplicationStage.HR, ApplicationStage.HIRED),
            # HIRED is terminal – no outgoing transitions
            (ApplicationStage.HIRED, ApplicationStage.APPLIED),
            (ApplicationStage.HIRED, ApplicationStage.SCREENING),
            (ApplicationStage.HIRED, ApplicationStage.INTERVIEW),
            (ApplicationStage.HIRED, ApplicationStage.TECHNICAL),
            (ApplicationStage.HIRED, ApplicationStage.HR),
            (ApplicationStage.HIRED, ApplicationStage.REJECTED),
            # REJECTED is terminal – no outgoing transitions
            (ApplicationStage.REJECTED, ApplicationStage.APPLIED),
            (ApplicationStage.REJECTED, ApplicationStage.SCREENING),
            (ApplicationStage.REJECTED, ApplicationStage.INTERVIEW),
            (ApplicationStage.REJECTED, ApplicationStage.TECHNICAL),
            (ApplicationStage.REJECTED, ApplicationStage.HR),
            (ApplicationStage.REJECTED, ApplicationStage.OFFER),
            (ApplicationStage.REJECTED, ApplicationStage.HIRED),
        ],
    )
    def test_blocked(self, from_s: ApplicationStage, to_s: ApplicationStage) -> None:
        assert ApplicationStage.can_transition(from_s, to_s) is False


class TestTerminalStagesHaveNoOutgoing:
    """Terminal stages must reject every outgoing transition."""

    @pytest.mark.parametrize("terminal", [
        ApplicationStage.REJECTED,
        ApplicationStage.HIRED,
    ])
    def test_no_exit(self, terminal: ApplicationStage) -> None:
        for target in _ALL_STAGES:
            assert ApplicationStage.can_transition(terminal, target) is False, (
                f"Terminal stage {terminal} should block transition to {target}"
            )


class TestNonTerminalCanReject:
    """Every non-terminal stage must be able to transition to REJECTED."""

    @pytest.mark.parametrize("stage", [
        s for s in _ALL_STAGES if s not in _TERMINAL_STAGES
    ])
    def test_can_reject(self, stage: ApplicationStage) -> None:
        assert ApplicationStage.can_transition(stage, ApplicationStage.REJECTED) is True


class TestForwardOnlyOneStep:
    """Only forward +1 pipeline steps are allowed (no skipping)."""

    @pytest.mark.parametrize(
        "from_s, to_s",
        [
            (_STAGE_ORDER[i], _STAGE_ORDER[j])
            for i in range(len(_STAGE_ORDER))
            for j in range(len(_STAGE_ORDER))
            if j != i + 1 and _STAGE_ORDER[j] != ApplicationStage.REJECTED
        ],
    )
    def test_no_skip(self, from_s: ApplicationStage, to_s: ApplicationStage) -> None:
        assert ApplicationStage.can_transition(from_s, to_s) is False, (
            f"can_transition({from_s}, {to_s}) should be False (not +1 step)"
        )


class TestExhaustive:
    """Every (from, to) pair is either explicitly legal or explicitly illegal."""

    def test_full_matrix(self) -> None:
        for from_s in _ALL_STAGES:
            for to_s in _ALL_STAGES:
                expected = (from_s, to_s) in _LEGAL
                actual = ApplicationStage.can_transition(from_s, to_s)
                assert actual is expected, (
                    f"can_transition({from_s}, {to_s}) "
                    f"returned {actual}, expected {expected}"
                )

    def test_legal_count(self) -> None:
        """Verify the exact number of legal transitions matches expectations.

        6 forward pipeline steps + 6 non-terminal→REJECTED = 12 total.
        """
        count = sum(
            1
            for from_s in _ALL_STAGES
            for to_s in _ALL_STAGES
            if ApplicationStage.can_transition(from_s, to_s)
        )
        assert count == 12
