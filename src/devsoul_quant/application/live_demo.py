"""Ephemeral live demo orchestration over a Deriv demo tick feed."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from devsoul_quant import __version__
from devsoul_quant.adapters.deriv.ephemeral import EphemeralTickCache
from devsoul_quant.application.paper import execute_paper
from devsoul_quant.domain.contracts import ContractAction, EnterContractIntent
from devsoul_quant.domain.execution_mode import ExecutionMode
from devsoul_quant.domain.ledger import InMemoryLedger
from devsoul_quant.domain.replay import EconomyProvenance, Outcome, Tick
from devsoul_quant.domain.risk import RiskDisposition, RiskPolicy
from devsoul_quant.domain.strategy import momentum_decision


class InvalidLiveDemo(ValueError):
    """Raised when a live demo slice cannot be built safely."""


@dataclass(frozen=True, slots=True)
class LiveDemoReport:
    """Stable public report for one ephemeral, non-economic live demo decision."""

    schema_version: str
    code_version: str
    execution_mode: ExecutionMode
    data_source: str
    symbol: str
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
    cache_ttl_seconds: int
    cache_size: int
    cache_expired_count: int

    def to_dict(self) -> dict[str, Any]:
        """Return a deterministic, JSON-compatible public representation."""
        return {
            "schema_version": self.schema_version,
            "code_version": self.code_version,
            "execution_mode": self.execution_mode.value,
            "data_source": self.data_source,
            "symbol": self.symbol,
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
            "cache_ttl_seconds": self.cache_ttl_seconds,
            "cache_size": self.cache_size,
            "cache_expired_count": self.cache_expired_count,
        }


def run_live_demo(
    *,
    ticks: Sequence[Tick],
    symbol: str,
    duration: int = 3,
    amount_requested: Decimal = Decimal("1.00"),
) -> LiveDemoReport:
    """Run generator-free strategy/risk/paper/ledger over ephemeral demo ticks."""
    if len(ticks) < 2:
        raise InvalidLiveDemo("live demo requires at least two ticks")
    if not isinstance(symbol, str) or not symbol.strip():
        raise InvalidLiveDemo("symbol must be a non-blank string")

    cache = EphemeralTickCache()
    now_epoch = ticks[-1].epoch
    for tick in ticks:
        cache.store(tick, now_epoch=tick.epoch)

    correlation_id = f"live-demo-{symbol}-{ticks[0].epoch}"
    active_ledger = InMemoryLedger()

    def record(event_type: str, payload: dict[str, str | int | bool | None]) -> str:
        sequence = len(active_ledger.events)
        event_id = f"{correlation_id}:{sequence:04d}"
        causation_id = active_ledger.events[-1].event_id if active_ledger.events else None
        active_ledger.append(
            event_id=event_id,
            event_type=event_type,
            occurred_at=ticks[0].epoch + sequence,
            correlation_id=correlation_id,
            causation_id=causation_id,
            payload=payload,
        )
        return event_id

    record(
        "DEMO_STARTED",
        {"symbol": symbol, "mode": ExecutionMode.EPHEMERAL_PUBLIC_INTEGRATION.value},
    )
    record(
        "MARKET_RECEIVED",
        {"source": "DERIV_DEMO_EPHEMERAL", "tick_count": len(ticks), "symbol": symbol},
    )

    intent = momentum_decision(
        history=ticks[:2],
        duration=duration,
        amount_requested=amount_requested,
        symbol=symbol,
    )
    if isinstance(intent, EnterContractIntent):
        strategy_payload: dict[str, str | int | bool | None] = {
            "action": intent.action.value,
            "reason": intent.strategy_reason,
            "symbol": intent.symbol,
            "contract_type": intent.contract_type.value,
            "duration": intent.duration,
            "duration_unit": intent.duration_unit.value,
            "basis": intent.basis.value,
            "amount_requested": str(intent.amount_requested),
            "currency": intent.currency,
            "barrier": str(intent.barrier) if intent.barrier is not None else None,
            "exit_policy": intent.exit_policy.value,
        }
    else:
        strategy_payload = {
            "action": intent.action.value,
            "reason": intent.strategy_reason,
        }
    record("STRATEGY_DECIDED", strategy_payload)

    risk_policy = RiskPolicy(max_amount_per_contract=amount_requested, kill_switch_enabled=False)
    risk_decision = risk_policy.evaluate(intent)
    record(
        "RISK_DECIDED",
        {"disposition": risk_decision.disposition.value, "reason": risk_decision.reason},
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
        {"action": intent.action.value, "outcome": outcome.value if outcome is not None else None},
    )
    expired = cache.expire(now_epoch=now_epoch)
    ledger_valid = active_ledger.verify()
    head_hash = active_ledger.events[-1].event_hash
    return LiveDemoReport(
        schema_version="1",
        code_version=__version__,
        execution_mode=ExecutionMode.EPHEMERAL_PUBLIC_INTEGRATION,
        data_source="DERIV_DEMO_EPHEMERAL",
        symbol=symbol,
        action=intent.action,
        risk_disposition=risk_decision.disposition,
        outcome=outcome,
        wins=int(outcome is Outcome.WIN),
        losses=int(outcome is Outcome.LOSS),
        no_trades=int(intent.action is ContractAction.NO_TRADE),
        economy=EconomyProvenance.UNAVAILABLE,
        event_count=len(active_ledger.events),
        ledger_hashes=tuple(event.event_hash for event in active_ledger.events),
        ledger_head_hash=head_hash,
        ledger_valid=ledger_valid,
        profitability_claim=False,
        cache_ttl_seconds=cache.ttl_seconds,
        cache_size=len(cache),
        cache_expired_count=expired,
    )
