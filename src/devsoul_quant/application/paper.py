"""Synthetic paper execution using the shared deterministic replay core."""

from collections.abc import Sequence
from dataclasses import dataclass

from devsoul_quant.domain.contracts import EnterContractIntent
from devsoul_quant.domain.replay import ReplayResult, Tick, replay_rise_fall
from devsoul_quant.domain.risk import RiskDecision, RiskDisposition, RiskPolicy


class UnapprovedPaperExecution(ValueError):
    """Raised when paper execution is attempted without risk approval."""


@dataclass(frozen=True, slots=True)
class PaperExecution:
    """One synthetic paper settlement with no inferred monetary result."""

    execution_id: str
    risk_decision: RiskDecision
    replay: ReplayResult


def execute_paper(
    *,
    execution_id: str,
    intent: EnterContractIntent,
    risk_policy: RiskPolicy,
    ticks: Sequence[Tick],
) -> PaperExecution:
    """Settle an approved paper intent through the exact replay implementation."""
    if not execution_id.strip():
        raise ValueError("execution_id must be non-blank")
    risk_decision = risk_policy.evaluate(intent)
    if risk_decision.disposition is not RiskDisposition.APPROVED:
        raise UnapprovedPaperExecution(
            f"paper execution requires APPROVED risk, got {risk_decision.disposition}"
        )
    return PaperExecution(
        execution_id=execution_id,
        risk_decision=risk_decision,
        replay=replay_rise_fall(intent, ticks),
    )
