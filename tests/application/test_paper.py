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
from devsoul_quant.domain.risk import RiskDecision, RiskDisposition


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
    execution = execute_paper(
        execution_id="paper-1",
        intent=_intent(),
        risk_decision=RiskDecision(RiskDisposition.APPROVED, "approved"),
        ticks=(
            Tick(epoch=1, quote=Decimal("100")),
            Tick(epoch=2, quote=Decimal("100.1")),
            Tick(epoch=3, quote=Decimal("100.2")),
        ),
    )

    assert execution.execution_id == "paper-1"
    assert execution.replay.outcome is Outcome.WIN
    assert execution.replay.economy is EconomyProvenance.UNAVAILABLE


def test_paper_execution_fails_closed_without_risk_approval() -> None:
    with pytest.raises(UnapprovedPaperExecution, match="REJECTED"):
        execute_paper(
            execution_id="paper-1",
            intent=_intent(),
            risk_decision=RiskDecision(RiskDisposition.REJECTED, "kill switch"),
            ticks=(
                Tick(epoch=1, quote=Decimal("100")),
                Tick(epoch=2, quote=Decimal("100.1")),
                Tick(epoch=3, quote=Decimal("100.2")),
            ),
        )


def test_paper_execution_rejects_a_blank_execution_id() -> None:
    with pytest.raises(ValueError, match="execution_id"):
        execute_paper(
            execution_id=" ",
            intent=_intent(),
            risk_decision=RiskDecision(RiskDisposition.APPROVED, "approved"),
            ticks=(
                Tick(epoch=1, quote=Decimal("100")),
                Tick(epoch=2, quote=Decimal("100.1")),
                Tick(epoch=3, quote=Decimal("100.2")),
            ),
        )
