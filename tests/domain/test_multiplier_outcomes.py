"""Tests for non-economic directional Multiplier outcomes."""

from decimal import Decimal

import pytest

from devsoul_quant.domain.decision import DecisionAction
from devsoul_quant.domain.multiplier_outcomes import (
    DirectionalBarrierPolicy,
    DirectionalOutcome,
    InvalidDirectionalOutcome,
    settle_directional_outcome,
)
from devsoul_quant.domain.replay import Tick


def _tick(epoch: int, quote: str) -> Tick:
    return Tick(epoch=epoch, quote=Decimal(quote), pip_size=4)


def test_multup_settles_target_at_first_directional_barrier() -> None:
    result = settle_directional_outcome(
        action=DecisionAction.MULTUP,
        entry_tick=_tick(10, "100"),
        future_ticks=(
            _tick(11, "100.4"),
            _tick(12, "101.1"),
            _tick(13, "99"),
        ),
        policy=DirectionalBarrierPolicy(
            target_return=Decimal("0.01"),
            stop_return=Decimal("0.005"),
            maximum_holding_ticks=3,
        ),
    )

    assert result.outcome is DirectionalOutcome.TARGET
    assert result.holding_ticks == 2
    assert result.terminal_tick == _tick(12, "101.1")
    assert result.directional_return == Decimal("0.011")


def test_multdown_settles_stop_at_first_directional_barrier() -> None:
    result = settle_directional_outcome(
        action=DecisionAction.MULTDOWN,
        entry_tick=_tick(20, "100"),
        future_ticks=(
            _tick(21, "100.2"),
            _tick(22, "100.6"),
            _tick(23, "98"),
        ),
        policy=DirectionalBarrierPolicy(
            target_return=Decimal("0.01"),
            stop_return=Decimal("0.005"),
            maximum_holding_ticks=3,
        ),
    )

    assert result.outcome is DirectionalOutcome.STOP
    assert result.holding_ticks == 2
    assert result.directional_return == Decimal("-0.006")


def test_directional_settlement_times_out_at_frozen_horizon() -> None:
    result = settle_directional_outcome(
        action=DecisionAction.MULTUP,
        entry_tick=_tick(30, "100"),
        future_ticks=(_tick(31, "100.2"), _tick(32, "99.8")),
        policy=DirectionalBarrierPolicy(
            target_return=Decimal("0.01"),
            stop_return=Decimal("0.01"),
            maximum_holding_ticks=2,
        ),
    )

    assert result.outcome is DirectionalOutcome.TIMEOUT
    assert result.holding_ticks == 2
    assert result.terminal_tick == _tick(32, "99.8")
    assert result.directional_return == Decimal("-0.002")


def test_directional_settlement_rejects_truncated_horizon() -> None:
    with pytest.raises(InvalidDirectionalOutcome, match="cover"):
        settle_directional_outcome(
            action=DecisionAction.MULTUP,
            entry_tick=_tick(40, "100"),
            future_ticks=(_tick(41, "101"),),
            policy=DirectionalBarrierPolicy(
                target_return=Decimal("0.02"),
                stop_return=Decimal("0.01"),
                maximum_holding_ticks=2,
            ),
        )


def test_directional_settlement_rejects_retroactive_future_tick() -> None:
    with pytest.raises(InvalidDirectionalOutcome, match="strictly increasing"):
        settle_directional_outcome(
            action=DecisionAction.MULTDOWN,
            entry_tick=_tick(50, "100"),
            future_ticks=(_tick(50, "99"),),
            policy=DirectionalBarrierPolicy(
                target_return=Decimal("0.01"),
                stop_return=Decimal("0.01"),
                maximum_holding_ticks=1,
            ),
        )
