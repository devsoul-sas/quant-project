"""Tests for the rich, auditable decision engine."""

from decimal import Decimal

import pytest

from devsoul_quant.domain.decision import (
    Decision,
    DecisionAction,
    InvalidDecision,
    ReversionPolicy,
    even_odd_decision,
    multiplier_decision,
)
from devsoul_quant.domain.digit_strategy import DigitDecisionPolicy, DigitEconomics
from devsoul_quant.domain.range_regime import RangePolicy, ReferenceMode
from devsoul_quant.domain.replay import Tick


def _ticks(digits: list[int]) -> tuple[Tick, ...]:
    return tuple(
        Tick(
            epoch=1_700_000_000 + i,
            quote=Decimal("100.0000") + Decimal(d) / Decimal("10000"),
            pip_size=4,
        )
        for i, d in enumerate(digits)
    )


def _quote_ticks(quotes: list[str]) -> tuple[Tick, ...]:
    return tuple(Tick(epoch=1_700_000_000 + i, quote=Decimal(q)) for i, q in enumerate(quotes))


def _parity_policy() -> DigitDecisionPolicy:
    return DigitDecisionPolicy(
        min_samples=10,
        z_score=Decimal("1.96"),
        min_edge_probability=Decimal("0"),
    )


def _economics() -> tuple[DigitEconomics, DigitEconomics]:
    return (
        DigitEconomics.even(ask_price=Decimal("1"), payout=Decimal("2")),
        DigitEconomics.odd(ask_price=Decimal("1"), payout=Decimal("2")),
    )


# --- Decision record validation -------------------------------------------------


def test_decision_requires_a_valid_action() -> None:
    with pytest.raises(InvalidDecision, match="action"):
        Decision(
            action="EVEN",  # type: ignore[arg-type]
            probability=None,
            probability_lower=None,
            probability_upper=None,
            uncertainty=None,
            expected_value_per_stake=None,
            risk_edge=None,
            reason="x",
        )


def test_decision_requires_a_reason() -> None:
    with pytest.raises(InvalidDecision, match="reason"):
        Decision(
            action=DecisionAction.NO_TRADE,
            probability=None,
            probability_lower=None,
            probability_upper=None,
            uncertainty=None,
            expected_value_per_stake=None,
            risk_edge=None,
            reason="",
        )


def test_decision_rejects_probability_out_of_range() -> None:
    with pytest.raises(InvalidDecision, match="probability"):
        Decision(
            action=DecisionAction.NO_TRADE,
            probability=Decimal("1.5"),
            probability_lower=None,
            probability_upper=None,
            uncertainty=None,
            expected_value_per_stake=None,
            risk_edge=None,
            reason="x",
        )


def test_decision_rejects_lower_above_upper() -> None:
    with pytest.raises(InvalidDecision, match="probability_lower"):
        Decision(
            action=DecisionAction.NO_TRADE,
            probability=Decimal("0.5"),
            probability_lower=Decimal("0.6"),
            probability_upper=Decimal("0.4"),
            uncertainty=Decimal("0.2"),
            expected_value_per_stake=Decimal("0"),
            risk_edge=Decimal("0"),
            reason="x",
        )


def test_decision_rejects_negative_uncertainty() -> None:
    with pytest.raises(InvalidDecision, match="uncertainty"):
        Decision(
            action=DecisionAction.NO_TRADE,
            probability=None,
            probability_lower=None,
            probability_upper=None,
            uncertainty=Decimal("-0.1"),
            expected_value_per_stake=None,
            risk_edge=None,
            reason="x",
        )


# --- Even/Odd decisions ---------------------------------------------------------


def test_even_odd_insufficient_sample_is_bare_no_trade() -> None:
    even, odd = _economics()
    decision = even_odd_decision(
        history=_ticks([2, 2, 1, 1, 2]),
        even_economics=even,
        odd_economics=odd,
        policy=_parity_policy(),
    )
    assert decision.action is DecisionAction.NO_TRADE
    assert decision.probability is None
    assert decision.expected_value_per_stake is None
    assert decision.risk_edge is None


def test_even_odd_enters_when_edge_is_positive() -> None:
    even, odd = _economics()
    decision = even_odd_decision(
        history=_ticks([2] * 80 + [1] * 20),
        even_economics=even,
        odd_economics=odd,
        policy=_parity_policy(),
    )
    assert decision.action is DecisionAction.EVEN
    assert decision.probability == Decimal("0.80")
    assert decision.probability_lower is not None
    assert decision.probability_lower > Decimal("0.5")
    assert decision.probability_lower < Decimal("0.8") < decision.probability_upper  # type: ignore[operator]
    assert decision.uncertainty == decision.probability_upper - decision.probability_lower  # type: ignore[operator]
    assert decision.risk_edge == decision.probability_lower - Decimal("0.5")
    assert decision.expected_value_per_stake == Decimal("0.6")


def test_even_odd_no_trade_when_edge_is_non_positive() -> None:
    even, odd = _economics()
    decision = even_odd_decision(
        history=_ticks([2] * 50 + [1] * 50),
        even_economics=even,
        odd_economics=odd,
        policy=_parity_policy(),
    )
    assert decision.action is DecisionAction.NO_TRADE
    assert decision.forecast_action is DecisionAction.EVEN
    assert decision.probability == Decimal("0.5")
    assert decision.risk_edge is not None and decision.risk_edge <= 0
    assert decision.expected_value_per_stake == Decimal("0")


def test_even_odd_entry_records_same_forecast_action() -> None:
    even, odd = _economics()
    decision = even_odd_decision(
        history=_ticks([2] * 80 + [1] * 20),
        even_economics=even,
        odd_economics=odd,
        policy=_parity_policy(),
    )

    assert decision.action is DecisionAction.EVEN
    assert decision.forecast_action is DecisionAction.EVEN


def test_even_odd_rejects_non_increasing_history() -> None:
    even, odd = _economics()
    ticks = list(_ticks([2] * 12))
    ticks[1] = Tick(epoch=ticks[0].epoch, quote=ticks[1].quote, pip_size=4)
    with pytest.raises(InvalidDecision, match="strictly increasing"):
        even_odd_decision(
            history=tuple(ticks),
            even_economics=even,
            odd_economics=odd,
            policy=_parity_policy(),
        )


# --- ReversionPolicy validation -------------------------------------------------


def test_reversion_policy_rejects_non_positive_z_threshold() -> None:
    with pytest.raises(InvalidDecision, match="z_score_threshold"):
        ReversionPolicy(
            z_score_threshold=Decimal("0"),
            min_deceleration=Decimal("0"),
            min_return_frequency=Decimal("0"),
        )


def test_reversion_policy_rejects_negative_deceleration() -> None:
    with pytest.raises(InvalidDecision, match="min_deceleration"):
        ReversionPolicy(
            z_score_threshold=Decimal("1.5"),
            min_deceleration=Decimal("-0.1"),
            min_return_frequency=Decimal("0"),
        )


# --- Multiplier decisions -------------------------------------------------------


def _multup_quotes() -> tuple[Tick, ...]:
    return _quote_ticks(["100", "98", "96", "96.5", "96.2", "96.0"])


def _multdown_quotes() -> tuple[Tick, ...]:
    return _quote_ticks(["100", "102", "104", "103.5", "103.8", "104.0"])


def _range_policy() -> RangePolicy:
    return RangePolicy(window=5, reference_mode=ReferenceMode.DISPLACEMENT)


def _permissive_reversion() -> ReversionPolicy:
    return ReversionPolicy(
        z_score_threshold=Decimal("1.5"),
        min_deceleration=Decimal("0"),
        min_return_frequency=Decimal("0"),
    )


def test_multiplier_enters_multup_on_reversion_setup() -> None:
    decision = multiplier_decision(
        history=_multup_quotes(),
        range_policy=_range_policy(),
        reversion_policy=_permissive_reversion(),
    )
    assert decision.action is DecisionAction.MULTUP
    assert decision.probability is None
    assert decision.reason


def test_multiplier_enters_multdown_on_reversion_setup() -> None:
    decision = multiplier_decision(
        history=_multdown_quotes(),
        range_policy=_range_policy(),
        reversion_policy=_permissive_reversion(),
    )
    assert decision.action is DecisionAction.MULTDOWN


def test_multiplier_insufficient_warm_up_is_bare_no_trade() -> None:
    decision = multiplier_decision(
        history=_quote_ticks(["100", "98"]),
        range_policy=_range_policy(),
        reversion_policy=_permissive_reversion(),
    )
    assert decision.action is DecisionAction.NO_TRADE
    assert decision.probability is None


def test_multiplier_neutral_z_score_is_no_trade() -> None:
    decision = multiplier_decision(
        history=_multup_quotes(),
        range_policy=_range_policy(),
        reversion_policy=ReversionPolicy(
            z_score_threshold=Decimal("100"),
            min_deceleration=Decimal("0"),
            min_return_frequency=Decimal("0"),
        ),
    )
    assert decision.action is DecisionAction.NO_TRADE
    assert "neutral" in decision.reason


def test_multiplier_no_deceleration_is_no_trade() -> None:
    decision = multiplier_decision(
        history=_multup_quotes(),
        range_policy=_range_policy(),
        reversion_policy=ReversionPolicy(
            z_score_threshold=Decimal("1.5"),
            min_deceleration=Decimal("100"),
            min_return_frequency=Decimal("0"),
        ),
    )
    assert decision.action is DecisionAction.NO_TRADE
    assert "deceleration" in decision.reason


def test_multiplier_insufficient_reversion_frequency_is_no_trade() -> None:
    decision = multiplier_decision(
        history=_multup_quotes(),
        range_policy=_range_policy(),
        reversion_policy=ReversionPolicy(
            z_score_threshold=Decimal("1.5"),
            min_deceleration=Decimal("0"),
            min_return_frequency=Decimal("0.9"),
        ),
    )
    assert decision.action is DecisionAction.NO_TRADE
    assert "frequency" in decision.reason


def test_multiplier_degenerate_flat_window_is_no_trade() -> None:
    decision = multiplier_decision(
        history=_quote_ticks(["100", "100", "100", "100", "100", "100"]),
        range_policy=_range_policy(),
        reversion_policy=_permissive_reversion(),
    )
    assert decision.action is DecisionAction.NO_TRADE
    assert "degenerate" in decision.reason
