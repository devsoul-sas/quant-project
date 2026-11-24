"""In-memory Even/Odd paper simulation tests."""

from decimal import Decimal

import pytest

from devsoul_quant.application.demo_execution import DemoProposal
from devsoul_quant.application.digit_paper import (
    UnsupportedDigitContracts,
    observe_digit_economics,
    simulate_digit_decision,
)
from devsoul_quant.domain.contracts import EnterContractIntent, NoTradeIntent
from devsoul_quant.domain.digit_strategy import DigitDecisionPolicy, DigitEconomics
from devsoul_quant.domain.replay import EconomyProvenance, Outcome, Tick


class FakeDigitGateway:
    def __init__(self, available: frozenset[str]) -> None:
        self.available = available
        self.proposed: list[EnterContractIntent] = []

    def available_contract_types(self, symbol: str) -> frozenset[str]:
        assert symbol == "R_10"
        return self.available

    def propose(self, intent: EnterContractIntent) -> DemoProposal:
        self.proposed.append(intent)
        payout = Decimal("1.9") if intent.contract_type.value == "DIGITEVEN" else Decimal("1.8")
        return DemoProposal(f"p-{intent.contract_type.value}", Decimal("1"), payout)


def test_observe_digit_economics_quotes_both_supported_sides() -> None:
    gateway = FakeDigitGateway(frozenset({"DIGITEVEN", "DIGITODD"}))

    even, odd = observe_digit_economics(
        gateway=gateway,
        symbol="R_10",
        amount_requested=Decimal("1"),
    )

    assert even == DigitEconomics.even(ask_price=Decimal("1"), payout=Decimal("1.9"))
    assert odd == DigitEconomics.odd(ask_price=Decimal("1"), payout=Decimal("1.8"))
    assert [intent.contract_type.value for intent in gateway.proposed] == [
        "DIGITEVEN",
        "DIGITODD",
    ]


def test_observe_digit_economics_rejects_incomplete_contract_family() -> None:
    gateway = FakeDigitGateway(frozenset({"DIGITEVEN"}))

    with pytest.raises(UnsupportedDigitContracts, match="DIGITODD"):
        observe_digit_economics(
            gateway=gateway,
            symbol="R_10",
            amount_requested=Decimal("1"),
        )

    assert gateway.proposed == []


def test_digit_paper_simulation_uses_observed_payout_for_profit() -> None:
    history = tuple(
        Tick(epoch=index, quote=Decimal(f"100.{digit}"), pip_size=1)
        for index, digit in enumerate((0, 2, 4, 6, 8) * 20)
    )

    result = simulate_digit_decision(
        history=history,
        settlement_tick=Tick(epoch=100, quote=Decimal("100.2"), pip_size=1),
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

    assert isinstance(result.decision, EnterContractIntent)
    assert result.outcome is Outcome.WIN
    assert result.profit == Decimal("0.9")
    assert result.economy is EconomyProvenance.OBSERVED


def test_digit_paper_simulation_does_not_settle_a_no_trade_decision() -> None:
    history = tuple(
        Tick(epoch=index, quote=Decimal(f"100.{digit}"), pip_size=1)
        for index, digit in enumerate(range(10))
    )

    result = simulate_digit_decision(
        history=history,
        settlement_tick=Tick(epoch=10, quote=Decimal("100.2"), pip_size=1),
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

    assert isinstance(result.decision, NoTradeIntent)
    assert result.outcome is None
    assert result.profit is None
