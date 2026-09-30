"""Deterministic end-to-end synthetic demo orchestration."""

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from devsoul_quant import __version__
from devsoul_quant.application.paper import execute_paper
from devsoul_quant.domain.contracts import ContractAction, EnterContractIntent
from devsoul_quant.domain.execution_mode import ExecutionMode
from devsoul_quant.domain.ledger import InMemoryLedger
from devsoul_quant.domain.replay import EconomyProvenance, Outcome
from devsoul_quant.domain.risk import RiskDisposition, RiskPolicy
from devsoul_quant.domain.strategy import momentum_decision
from devsoul_quant.domain.synthetic import generate_ticks


@dataclass(frozen=True, slots=True)
class DemoReport:
    """Stable public report for one non-economic synthetic decision."""

    schema_version: str
    code_version: str
    seed: int
    execution_mode: ExecutionMode
    data_source: str
    action: ContractAction
    risk_disposition: RiskDisposition
    outcome: Outcome | None
    wins: int
    losses: int
    no_trades: int
    economy: EconomyProvenance
    event_count: int
    ledger_hashes: tuple[str, ...]
    ledger_head_hash: str
    ledger_valid: bool
    profitability_claim: bool

    def to_dict(self) -> dict[str, Any]:
        """Return a deterministic, JSON-compatible public representation."""
        return {
            "schema_version": self.schema_version,
            "code_version": self.code_version,
            "seed": self.seed,
            "execution_mode": self.execution_mode.value,
            "data_source": self.data_source,
            "action": self.action.value,
            "risk_disposition": self.risk_disposition.value,
            "outcome": self.outcome.value if self.outcome is not None else None,
            "wins": self.wins,
            "losses": self.losses,
            "no_trades": self.no_trades,
            "economy": self.economy.value,
            "event_count": self.event_count,
            "ledger_hashes": list(self.ledger_hashes),
            "ledger_head_hash": self.ledger_head_hash,
            "ledger_valid": self.ledger_valid,
            "profitability_claim": self.profitability_claim,
        }


def run_synthetic_demo(*, seed: int, start_epoch: int = 1_700_000_000) -> DemoReport:
    """Run generator, strategy, risk, paper settlement, and ledger as one slice."""
    duration = 3
    amount_requested = Decimal("1.00")
    ticks = generate_ticks(seed=seed, count=duration + 2, start_epoch=start_epoch)
    correlation_id = f"synthetic-demo-{seed}"
    ledger = InMemoryLedger()

    def record(event_type: str, payload: dict[str, str | int | bool | None]) -> str:
        sequence = len(ledger.events)
        event_id = f"{correlation_id}:{sequence:04d}"
        causation_id = ledger.events[-1].event_id if ledger.events else None
        ledger.append(
            event_id=event_id,
            event_type=event_type,
            occurred_at=start_epoch + sequence,
            correlation_id=correlation_id,
            causation_id=causation_id,
            payload=payload,
        )
        return event_id

    record("DEMO_STARTED", {"seed": seed, "mode": ExecutionMode.SYNTHETIC_PAPER.value})
    record(
        "MARKET_GENERATED",
        {"source": "DEVSOUL_SYNTHETIC", "tick_count": len(ticks)},
    )

    intent = momentum_decision(
        history=ticks[:2],
        duration=duration,
        amount_requested=amount_requested,
    )
    record(
        "STRATEGY_DECIDED",
        {"action": intent.action.value, "reason": intent.strategy_reason},
    )

    risk_policy = RiskPolicy(max_amount_per_contract=amount_requested)
    risk_decision = risk_policy.evaluate(intent)
    record(
        "RISK_DECIDED",
        {
            "disposition": risk_decision.disposition.value,
            "reason": risk_decision.reason,
        },
    )

    outcome: Outcome | None = None
    if isinstance(intent, EnterContractIntent):
        execution = execute_paper(
            execution_id=f"{correlation_id}:paper",
            intent=intent,
            risk_policy=risk_policy,
            ticks=ticks[1:],
        )
        outcome = execution.replay.outcome
        record(
            "PAPER_SETTLED",
            {
                "economy": execution.replay.economy.value,
                "outcome": execution.replay.outcome.value,
            },
        )

    record(
        "DEMO_COMPLETED",
        {
            "action": intent.action.value,
            "outcome": outcome.value if outcome is not None else None,
        },
    )
    ledger_valid = ledger.verify()
    head_hash = ledger.events[-1].event_hash
    return DemoReport(
        schema_version="1",
        code_version=__version__,
        seed=seed,
        execution_mode=ExecutionMode.SYNTHETIC_PAPER,
        data_source="DEVSOUL_SYNTHETIC",
        action=intent.action,
        risk_disposition=risk_decision.disposition,
        outcome=outcome,
        wins=int(outcome is Outcome.WIN),
        losses=int(outcome is Outcome.LOSS),
        no_trades=int(intent.action is ContractAction.NO_TRADE),
        economy=EconomyProvenance.UNAVAILABLE,
        event_count=len(ledger.events),
        ledger_hashes=tuple(event.event_hash for event in ledger.events),
        ledger_head_hash=head_hash,
        ledger_valid=ledger_valid,
        profitability_claim=False,
    )
