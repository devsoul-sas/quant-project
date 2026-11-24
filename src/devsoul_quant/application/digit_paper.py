"""Ephemeral in-memory simulation for one causal Even/Odd decision."""

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol

from devsoul_quant.application.demo_execution import DemoProposal
from devsoul_quant.domain.contracts import (
    Basis,
    ContractAction,
    ContractType,
    DurationUnit,
    EnterContractIntent,
    ExitPolicy,
    NoTradeIntent,
)
from devsoul_quant.domain.digit_replay import replay_digit
from devsoul_quant.domain.digit_strategy import (
    DigitDecisionPolicy,
    DigitEconomics,
    digit_parity_decision,
)
from devsoul_quant.domain.replay import EconomyProvenance, Outcome, Tick


class UnsupportedDigitContracts(ValueError):
    """Raised when runtime discovery cannot prove both parity contracts exist."""


class DigitProposalGateway(Protocol):
    """Read-only discovery and proposal port for ephemeral digit economics."""

    def available_contract_types(self, symbol: str) -> frozenset[str]: ...

    def propose(self, intent: EnterContractIntent) -> DemoProposal: ...


def _digit_intent(
    contract_type: ContractType,
    *,
    symbol: str,
    amount_requested: Decimal,
) -> EnterContractIntent:
    return EnterContractIntent(
        action=ContractAction.ENTER_CONTRACT,
        symbol=symbol,
        contract_type=contract_type,
        duration=1,
        duration_unit=DurationUnit.TICKS,
        basis=Basis.STAKE,
        amount_requested=amount_requested,
        currency="USD",
        barrier=None,
        exit_policy=ExitPolicy.EXPIRY,
        strategy_reason="observe parity economics without purchase",
    )


def observe_digit_economics(
    *,
    gateway: DigitProposalGateway,
    symbol: str,
    amount_requested: Decimal,
) -> tuple[DigitEconomics, DigitEconomics]:
    """Quote both parity sides after fail-closed runtime contract discovery."""
    available = gateway.available_contract_types(symbol)
    required = {ContractType.DIGITEVEN.value, ContractType.DIGITODD.value}
    missing = required - available
    if missing:
        raise UnsupportedDigitContracts(
            f"symbol lacks required contracts: {', '.join(sorted(missing))}"
        )
    even = gateway.propose(
        _digit_intent(
            ContractType.DIGITEVEN,
            symbol=symbol,
            amount_requested=amount_requested,
        )
    )
    odd = gateway.propose(
        _digit_intent(
            ContractType.DIGITODD,
            symbol=symbol,
            amount_requested=amount_requested,
        )
    )
    return (
        DigitEconomics.even(ask_price=even.ask_price, payout=even.payout),
        DigitEconomics.odd(ask_price=odd.ask_price, payout=odd.payout),
    )


@dataclass(frozen=True, slots=True)
class DigitPaperResult:
    """Transient decision and observed-economy paper outcome."""

    decision: EnterContractIntent | NoTradeIntent
    outcome: Outcome | None
    profit: Decimal | None
    economy: EconomyProvenance


def simulate_digit_decision(
    *,
    history: Sequence[Tick],
    settlement_tick: Tick,
    even_economics: DigitEconomics,
    odd_economics: DigitEconomics,
    policy: DigitDecisionPolicy,
    amount_requested: Decimal,
    symbol: str,
) -> DigitPaperResult:
    """Decide from history only, then settle against one unseen tick."""
    decision = digit_parity_decision(
        history=history,
        even_economics=even_economics,
        odd_economics=odd_economics,
        policy=policy,
        amount_requested=amount_requested,
        symbol=symbol,
    )
    if isinstance(decision, NoTradeIntent):
        return DigitPaperResult(
            decision=decision,
            outcome=None,
            profit=None,
            economy=EconomyProvenance.OBSERVED,
        )

    selected = even_economics if decision.contract_type is ContractType.DIGITEVEN else odd_economics
    replay = replay_digit(
        decision,
        (history[-1], settlement_tick),
        economy=EconomyProvenance.OBSERVED,
    )
    profit = (
        selected.payout - selected.ask_price
        if replay.outcome is Outcome.WIN
        else -selected.ask_price
    )
    return DigitPaperResult(
        decision=decision,
        outcome=replay.outcome,
        profit=profit,
        economy=replay.economy,
    )
