"""Bounded, local and ephemeral autonomous Deriv demo runner.

The runner keeps NO_TRADE as its default, never exposes a real-money mode, uses
fresh demo URLs for independent connections, and returns only in-memory session
state. Callers are responsible for discarding the returned snapshot after use.
"""

from __future__ import annotations

import random
import time
from collections.abc import Callable, Sequence
from contextlib import AbstractContextManager
from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from typing import Protocol

from devsoul_quant.application.adaptive_shadow import (
    AdaptiveEvaluationSnapshot,
    AdaptivePrequentialEvaluator,
)
from devsoul_quant.application.demo_execution import (
    AmbiguousDemoExecution,
    DemoExecutionGateway,
    DemoExecutionLimits,
    DemoSession,
    execute_demo_intent,
)
from devsoul_quant.domain.contracts import (
    Basis,
    ContractAction,
    ContractType,
    DurationUnit,
    EnterContractIntent,
    ExitPolicy,
    NoTradeIntent,
)
from devsoul_quant.domain.demo_gates import evaluate_risk_gate
from devsoul_quant.domain.digit_strategy import (
    DigitDecisionPolicy,
    DigitEconomics,
    digit_parity_decision,
    last_digit,
)
from devsoul_quant.domain.execution_mode import ExecutionMode
from devsoul_quant.domain.replay import Tick
from devsoul_quant.domain.strategy import momentum_decision


class InvalidAutonomousDemo(ValueError):
    """Raised when autonomous demo configuration is not fail-closed."""


class DemoStrategy(StrEnum):
    """Only the experimental strategies approved for S3.6."""

    EVEN_ODD = "EVEN_ODD"
    MOMENTUM = "MOMENTUM"
    CONTROLLED_RANDOM = "CONTROLLED_RANDOM"
    ADAPTIVE_ENSEMBLE = "ADAPTIVE_ENSEMBLE"


_ALLOWED_MODES = frozenset(
    {
        ExecutionMode.OBSERVE_ONLY,
        ExecutionMode.SHADOW_TRADING,
        ExecutionMode.DEMO_INTEGRATION,
        ExecutionMode.DEMO_EXPLORATORY,
    }
)
_DEMO_EXECUTION_MODES = frozenset({ExecutionMode.DEMO_INTEGRATION, ExecutionMode.DEMO_EXPLORATORY})


@dataclass(frozen=True, slots=True)
class AutonomousDemoConfig:
    """Prospective local runner settings with an explicit operation bound."""

    mode: ExecutionMode
    symbol: str
    strategy: DemoStrategy
    session_seconds: int
    ticks_per_cycle: int
    contract_duration: int
    maximum_cycles: int
    experimental_budget: Decimal = Decimal("2")
    seed: int = 42
    armed: bool = False

    def __post_init__(self) -> None:
        if self.mode not in _ALLOWED_MODES:
            raise InvalidAutonomousDemo("mode is not available to the autonomous demo runner")
        if not isinstance(self.symbol, str) or not self.symbol.strip():
            raise InvalidAutonomousDemo("symbol must be a non-blank string")
        if not isinstance(self.strategy, DemoStrategy):
            raise InvalidAutonomousDemo("strategy must be a DemoStrategy")
        for name, value in (
            ("session_seconds", self.session_seconds),
            ("ticks_per_cycle", self.ticks_per_cycle),
            ("contract_duration", self.contract_duration),
            ("maximum_cycles", self.maximum_cycles),
        ):
            if type(value) is not int or value < 1:
                raise InvalidAutonomousDemo(f"{name} must be a positive integer")
        if self.session_seconds >= 86_400:
            raise InvalidAutonomousDemo("session_seconds must remain strictly below 24 hours")
        if self.ticks_per_cycle > 10_000:
            raise InvalidAutonomousDemo("ticks_per_cycle must be at most 10000")
        if (
            not isinstance(self.experimental_budget, Decimal)
            or not self.experimental_budget.is_finite()
            or self.experimental_budget <= 0
            or self.experimental_budget > Decimal("100")
        ):
            raise InvalidAutonomousDemo(
                "experimental_budget must be a positive finite Decimal at most 100"
            )
        if type(self.seed) is not int:
            raise InvalidAutonomousDemo("seed must be an integer")
        if type(self.armed) is not bool:
            raise InvalidAutonomousDemo("armed must be a boolean")
        if self.strategy is DemoStrategy.ADAPTIVE_ENSEMBLE and (
            self.mode is not ExecutionMode.SHADOW_TRADING
            or self.symbol != "R_10"
            or self.contract_duration != 1
            or self.armed
        ):
            raise InvalidAutonomousDemo(
                "ADAPTIVE_ENSEMBLE requires unarmed R_10 SHADOW_TRADING with one-tick horizon"
            )


@dataclass(frozen=True, slots=True)
class ContractEconomicMetrics:
    """Transient observed economics for one provider contract type."""

    contract_type: str
    operations: int
    wins: int
    losses: int
    stakes: Decimal
    effective_net_payout: Decimal
    break_even: Decimal
    estimated_probability: Decimal | None
    estimated_value: Decimal | None
    gross_profit: Decimal
    gross_loss: Decimal
    net_profit: Decimal
    profit_factor: Decimal | None
    roi_on_stakes: Decimal


@dataclass(frozen=True, slots=True)
class EconomicMetrics:
    """Transient campaign economics computed only from observed proposals."""

    decisions: int
    abstentions: int
    abstention_frequency: Decimal | None
    wins: int
    losses: int
    stakes: Decimal
    effective_net_payout: Decimal | None
    break_even: Decimal | None
    estimated_probability: Decimal | None
    estimated_value: Decimal | None
    gross_profit: Decimal
    gross_loss: Decimal
    net_profit: Decimal
    profit_factor: Decimal | None
    roi_on_stakes: Decimal | None
    by_contract_type: tuple[ContractEconomicMetrics, ...]


@dataclass(frozen=True, slots=True)
class _EconomicObservation:
    contract_type: str
    stake: Decimal
    profit: Decimal
    net_payout_ratio: Decimal
    estimated_probability: Decimal | None


def _contract_metrics(
    contract_type: str, observations: Sequence[_EconomicObservation]
) -> ContractEconomicMetrics:
    count = len(observations)
    count_decimal = Decimal(count)
    stakes = sum((item.stake for item in observations), start=Decimal("0"))
    gross_profit = sum(
        (item.profit for item in observations if item.profit > 0), start=Decimal("0")
    )
    gross_loss = sum((-item.profit for item in observations if item.profit < 0), start=Decimal("0"))
    net_profit = gross_profit - gross_loss
    probabilities = tuple(
        item.estimated_probability
        for item in observations
        if item.estimated_probability is not None
    )
    estimated_probability = (
        sum(probabilities, start=Decimal("0")) / count_decimal
        if len(probabilities) == count
        else None
    )
    estimated_value = (
        sum(
            (
                item.estimated_probability * item.net_payout_ratio
                - (Decimal("1") - item.estimated_probability)
                for item in observations
                if item.estimated_probability is not None
            ),
            start=Decimal("0"),
        )
        / count_decimal
        if estimated_probability is not None
        else None
    )
    return ContractEconomicMetrics(
        contract_type=contract_type,
        operations=count,
        wins=sum(item.profit > 0 for item in observations),
        losses=sum(item.profit <= 0 for item in observations),
        stakes=stakes,
        effective_net_payout=(
            sum((item.net_payout_ratio for item in observations), start=Decimal("0"))
            / count_decimal
        ),
        break_even=(
            sum(
                (Decimal("1") / (Decimal("1") + item.net_payout_ratio) for item in observations),
                start=Decimal("0"),
            )
            / count_decimal
        ),
        estimated_probability=estimated_probability,
        estimated_value=estimated_value,
        gross_profit=gross_profit,
        gross_loss=gross_loss,
        net_profit=net_profit,
        profit_factor=gross_profit / gross_loss if gross_loss else None,
        roi_on_stakes=net_profit / stakes,
    )


def _economic_metrics(
    observations: Sequence[_EconomicObservation], *, decisions: int, abstentions: int
) -> EconomicMetrics:
    grouped: dict[str, list[_EconomicObservation]] = {}
    for observation in observations:
        grouped.setdefault(observation.contract_type, []).append(observation)
    breakdowns = tuple(
        _contract_metrics(contract_type, items) for contract_type, items in grouped.items()
    )
    if not observations:
        return EconomicMetrics(
            decisions=decisions,
            abstentions=abstentions,
            abstention_frequency=(Decimal(abstentions) / Decimal(decisions) if decisions else None),
            wins=0,
            losses=0,
            stakes=Decimal("0"),
            effective_net_payout=None,
            break_even=None,
            estimated_probability=None,
            estimated_value=None,
            gross_profit=Decimal("0"),
            gross_loss=Decimal("0"),
            net_profit=Decimal("0"),
            profit_factor=None,
            roi_on_stakes=None,
            by_contract_type=(),
        )
    combined = _contract_metrics("ALL", observations)
    return EconomicMetrics(
        decisions=decisions,
        abstentions=abstentions,
        abstention_frequency=Decimal(abstentions) / Decimal(decisions),
        wins=combined.wins,
        losses=combined.losses,
        stakes=combined.stakes,
        effective_net_payout=combined.effective_net_payout,
        break_even=combined.break_even,
        estimated_probability=combined.estimated_probability,
        estimated_value=combined.estimated_value,
        gross_profit=combined.gross_profit,
        gross_loss=combined.gross_loss,
        net_profit=combined.net_profit,
        profit_factor=combined.profit_factor,
        roi_on_stakes=combined.roi_on_stakes,
        by_contract_type=breakdowns,
    )


@dataclass(frozen=True, slots=True)
class AutonomousDemoSnapshot:
    """Ephemeral operational metrics suitable for a local terminal display."""

    connection_state: str
    instrument: str
    strategy: str
    ticks_processed: int
    signal: str
    virtual_balance: Decimal
    open_contracts: int
    settled_contracts: int
    quotes_consulted: int
    profit_loss: Decimal
    win_rate: Decimal | None
    break_even: Decimal | None
    drawdown: Decimal
    risk_state: str
    elapsed_seconds: Decimal
    abstention_reasons: tuple[str, ...]
    experimental_budget: Decimal
    budget_used: Decimal
    budget_remaining: Decimal
    economics: EconomicMetrics
    adaptive: AdaptiveEvaluationSnapshot | None = None


@dataclass(frozen=True, slots=True)
class AutonomousDemoResult:
    """Transient result classified by capability, never by profitability."""

    classification: str
    final: AutonomousDemoSnapshot


class AutonomousGateway(DemoExecutionGateway, Protocol):
    """Demo gateway capabilities needed by the runner."""

    def available_contract_types(self, symbol: str) -> frozenset[str]: ...


GatewayContext = AbstractContextManager[AutonomousGateway]


class _FreshReconciler:
    account_type = "demo"

    def __init__(
        self,
        resolve_url: Callable[[], str],
        gateway_factory: Callable[[str], GatewayContext],
    ) -> None:
        self._resolve_url = resolve_url
        self._gateway_factory = gateway_factory

    def reconcile(self) -> tuple[str, ...]:
        with self._gateway_factory(self._resolve_url()) as gateway:
            return gateway.reconcile()


def _intent(
    *,
    symbol: str,
    contract_type: ContractType,
    duration: int,
    stake: Decimal,
    reason: str,
) -> EnterContractIntent:
    return EnterContractIntent(
        action=ContractAction.ENTER_CONTRACT,
        symbol=symbol,
        contract_type=contract_type,
        duration=duration,
        duration_unit=DurationUnit.TICKS,
        basis=Basis.STAKE,
        amount_requested=stake,
        currency="USD",
        barrier=None,
        exit_policy=ExitPolicy.EXPIRY,
        strategy_reason=reason,
    )


def _controlled_random_intent(
    config: AutonomousDemoConfig,
    limits: DemoExecutionLimits,
    operation_index: int,
) -> EnterContractIntent:
    generator = random.Random(config.seed + operation_index)
    family = operation_index % 2
    choices = (
        (ContractType.DIGITEVEN, ContractType.DIGITODD)
        if family == 0
        else (ContractType.CALL, ContractType.PUT)
    )
    return _intent(
        symbol=config.symbol,
        contract_type=generator.choice(choices),
        duration=config.contract_duration,
        stake=limits.fixed_stake,
        reason="controlled random integration baseline",
    )


def _parity_decision(
    *,
    config: AutonomousDemoConfig,
    limits: DemoExecutionLimits,
    history: Sequence[Tick],
    resolve_url: Callable[[], str],
    gateway_factory: Callable[[str], GatewayContext],
) -> tuple[EnterContractIntent | NoTradeIntent, int, Decimal | None, Decimal | None]:
    even_intent = _intent(
        symbol=config.symbol,
        contract_type=ContractType.DIGITEVEN,
        duration=1,
        stake=limits.fixed_stake,
        reason="Even quote for prospective parity decision",
    )
    odd_intent = _intent(
        symbol=config.symbol,
        contract_type=ContractType.DIGITODD,
        duration=1,
        stake=limits.fixed_stake,
        reason="Odd quote for prospective parity decision",
    )
    with gateway_factory(resolve_url()) as gateway:
        available = gateway.available_contract_types(config.symbol)
        if not {ContractType.DIGITEVEN.value, ContractType.DIGITODD.value}.issubset(available):
            return (
                NoTradeIntent(
                    action=ContractAction.NO_TRADE,
                    strategy_reason="Even/Odd contracts are unavailable",
                ),
                0,
                None,
                None,
            )
        even = gateway.propose(even_intent)
        odd = gateway.propose(odd_intent)
    decision = digit_parity_decision(
        history=history,
        even_economics=DigitEconomics.even(ask_price=even.ask_price, payout=even.payout),
        odd_economics=DigitEconomics.odd(ask_price=odd.ask_price, payout=odd.payout),
        policy=DigitDecisionPolicy(
            min_samples=config.ticks_per_cycle,
            z_score=Decimal("2.576"),
            min_edge_probability=Decimal("0"),
        ),
        amount_requested=limits.fixed_stake,
        symbol=config.symbol,
    )
    selected = even if getattr(decision, "contract_type", None) is ContractType.DIGITEVEN else odd
    estimated_probability: Decimal | None = None
    if isinstance(decision, EnterContractIntent):
        selected_even = decision.contract_type is ContractType.DIGITEVEN
        selected_count = sum((last_digit(tick) % 2 == 0) is selected_even for tick in history)
        estimated_probability = Decimal(selected_count) / Decimal(len(history))
    return decision, 2, selected.ask_price / selected.payout, estimated_probability


def _decision(
    *,
    config: AutonomousDemoConfig,
    limits: DemoExecutionLimits,
    history: Sequence[Tick],
    operation_index: int,
    resolve_url: Callable[[], str],
    gateway_factory: Callable[[str], GatewayContext],
) -> tuple[EnterContractIntent | NoTradeIntent, int, Decimal | None, Decimal | None]:
    if config.strategy is DemoStrategy.CONTROLLED_RANDOM:
        return (
            _controlled_random_intent(config, limits, operation_index),
            0,
            None,
            Decimal("0.5"),
        )
    if config.strategy is DemoStrategy.MOMENTUM:
        return (
            momentum_decision(
                history=history,
                duration=config.contract_duration,
                amount_requested=limits.fixed_stake,
                symbol=config.symbol,
            ),
            0,
            None,
            None,
        )
    return _parity_decision(
        config=config,
        limits=limits,
        history=history,
        resolve_url=resolve_url,
        gateway_factory=gateway_factory,
    )


def _classification(mode: ExecutionMode) -> str:
    if mode is ExecutionMode.OBSERVE_ONLY:
        return "OBSERVATION_ONLY"
    if mode is ExecutionMode.SHADOW_TRADING:
        return "SHADOW_ONLY"
    if mode is ExecutionMode.DEMO_INTEGRATION:
        return "INTEGRATION_TEST"
    return "DEMO_EXPLORATORY"


def run_autonomous_demo(
    *,
    config: AutonomousDemoConfig,
    limits: DemoExecutionLimits,
    collect_ticks: Callable[[str, int], Sequence[Tick]],
    resolve_url: Callable[[], str],
    gateway_factory: Callable[[str], GatewayContext],
    emit: Callable[[AutonomousDemoSnapshot], None] | None = None,
    monotonic: Callable[[], float] = time.monotonic,
) -> AutonomousDemoResult:
    """Run a bounded local demo loop and stop on limits or ambiguity."""
    started = monotonic()
    history: list[Tick] = []
    session = DemoSession()
    signal = "NO_TRADE"
    settled = wins = quotes = decisions = abstentions = 0
    profit = peak = drawdown = Decimal("0")
    break_even: Decimal | None = None
    open_contracts = 0
    reasons: list[str] = []
    budget_used = Decimal("0")
    economic_observations: list[_EconomicObservation] = []
    adaptive_evaluator = (
        AdaptivePrequentialEvaluator(warmup_labels=120, seed=config.seed)
        if config.strategy is DemoStrategy.ADAPTIVE_ENSEMBLE
        else None
    )
    sink = emit if emit is not None else lambda snapshot: None

    def snapshot(
        connection_state: str, *, finalize_adaptive: bool = False
    ) -> AutonomousDemoSnapshot:
        win_rate = Decimal(wins) / Decimal(settled) if settled else None
        risk = evaluate_risk_gate(
            demo_account_confirmed=True,
            real_money_used=False,
            fixed_stake=limits.fixed_stake,
            maximum_stake=limits.fixed_stake,
            contracts_executed=settled,
            maximum_contracts=limits.maximum_contracts,
            open_contracts=open_contracts,
            maximum_open_contracts=1,
            realized_loss=max(Decimal("0"), -profit),
            maximum_loss=limits.maximum_session_loss,
        )
        return AutonomousDemoSnapshot(
            connection_state=connection_state,
            instrument=config.symbol,
            strategy=config.strategy.value,
            ticks_processed=len(history),
            signal=signal,
            virtual_balance=profit,
            open_contracts=open_contracts,
            settled_contracts=settled,
            quotes_consulted=quotes,
            profit_loss=profit,
            win_rate=win_rate,
            break_even=break_even,
            drawdown=drawdown,
            risk_state=risk.status.value,
            elapsed_seconds=Decimal(str(max(0.0, monotonic() - started))),
            abstention_reasons=tuple(dict.fromkeys(reasons + list(risk.reasons))),
            experimental_budget=config.experimental_budget,
            budget_used=budget_used,
            budget_remaining=max(Decimal("0"), config.experimental_budget - budget_used),
            economics=_economic_metrics(
                economic_observations,
                decisions=decisions,
                abstentions=abstentions,
            ),
            adaptive=(
                (
                    adaptive_evaluator.final_snapshot()
                    if finalize_adaptive
                    else adaptive_evaluator.snapshot()
                )
                if adaptive_evaluator is not None
                else None
            ),
        )

    try:
        if config.mode in _DEMO_EXECUTION_MODES and not config.armed:
            reasons.append("DEMO_EXECUTION_NOT_ARMED")
            final = snapshot("DISCONNECTED")
            sink(final)
            return AutonomousDemoResult(_classification(config.mode), final)

        for _cycle in range(config.maximum_cycles):
            if monotonic() - started >= config.session_seconds:
                reasons.append("SESSION_DURATION_REACHED")
                break
            batch = tuple(collect_ticks(config.symbol, config.ticks_per_cycle))
            if not batch:
                reasons.append("TICK_SOURCE_EXHAUSTED")
                break
            newest_epoch = history[-1].epoch if history else None
            fresh = tuple(
                tick for tick in batch if newest_epoch is None or tick.epoch > newest_epoch
            )
            if not fresh:
                reasons.append("NO_STRICTLY_NEW_TICKS")
                break
            history.extend(fresh)
            adaptive_prediction = None
            if adaptive_evaluator is not None:
                for tick in fresh:
                    adaptive_prediction = adaptive_evaluator.observe(tick)
            sink(snapshot("CONNECTED"))

            if config.mode is ExecutionMode.OBSERVE_ONLY:
                continue
            if adaptive_evaluator is not None:
                if adaptive_prediction is None:
                    signal = "NO_TRADE"
                    reasons.append("ADAPTIVE_FEATURE_WARMUP")
                    sink(snapshot("DISCONNECTED"))
                    continue
                call_intent = _intent(
                    symbol=config.symbol,
                    contract_type=ContractType.CALL,
                    duration=1,
                    stake=limits.fixed_stake,
                    reason="S3.8 ephemeral adaptive CALL quote",
                )
                put_intent = _intent(
                    symbol=config.symbol,
                    contract_type=ContractType.PUT,
                    duration=1,
                    stake=limits.fixed_stake,
                    reason="S3.8 ephemeral adaptive PUT quote",
                )
                with gateway_factory(resolve_url()) as gateway:
                    available = gateway.available_contract_types(config.symbol)
                    if not {ContractType.CALL.value, ContractType.PUT.value}.issubset(available):
                        signal = "NO_TRADE"
                        reasons.append("RISE_FALL_CONTRACTS_UNAVAILABLE")
                        sink(snapshot("DISCONNECTED"))
                        continue
                    call_proposal = gateway.propose(call_intent)
                    put_proposal = gateway.propose(put_intent)
                quotes += 2
                call_break_even = call_proposal.ask_price / call_proposal.payout
                put_break_even = put_proposal.ask_price / put_proposal.payout
                adaptive_evaluator.observe_quotes(
                    adaptive_prediction,
                    call_break_even=call_break_even,
                    put_break_even=put_break_even,
                )
                logistic_probability = adaptive_prediction.probability("LOGISTIC")
                signal = "CALL" if logistic_probability >= Decimal("0.5") else "PUT"
                break_even = call_break_even if signal == "CALL" else put_break_even
                sink(snapshot("DISCONNECTED"))
                continue
            decision, decision_quotes, decision_break_even, estimated_probability = _decision(
                config=config,
                limits=limits,
                history=history,
                operation_index=settled,
                resolve_url=resolve_url,
                gateway_factory=gateway_factory,
            )
            decisions += 1
            quotes += decision_quotes
            if decision_break_even is not None:
                break_even = decision_break_even
            if isinstance(decision, NoTradeIntent):
                signal = "NO_TRADE"
                abstentions += 1
                reasons.append(decision.strategy_reason)
                sink(snapshot("DISCONNECTED"))
                continue
            signal = decision.contract_type.value

            if config.mode is ExecutionMode.SHADOW_TRADING:
                with gateway_factory(resolve_url()) as gateway:
                    available = gateway.available_contract_types(config.symbol)
                    if decision.contract_type.value not in available:
                        signal = "NO_TRADE"
                        abstentions += 1
                        reasons.append("CONTRACT_TYPE_UNAVAILABLE")
                        continue
                    proposal = gateway.propose(decision)
                quotes += 1
                break_even = proposal.ask_price / proposal.payout
                sink(snapshot("DISCONNECTED"))
                continue

            if settled >= limits.maximum_contracts:
                reasons.append("CONTRACT_LIMIT_REACHED")
                break
            if budget_used + limits.fixed_stake > config.experimental_budget:
                reasons.append("EXPERIMENTAL_BUDGET_EXHAUSTED")
                break
            reconciler = _FreshReconciler(resolve_url, gateway_factory)
            try:
                with gateway_factory(resolve_url()) as gateway:
                    available = gateway.available_contract_types(config.symbol)
                    if decision.contract_type.value not in available:
                        signal = "NO_TRADE"
                        abstentions += 1
                        reasons.append("CONTRACT_TYPE_UNAVAILABLE")
                        continue
                    result = execute_demo_intent(
                        decision,
                        gateway=gateway,
                        reconciliation_gateway=reconciler,
                        limits=limits,
                        session=session,
                    )
            except AmbiguousDemoExecution as error:
                budget_used += limits.fixed_stake
                open_contracts = len(error.open_contract_ids)
                signal = "NO_TRADE"
                reasons.append("AMBIGUOUS_DEMO_EXECUTION")
                break
            settled += 1
            budget_used += limits.fixed_stake
            quotes += 1
            profit += result.profit
            economic_observations.append(
                _EconomicObservation(
                    contract_type=decision.contract_type.value,
                    stake=limits.fixed_stake,
                    profit=result.profit,
                    net_payout_ratio=result.net_payout_ratio,
                    estimated_probability=estimated_probability,
                )
            )
            if result.profit > 0:
                wins += 1
            peak = max(peak, profit)
            drawdown = max(drawdown, peak - profit)
            break_even = Decimal("1") / (Decimal("1") + result.net_payout_ratio)
            sink(snapshot("DISCONNECTED"))
            if settled >= limits.maximum_contracts:
                reasons.append("CONTRACT_LIMIT_REACHED")
                break
            if budget_used + limits.fixed_stake > config.experimental_budget:
                reasons.append("EXPERIMENTAL_BUDGET_EXHAUSTED")
                break
            if max(Decimal("0"), -profit) >= limits.maximum_session_loss:
                reasons.append("LOSS_LIMIT_REACHED")
                break

        if config.mode in _DEMO_EXECUTION_MODES and config.armed:
            open_contracts = len(_FreshReconciler(resolve_url, gateway_factory).reconcile())
            if open_contracts:
                reasons.append("OPEN_CONTRACTS_REMAIN")
        final = snapshot("DISCONNECTED", finalize_adaptive=True)
        sink(final)
        return AutonomousDemoResult(_classification(config.mode), final)
    finally:
        session.clear()
        history.clear()
        economic_observations.clear()
        if adaptive_evaluator is not None:
            adaptive_evaluator.clear()
