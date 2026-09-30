from decimal import Decimal

import pytest

from devsoul_quant.domain.contracts import (
    Basis,
    ContractAction,
    ContractType,
    DurationUnit,
    EnterContractIntent,
    ExitPolicy,
)
from devsoul_quant.domain.replay import Outcome
from devsoul_quant.domain.trading import (
    Adjustment,
    InvalidTradeTransition,
    Trade,
    TradeState,
)


def _intent() -> EnterContractIntent:
    return EnterContractIntent(
        action=ContractAction.ENTER_CONTRACT,
        symbol="SYNTH_OWNED",
        contract_type=ContractType.CALL,
        duration=3,
        duration_unit=DurationUnit.TICKS,
        basis=Basis.STAKE,
        amount_requested=Decimal("1.00"),
        currency="USD",
        barrier=None,
        exit_policy=ExitPolicy.EXPIRY,
        strategy_reason="test",
    )


def test_trade_opens_and_closes_by_returning_new_immutable_states() -> None:
    pending = Trade.pending(trade_id="trade-1", intent=_intent())

    opened = pending.open(position_id="paper-position-1")
    closed = opened.close(Outcome.WIN)

    assert pending.state is TradeState.PENDING
    assert pending.position_id is None
    assert opened.state is TradeState.OPEN
    assert opened.position_id == "paper-position-1"
    assert closed.state is TradeState.CLOSED
    assert closed.outcome is Outcome.WIN
    assert closed.intent == pending.intent


def test_trade_rejects_illegal_state_transitions() -> None:
    pending = Trade.pending(trade_id="trade-1", intent=_intent())
    opened = pending.open(position_id="paper-position-1")
    closed = opened.close(Outcome.LOSS)

    with pytest.raises(InvalidTradeTransition, match="PENDING"):
        pending.close(Outcome.LOSS)
    with pytest.raises(InvalidTradeTransition, match="OPEN"):
        opened.open(position_id="paper-position-2")
    with pytest.raises(InvalidTradeTransition, match="CLOSED"):
        closed.close(Outcome.WIN)


def test_adjustment_references_history_without_mutating_it() -> None:
    original = Trade.pending(trade_id="trade-1", intent=_intent())

    adjustment = Adjustment(
        adjustment_id="adjustment-1",
        original_event_id="event-1",
        reason="correct external reference",
    )

    assert adjustment.original_event_id == "event-1"
    assert original.state is TradeState.PENDING


@pytest.mark.parametrize("value", ["", "   "])
def test_trade_and_adjustment_reject_blank_identifiers(value: str) -> None:
    with pytest.raises(ValueError):
        Trade.pending(trade_id=value, intent=_intent())
    with pytest.raises(ValueError):
        Adjustment(adjustment_id="adjustment-1", original_event_id=value, reason="reason")
