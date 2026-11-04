"""Windowed momentum and mean-reversion strategy tests."""

from decimal import Decimal

import pytest

from devsoul_quant.domain.contracts import (
    ContractAction,
    ContractType,
    EnterContractIntent,
    NoTradeIntent,
)
from devsoul_quant.domain.replay import Tick
from devsoul_quant.domain.strategy import (
    InvalidStrategyInput,
    mean_reversion_decision,
    momentum_window_decision,
)


def _history(*quotes: str) -> tuple[Tick, ...]:
    return tuple(Tick(epoch=i, quote=Decimal(quote)) for i, quote in enumerate(quotes))


def test_momentum_window_calls_when_latest_exceeds_lookback() -> None:
    decision = momentum_window_decision(
        history=_history("1.00", "1.01", "1.02"),
        lookback=2,
        duration=3,
        amount_requested=Decimal("1.00"),
    )

    assert isinstance(decision, EnterContractIntent)
    assert decision.contract_type is ContractType.CALL


def test_momentum_window_puts_when_latest_falls() -> None:
    decision = momentum_window_decision(
        history=_history("1.02", "1.01", "1.00"),
        lookback=2,
        duration=3,
        amount_requested=Decimal("1.00"),
    )

    assert isinstance(decision, EnterContractIntent)
    assert decision.contract_type is ContractType.PUT


def test_mean_reversion_fades_the_move() -> None:
    up = mean_reversion_decision(
        history=_history("1.00", "1.01", "1.02"),
        lookback=2,
        duration=3,
        amount_requested=Decimal("1.00"),
    )
    down = mean_reversion_decision(
        history=_history("1.02", "1.01", "1.00"),
        lookback=2,
        duration=3,
        amount_requested=Decimal("1.00"),
    )

    assert isinstance(up, EnterContractIntent)
    assert up.contract_type is ContractType.PUT
    assert isinstance(down, EnterContractIntent)
    assert down.contract_type is ContractType.CALL


def test_window_decision_emits_no_trade_when_flat() -> None:
    decision = momentum_window_decision(
        history=_history("1.00", "1.00", "1.00"),
        lookback=2,
        duration=3,
        amount_requested=Decimal("1.00"),
    )

    assert isinstance(decision, NoTradeIntent)
    assert decision.action is ContractAction.NO_TRADE


def test_window_decision_accepts_an_explicit_symbol() -> None:
    decision = momentum_window_decision(
        history=_history("1.00", "1.01"),
        lookback=1,
        duration=3,
        amount_requested=Decimal("1.00"),
        symbol="EURUSD",
    )

    assert isinstance(decision, EnterContractIntent)
    assert decision.symbol == "EURUSD"


@pytest.mark.parametrize("lookback", [0, -1, True])
def test_window_decision_rejects_invalid_lookback(lookback: object) -> None:
    with pytest.raises(InvalidStrategyInput, match="lookback"):
        momentum_window_decision(
            history=_history("1.00", "1.01"),
            lookback=lookback,  # type: ignore[arg-type]
            duration=3,
            amount_requested=Decimal("1.00"),
        )


def test_window_decision_rejects_short_history() -> None:
    with pytest.raises(InvalidStrategyInput, match="short"):
        momentum_window_decision(
            history=_history("1.00", "1.01"),
            lookback=2,
            duration=3,
            amount_requested=Decimal("1.00"),
        )


def test_window_decision_rejects_unordered_history() -> None:
    with pytest.raises(InvalidStrategyInput, match="increasing"):
        momentum_window_decision(
            history=(
                Tick(epoch=5, quote=Decimal("1.00")),
                Tick(epoch=4, quote=Decimal("1.01")),
            ),
            lookback=1,
            duration=3,
            amount_requested=Decimal("1.00"),
        )
