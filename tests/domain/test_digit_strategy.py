"""Causal digit-feature tests for Deriv paper research."""

from decimal import Decimal

import pytest

from devsoul_quant.domain.contracts import ContractType, EnterContractIntent, NoTradeIntent
from devsoul_quant.domain.digit_strategy import (
    DigitDecisionPolicy,
    DigitEconomics,
    InvalidDigitPolicy,
    InvalidDigitTick,
    digit_parity_decision,
    last_digit,
)
from devsoul_quant.domain.replay import InvalidTick, Tick


def test_last_digit_uses_provider_pip_size_instead_of_decimal_exponent() -> None:
    tick = Tick(epoch=1, quote=Decimal("123.4"), pip_size=3)

    assert last_digit(tick) == 0


def test_last_digit_rejects_tick_without_provider_precision() -> None:
    with pytest.raises(InvalidDigitTick, match="pip_size"):
        last_digit(Tick(epoch=1, quote=Decimal("123.4")))


@pytest.mark.parametrize("pip_size", [-1, True, "3"])
def test_tick_rejects_invalid_pip_size(pip_size: object) -> None:
    with pytest.raises(InvalidTick, match="pip_size"):
        Tick(epoch=1, quote=Decimal("123.4"), pip_size=pip_size)  # type: ignore[arg-type]


def test_digit_decision_fails_closed_before_minimum_sample() -> None:
    history = tuple(
        Tick(epoch=index, quote=Decimal(f"100.{digit}"), pip_size=1)
        for index, digit in enumerate((0, 1, 2, 3))
    )
    decision = digit_parity_decision(
        history=history,
        even_economics=DigitEconomics.even(ask_price=Decimal("1"), payout=Decimal("1.9")),
        odd_economics=DigitEconomics.odd(ask_price=Decimal("1"), payout=Decimal("1.9")),
        policy=DigitDecisionPolicy(
            min_samples=100,
            z_score=Decimal("2.576"),
            min_edge_probability=Decimal("0.01"),
        ),
        amount_requested=Decimal("1"),
        symbol="R_10",
    )

    assert isinstance(decision, NoTradeIntent)
    assert "insufficient sample" in decision.strategy_reason


def test_digit_decision_enters_even_only_when_conservative_edge_clears_break_even() -> None:
    history = tuple(
        Tick(epoch=index, quote=Decimal(f"100.{digit}"), pip_size=1)
        for index, digit in enumerate((0, 2, 4, 6, 8) * 20)
    )

    decision = digit_parity_decision(
        history=history,
        even_economics=DigitEconomics.even(ask_price=Decimal("1"), payout=Decimal("1.9")),
        odd_economics=DigitEconomics.odd(ask_price=Decimal("1"), payout=Decimal("1.9")),
        policy=DigitDecisionPolicy(
            min_samples=100,
            z_score=Decimal("2.576"),
            min_edge_probability=Decimal("0.01"),
        ),
        amount_requested=Decimal("1"),
        symbol="R_10",
    )

    assert isinstance(decision, EnterContractIntent)
    assert decision.contract_type is ContractType.DIGITEVEN
    assert decision.duration == 1
    assert decision.symbol == "R_10"


def test_digit_decision_emits_no_trade_for_balanced_history() -> None:
    history = tuple(
        Tick(epoch=index, quote=Decimal(f"100.{digit}"), pip_size=1)
        for index, digit in enumerate(tuple(range(10)) * 20)
    )

    decision = digit_parity_decision(
        history=history,
        even_economics=DigitEconomics.even(ask_price=Decimal("1"), payout=Decimal("1.9")),
        odd_economics=DigitEconomics.odd(ask_price=Decimal("1"), payout=Decimal("1.9")),
        policy=DigitDecisionPolicy(
            min_samples=100,
            z_score=Decimal("2.576"),
            min_edge_probability=Decimal("0.01"),
        ),
        amount_requested=Decimal("1"),
        symbol="R_10",
    )

    assert isinstance(decision, NoTradeIntent)
    assert "does not clear" in decision.strategy_reason


@pytest.mark.parametrize(
    ("min_samples", "z_score", "min_edge"),
    [
        (0, Decimal("2.576"), Decimal("0.01")),
        (100, Decimal("0"), Decimal("0.01")),
        (100, Decimal("2.576"), Decimal("-0.01")),
    ],
)
def test_digit_policy_rejects_unsafe_thresholds(
    min_samples: int, z_score: Decimal, min_edge: Decimal
) -> None:
    with pytest.raises(InvalidDigitPolicy):
        DigitDecisionPolicy(
            min_samples=min_samples,
            z_score=z_score,
            min_edge_probability=min_edge,
        )


@pytest.mark.parametrize(
    ("ask_price", "payout"),
    [
        (Decimal("0"), Decimal("1.9")),
        (Decimal("1"), Decimal("0")),
        (Decimal("NaN"), Decimal("1.9")),
    ],
)
def test_digit_economics_rejects_non_positive_or_non_finite_values(
    ask_price: Decimal, payout: Decimal
) -> None:
    with pytest.raises(InvalidDigitPolicy):
        DigitEconomics.even(ask_price=ask_price, payout=payout)


def test_digit_economics_rejects_non_digit_contract() -> None:
    with pytest.raises(InvalidDigitPolicy, match="Even/Odd"):
        DigitEconomics(ContractType.CALL, Decimal("1"), Decimal("1.9"))


def test_digit_decision_rejects_unordered_history() -> None:
    history = tuple(Tick(epoch=index, quote=Decimal("100.0"), pip_size=1) for index in range(100))
    unordered = (*history[:-1], Tick(epoch=98, quote=Decimal("100.0"), pip_size=1))

    with pytest.raises(InvalidDigitTick, match="increasing"):
        digit_parity_decision(
            history=unordered,
            even_economics=DigitEconomics.even(ask_price=Decimal("1"), payout=Decimal("1.9")),
            odd_economics=DigitEconomics.odd(ask_price=Decimal("1"), payout=Decimal("1.9")),
            policy=DigitDecisionPolicy(
                min_samples=100,
                z_score=Decimal("2.576"),
                min_edge_probability=Decimal("0.01"),
            ),
            amount_requested=Decimal("1"),
            symbol="R_10",
        )
