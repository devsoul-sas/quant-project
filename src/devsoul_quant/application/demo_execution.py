"""Fail-closed orchestration for one ephemeral Deriv demo contract.

This module owns no network or persistence. A caller supplies a demo-only gateway;
all session results remain in memory and can be explicitly discarded with ``clear``.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol

from devsoul_quant.domain.contracts import EnterContractIntent


class DemoTradeRejected(ValueError):
    """Raised before a demo purchase when a safety gate denies execution."""


class AmbiguousDemoExecution(RuntimeError):
    """Raised when a purchase outcome is unknown after one reconciliation."""

    def __init__(self, message: str, open_contract_ids: tuple[str, ...]) -> None:
        super().__init__(message)
        self.open_contract_ids = open_contract_ids


def _positive(value: Decimal, field: str) -> None:
    if not isinstance(value, Decimal) or not value.is_finite() or value <= 0:
        raise DemoTradeRejected(f"{field} must be a positive finite Decimal")


@dataclass(frozen=True, slots=True)
class DemoExecutionLimits:
    """Frozen per-session limits; the kill switch is enabled by default."""

    fixed_stake: Decimal
    minimum_net_payout_ratio: Decimal
    maximum_contracts: int
    maximum_session_loss: Decimal
    kill_switch_enabled: bool = True

    def __post_init__(self) -> None:
        _positive(self.fixed_stake, "fixed_stake")
        _positive(self.minimum_net_payout_ratio, "minimum_net_payout_ratio")
        _positive(self.maximum_session_loss, "maximum_session_loss")
        if type(self.maximum_contracts) is not int or self.maximum_contracts < 1:
            raise DemoTradeRejected("maximum_contracts must be a positive integer")
        if type(self.kill_switch_enabled) is not bool:
            raise DemoTradeRejected("kill_switch_enabled must be a boolean")


@dataclass(frozen=True, slots=True)
class DemoProposal:
    """Minimal transient economics required to approve one demo purchase."""

    proposal_id: str
    ask_price: Decimal
    payout: Decimal

    def __post_init__(self) -> None:
        if not isinstance(self.proposal_id, str) or not self.proposal_id.strip():
            raise DemoTradeRejected("proposal_id must be non-blank")
        _positive(self.ask_price, "ask_price")
        _positive(self.payout, "payout")
        if self.payout <= self.ask_price:
            raise DemoTradeRejected("payout must exceed ask_price")

    @property
    def net_payout_ratio(self) -> Decimal:
        return (self.payout - self.ask_price) / self.ask_price


@dataclass(frozen=True, slots=True)
class DemoSettlement:
    """Minimal transient result for one settled demo contract."""

    contract_id: str
    profit: Decimal

    def __post_init__(self) -> None:
        if not isinstance(self.contract_id, str) or not self.contract_id.strip():
            raise DemoTradeRejected("contract_id must be non-blank")
        if not isinstance(self.profit, Decimal) or not self.profit.is_finite():
            raise DemoTradeRejected("profit must be a finite Decimal")


@dataclass(frozen=True, slots=True)
class DemoExecutionResult:
    """In-memory result; never suitable for durable evidence or profitability claims."""

    contract_id: str
    profit: Decimal
    net_payout_ratio: Decimal


class DemoExecutionGateway(Protocol):
    """Synchronous port implemented by a demo-only transport adapter."""

    account_type: str

    def propose(self, intent: EnterContractIntent) -> DemoProposal: ...

    def buy(self, proposal: DemoProposal) -> str: ...

    def await_settlement(self, contract_id: str) -> DemoSettlement: ...

    def reconcile(self) -> tuple[str, ...]: ...


class DemoReconciliationGateway(Protocol):
    """Minimal port for state verification over a fresh demo connection."""

    account_type: str

    def reconcile(self) -> tuple[str, ...]: ...


class DemoSession:
    """Bounded transient state with explicit zeroization by reference removal."""

    def __init__(self) -> None:
        self._results: list[DemoExecutionResult] = []

    @property
    def results(self) -> tuple[DemoExecutionResult, ...]:
        return tuple(self._results)

    @property
    def contract_count(self) -> int:
        return len(self._results)

    @property
    def realized_profit(self) -> Decimal:
        return sum((result.profit for result in self._results), start=Decimal("0"))

    @property
    def realized_loss(self) -> Decimal:
        return max(Decimal("0"), -self.realized_profit)

    def record(self, result: DemoExecutionResult) -> None:
        self._results.append(result)

    def clear(self) -> None:
        self._results.clear()


def execute_demo_intent(
    intent: EnterContractIntent,
    *,
    gateway: DemoExecutionGateway,
    reconciliation_gateway: DemoReconciliationGateway | None = None,
    limits: DemoExecutionLimits,
    session: DemoSession,
) -> DemoExecutionResult:
    """Execute exactly one bounded demo intent without blind purchase retries."""
    if limits.kill_switch_enabled:
        raise DemoTradeRejected("kill switch is enabled")
    if gateway.account_type != "demo":
        raise DemoTradeRejected("execution requires a provider-confirmed demo account")
    if reconciliation_gateway is not None and reconciliation_gateway.account_type != "demo":
        raise DemoTradeRejected("reconciliation requires a provider-confirmed demo account")
    if intent.amount_requested != limits.fixed_stake:
        raise DemoTradeRejected("intent amount must equal the fixed stake")
    if session.contract_count >= limits.maximum_contracts:
        raise DemoTradeRejected("session contract limit reached")
    if session.realized_loss + limits.fixed_stake > limits.maximum_session_loss:
        raise DemoTradeRejected("session loss limit would be exceeded")

    proposal = gateway.propose(intent)
    if proposal.ask_price > limits.fixed_stake:
        raise DemoTradeRejected("proposal ask price exceeds the fixed stake")
    if proposal.net_payout_ratio < limits.minimum_net_payout_ratio:
        raise DemoTradeRejected("proposal payout is below the configured minimum")

    try:
        contract_id = gateway.buy(proposal)
    except Exception as error:
        reconciled = (reconciliation_gateway or gateway).reconcile()
        raise AmbiguousDemoExecution(
            f"demo purchase outcome is ambiguous; reconciled {len(reconciled)} open contracts",
            reconciled,
        ) from error

    try:
        settlement = gateway.await_settlement(contract_id)
    except Exception as error:
        reconciled = (reconciliation_gateway or gateway).reconcile()
        raise AmbiguousDemoExecution(
            f"demo settlement is ambiguous; reconciled {len(reconciled)} open contracts",
            reconciled,
        ) from error
    if settlement.contract_id != contract_id:
        reconciled = (reconciliation_gateway or gateway).reconcile()
        raise AmbiguousDemoExecution(
            "settlement contract does not match the purchased contract", reconciled
        )
    result = DemoExecutionResult(
        contract_id=contract_id,
        profit=settlement.profit,
        net_payout_ratio=proposal.net_payout_ratio,
    )
    session.record(result)
    return result
