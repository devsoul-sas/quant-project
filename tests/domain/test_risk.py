from decimal import Decimal

import pytest

from devsoul_quant.domain.contracts import (
    Basis,
    ContractAction,
    ContractType,
    DurationUnit,
    EnterContractIntent,
    ExitContractIntent,
    ExitPolicy,
    NoTradeIntent,
)
from devsoul_quant.domain.risk import InvalidRiskPolicy, RiskDisposition, RiskPolicy


def _enter(amount: Decimal = Decimal("1.00")) -> EnterContractIntent:
    return EnterContractIntent(
        action=ContractAction.ENTER_CONTRACT,
        symbol="SYNTH_OWNED",
        contract_type=ContractType.CALL,
        duration=3,
        duration_unit=DurationUnit.TICKS,
        basis=Basis.STAKE,
        amount_requested=amount,
        currency="USD",
        barrier=None,
        exit_policy=ExitPolicy.EXPIRY,
        strategy_reason="test",
    )


def test_risk_approves_only_an_enter_within_the_amount_limit() -> None:
    policy = RiskPolicy(max_amount_per_contract=Decimal("1.00"), kill_switch_enabled=False)
    approved_intent = _enter()
    rejected_intent = _enter(Decimal("1.01"))

    approved = policy.evaluate(approved_intent)
    rejected = policy.evaluate(rejected_intent)

    assert approved.disposition is RiskDisposition.APPROVED
    assert approved.intent == approved_intent
    assert rejected.disposition is RiskDisposition.REJECTED
    assert rejected.intent == rejected_intent
    assert "amount" in rejected.reason


def test_risk_kill_switch_rejects_every_enter() -> None:
    policy = RiskPolicy(max_amount_per_contract=Decimal("1.00"), kill_switch_enabled=True)

    decision = policy.evaluate(_enter())

    assert decision.disposition is RiskDisposition.REJECTED
    assert "kill switch" in decision.reason


def test_risk_policy_requires_an_explicit_kill_switch_decision() -> None:
    with pytest.raises(TypeError):
        RiskPolicy(max_amount_per_contract=Decimal("1.00"))  # type: ignore[call-arg]


def test_risk_preserves_no_trade_as_no_action() -> None:
    policy = RiskPolicy(max_amount_per_contract=Decimal("1.00"), kill_switch_enabled=False)
    intent = NoTradeIntent(
        action=ContractAction.NO_TRADE,
        strategy_reason="flat synthetic momentum",
    )

    decision = policy.evaluate(intent)

    assert decision.disposition is RiskDisposition.NO_ACTION
    assert decision.intent == intent


@pytest.mark.parametrize(
    "arguments",
    [
        {"max_amount_per_contract": Decimal("NaN"), "kill_switch_enabled": False},
        {"max_amount_per_contract": Decimal("1"), "kill_switch_enabled": 1},
    ],
)
def test_risk_policy_rejects_unsafe_configuration(arguments: dict[str, object]) -> None:
    with pytest.raises(InvalidRiskPolicy):
        RiskPolicy(**arguments)  # type: ignore[arg-type]


def test_risk_rejects_an_unsupported_exit_action() -> None:
    policy = RiskPolicy(max_amount_per_contract=Decimal("1.00"), kill_switch_enabled=False)
    intent = ExitContractIntent(
        action=ContractAction.EXIT_CONTRACT,
        position_id="position-1",
        minimum_sell_price=None,
        exit_reason="test",
    )

    decision = policy.evaluate(intent)

    assert decision.disposition is RiskDisposition.REJECTED
    assert decision.intent == intent
