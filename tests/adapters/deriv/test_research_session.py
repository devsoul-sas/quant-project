"""Bounded Deriv research-session lifecycle tests."""

from decimal import Decimal

import pytest

from devsoul_quant.adapters.deriv.research_session import (
    EphemeralResearchSession,
    ExpiredResearchSession,
)
from devsoul_quant.domain.replay import Tick


class Clock:
    def __init__(self, epoch: int) -> None:
        self.epoch = epoch

    def __call__(self) -> int:
        return self.epoch


def test_research_session_keeps_only_in_memory_state_and_zeroizes_on_exit() -> None:
    clock = Clock(1_000)
    session = EphemeralResearchSession(clock=clock, ttl_seconds=10)

    with session:
        session.add_tick(Tick(epoch=999, quote=Decimal("100")))
        session.record_result("paper-result")
        assert session.ticks == (Tick(epoch=999, quote=Decimal("100")),)
        assert session.results == ("paper-result",)

    assert session.ticks == ()
    assert session.results == ()
    assert session.closed is True


def test_research_session_expires_and_zeroizes_at_ttl_boundary() -> None:
    clock = Clock(1_000)
    session = EphemeralResearchSession(clock=clock, ttl_seconds=10)
    session.add_tick(Tick(epoch=999, quote=Decimal("100")))
    session.record_result("paper-result")

    clock.epoch = 1_010

    with pytest.raises(ExpiredResearchSession, match="expired"):
        session.add_tick(Tick(epoch=1_010, quote=Decimal("101")))

    assert session.ticks == ()
    assert session.results == ()
    assert session.closed is True


def test_research_session_rejects_invalid_clock_and_mutation_after_close() -> None:
    with pytest.raises(TypeError, match="integer epoch"):
        EphemeralResearchSession(clock=lambda: True, ttl_seconds=10)

    session = EphemeralResearchSession[str](clock=lambda: 1_000, ttl_seconds=10)
    session.close()
    with pytest.raises(ExpiredResearchSession, match="closed"):
        session.record_result("late")
