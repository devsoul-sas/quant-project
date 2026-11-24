from decimal import Decimal

import pytest

from devsoul_quant.application.paper import UnapprovedPaperExecution, execute_paper
from devsoul_quant.domain.contracts import (
    Basis,
    ContractAction,
    ContractType,
    DurationUnit,
    EnterContractIntent,
    ExitPolicy,
)
from devsoul_quant.domain.replay import EconomyProvenance, Outcome, Tick
from devsoul_quant.domain.risk import RiskDisposition, RiskPolicy


def _intent() -> EnterContractIntent:
    return EnterContractIntent(
        action=ContractAction.ENTER_CONTRACT,
        symbol="SYNTH_OWNED",
        contract_type=ContractType.CALL,
        duration=2,
        duration_unit=DurationUnit.TICKS,
        basis=Basis.STAKE,
        amount_requested=Decimal("1.00"),
        currency="USD",
        barrier=None,
        exit_policy=ExitPolicy.EXPIRY,
        strategy_reason="test",
    )


def test_paper_execution_reuses_the_deterministic_replay_core() -> None:
    intent = _intent()
    execution = execute_paper(
        execution_id="paper-1",
        intent=intent,
        risk_policy=RiskPolicy(max_amount_per_contract=Decimal("1.00"), kill_switch_enabled=False),
        ticks=(
            Tick(epoch=1, quote=Decimal("100")),
            Tick(epoch=2, quote=Decimal("100.1")),
            Tick(epoch=3, quote=Decimal("100.2")),
        ),
    )

    assert execution.execution_id == "paper-1"
    assert execution.risk_decision.disposition is RiskDisposition.APPROVED
    assert execution.risk_decision.intent == intent
    assert execution.replay.outcome is Outcome.WIN
    assert execution.replay.economy is EconomyProvenance.UNAVAILABLE


def test_paper_execution_dispatches_even_contract_to_digit_replay() -> None:
    intent = _intent().model_copy(update={"contract_type": ContractType.DIGITEVEN, "duration": 1})

    execution = execute_paper(
        execution_id="paper-digit-1",
        intent=intent,
        risk_policy=RiskPolicy(max_amount_per_contract=Decimal("1.00"), kill_switch_enabled=False),
        ticks=(
            Tick(epoch=1, quote=Decimal("100.1"), pip_size=1),
            Tick(epoch=2, quote=Decimal("100.2"), pip_size=1),
        ),
    )

    assert execution.replay.outcome is Outcome.WIN


def test_paper_execution_fails_closed_without_risk_approval() -> None:
    intent = _intent()
    with pytest.raises(UnapprovedPaperExecution, match="REJECTED"):
        execute_paper(
            execution_id="paper-1",
            intent=intent,
            risk_policy=RiskPolicy(
                max_amount_per_contract=Decimal("1.00"),
                kill_switch_enabled=True,
            ),
            ticks=(
                Tick(epoch=1, quote=Decimal("100")),
                Tick(epoch=2, quote=Decimal("100.1")),
                Tick(epoch=3, quote=Decimal("100.2")),
            ),
        )


def test_paper_execution_rejects_a_blank_execution_id() -> None:
    intent = _intent()
    with pytest.raises(ValueError, match="execution_id"):
        execute_paper(
            execution_id=" ",
            intent=intent,
            risk_policy=RiskPolicy(
                max_amount_per_contract=Decimal("1.00"), kill_switch_enabled=False
            ),
            ticks=(
                Tick(epoch=1, quote=Decimal("100")),
                Tick(epoch=2, quote=Decimal("100.1")),
                Tick(epoch=3, quote=Decimal("100.2")),
            ),
        )


def test_paper_execution_cannot_bypass_the_policy_with_a_larger_intent() -> None:
    large_intent = _intent().model_copy(update={"amount_requested": Decimal("1000000.00")})

    with pytest.raises(UnapprovedPaperExecution, match="REJECTED"):
        execute_paper(
            execution_id="paper-2",
            intent=large_intent,
            risk_policy=RiskPolicy(
                max_amount_per_contract=Decimal("1.00"), kill_switch_enabled=False
            ),
            ticks=(
                Tick(epoch=1, quote=Decimal("100")),
                Tick(epoch=2, quote=Decimal("100.1")),
                Tick(epoch=3, quote=Decimal("100.2")),
            ),
        )
