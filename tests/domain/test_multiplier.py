"""Causal Multiplier regime and estimated paper-P&L tests."""

from dataclasses import replace
from decimal import Decimal

import pytest

from devsoul_quant.domain.contracts import ContractType, NoTradeIntent
from devsoul_quant.domain.multiplier import (
    InvalidMultiplierPolicy,
    MultiplierIntent,
    MultiplierPolicy,
    decide_multiplier,
    replay_multiplier_estimate,
)
from devsoul_quant.domain.replay import EconomyProvenance, Tick


def _ticks(quotes: list[str]) -> tuple[Tick, ...]:
    return tuple(Tick(epoch=index, quote=Decimal(quote)) for index, quote in enumerate(quotes))


def _policy() -> MultiplierPolicy:
    return MultiplierPolicy(
        lookback_ticks=5,
        minimum_absolute_return=Decimal("0.01"),
        minimum_directional_consistency=Decimal("0.75"),
        multiplier=Decimal("10"),
        stake=Decimal("1"),
        stop_loss=Decimal("0.50"),
        take_profit=Decimal("1.00"),
        maximum_holding_ticks=5,
    )


def test_multiplier_decision_defaults_to_no_trade_without_stable_regime() -> None:
    decision = decide_multiplier(
        history=_ticks(["100", "101", "100", "101", "100"]),
        symbol="DRIFT_CANDIDATE",
        policy=_policy(),
    )

    assert isinstance(decision, NoTradeIntent)


def test_multiplier_decision_enters_up_only_for_stable_positive_regime() -> None:
    decision = decide_multiplier(
        history=_ticks(["100", "101", "102", "103", "104"]),
        symbol="DRIFT_CANDIDATE",
        policy=_policy(),
    )

    assert isinstance(decision, MultiplierIntent)
    assert decision.contract_type is ContractType.MULTUP
    assert decision.multiplier == Decimal("10")


def test_multiplier_paper_replay_is_estimated_and_applies_observed_commission() -> None:
    decision = decide_multiplier(
        history=_ticks(["100", "101", "102", "103", "104"]),
        symbol="DRIFT_CANDIDATE",
        policy=_policy(),
    )
    assert isinstance(decision, MultiplierIntent)

    result = replay_multiplier_estimate(
        decision,
        entry_tick=Tick(epoch=4, quote=Decimal("104")),
        exit_tick=Tick(epoch=5, quote=Decimal("105")),
        observed_commission=Decimal("0.01"),
    )

    assert result.economy is EconomyProvenance.ESTIMATED
    assert result.profit == Decimal("0.08615384615384615384615384615")


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("lookback_ticks", 1),
        ("maximum_holding_ticks", 0),
        ("multiplier", Decimal("0")),
        ("minimum_directional_consistency", Decimal("0.5")),
        ("stop_loss", Decimal("2")),
    ],
)
def test_multiplier_policy_rejects_unsafe_parameters(field: str, value: object) -> None:
    with pytest.raises(InvalidMultiplierPolicy):
        replace(_policy(), **{field: value})


def test_multiplier_intent_rejects_non_multiplier_direction() -> None:
    with pytest.raises(InvalidMultiplierPolicy, match="MULTUP or MULTDOWN"):
        MultiplierIntent(
            symbol="R_10",
            contract_type=ContractType.CALL,
            stake=Decimal("1"),
            multiplier=Decimal("10"),
            stop_loss=Decimal("0.5"),
            take_profit=Decimal("1"),
            maximum_holding_ticks=5,
            strategy_reason="invalid",
        )


def test_multiplier_decision_rejects_invalid_history_and_weak_consistency() -> None:
    insufficient = decide_multiplier(history=_ticks(["100"]), symbol="R_10", policy=_policy())
    assert isinstance(insufficient, NoTradeIntent)

    with pytest.raises(InvalidMultiplierPolicy, match="increasing"):
        decide_multiplier(
            history=(
                Tick(epoch=1, quote=Decimal("100")),
                Tick(epoch=2, quote=Decimal("101")),
                Tick(epoch=2, quote=Decimal("102")),
                Tick(epoch=3, quote=Decimal("103")),
                Tick(epoch=4, quote=Decimal("104")),
            ),
            symbol="R_10",
            policy=_policy(),
        )
    with pytest.raises(InvalidMultiplierPolicy, match="zero"):
        decide_multiplier(
            history=_ticks(["0", "1", "2", "3", "4"]),
            symbol="R_10",
            policy=_policy(),
        )

    weak = decide_multiplier(
        history=_ticks(["100", "104", "103", "102", "104"]),
        symbol="R_10",
        policy=_policy(),
    )
    assert isinstance(weak, NoTradeIntent)


def test_multiplier_down_replay_clamps_take_profit_and_stop_loss() -> None:
    decision = decide_multiplier(
        history=_ticks(["104", "103", "102", "101", "100"]),
        symbol="R_10",
        policy=_policy(),
    )
    assert isinstance(decision, MultiplierIntent)
    assert decision.contract_type is ContractType.MULTDOWN

    take_profit = replay_multiplier_estimate(
        decision,
        entry_tick=Tick(epoch=4, quote=Decimal("100")),
        exit_tick=Tick(epoch=5, quote=Decimal("80")),
        observed_commission=Decimal("0"),
    )
    stop_loss = replay_multiplier_estimate(
        decision,
        entry_tick=Tick(epoch=4, quote=Decimal("100")),
        exit_tick=Tick(epoch=5, quote=Decimal("120")),
        observed_commission=Decimal("0"),
    )

    assert take_profit.profit == Decimal("1.00")
    assert stop_loss.profit == Decimal("-0.50")


@pytest.mark.parametrize("commission", [Decimal("-1"), Decimal("NaN")])
def test_multiplier_replay_rejects_invalid_inputs(commission: Decimal) -> None:
    intent = MultiplierIntent(
        symbol="R_10",
        contract_type=ContractType.MULTUP,
        stake=Decimal("1"),
        multiplier=Decimal("10"),
        stop_loss=Decimal("0.5"),
        take_profit=Decimal("1"),
        maximum_holding_ticks=5,
        strategy_reason="test",
    )
    with pytest.raises(InvalidMultiplierPolicy):
        replay_multiplier_estimate(
            intent,
            entry_tick=Tick(epoch=1, quote=Decimal("100")),
            exit_tick=Tick(epoch=2, quote=Decimal("101")),
            observed_commission=commission,
        )
