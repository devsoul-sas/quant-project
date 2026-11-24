"""Causal regime baseline and conservative estimated Multiplier replay."""

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal, localcontext
from itertools import pairwise

from devsoul_quant.domain.contracts import (
    ContractAction,
    ContractType,
    NoTradeIntent,
)
from devsoul_quant.domain.replay import EconomyProvenance, Tick


class InvalidMultiplierPolicy(ValueError):
    """Raised for unsafe or internally inconsistent Multiplier inputs."""


def _positive(value: Decimal, field: str) -> None:
    if not isinstance(value, Decimal) or not value.is_finite() or value <= 0:
        raise InvalidMultiplierPolicy(f"{field} must be a positive finite Decimal")


@dataclass(frozen=True, slots=True)
class MultiplierPolicy:
    """Frozen causal detector and bounded paper-risk parameters.

    ``multiplier`` is a ceiling: the session uses the minimum multiplier the venue
    offers at runtime, and refuses to run when that minimum exceeds this ceiling.
    """

    lookback_ticks: int
    minimum_absolute_return: Decimal
    minimum_directional_consistency: Decimal
    multiplier: Decimal
    stake: Decimal
    stop_loss: Decimal
    take_profit: Decimal
    maximum_holding_ticks: int

    def __post_init__(self) -> None:
        if type(self.lookback_ticks) is not int or self.lookback_ticks < 2:
            raise InvalidMultiplierPolicy("lookback_ticks must be an integer of at least 2")
        if type(self.maximum_holding_ticks) is not int or self.maximum_holding_ticks < 1:
            raise InvalidMultiplierPolicy("maximum_holding_ticks must be positive")
        for field in (
            "minimum_absolute_return",
            "multiplier",
            "stake",
            "stop_loss",
            "take_profit",
        ):
            _positive(getattr(self, field), field)
        consistency = self.minimum_directional_consistency
        if (
            not isinstance(consistency, Decimal)
            or not consistency.is_finite()
            or consistency <= Decimal("0.5")
            or consistency > Decimal("1")
        ):
            raise InvalidMultiplierPolicy("minimum_directional_consistency must be in (0.5, 1]")
        if self.stop_loss > self.stake:
            raise InvalidMultiplierPolicy("stop_loss cannot exceed stake")


@dataclass(frozen=True, slots=True)
class MultiplierIntent:
    """Paper-only directional Multiplier intent with bounded exits."""

    symbol: str
    contract_type: ContractType
    stake: Decimal
    multiplier: Decimal
    stop_loss: Decimal
    take_profit: Decimal
    maximum_holding_ticks: int
    strategy_reason: str

    def __post_init__(self) -> None:
        if not isinstance(self.symbol, str) or not self.symbol.strip():
            raise InvalidMultiplierPolicy("symbol must be non-blank")
        if self.contract_type not in (ContractType.MULTUP, ContractType.MULTDOWN):
            raise InvalidMultiplierPolicy("contract_type must be MULTUP or MULTDOWN")
        for field in ("stake", "multiplier", "stop_loss", "take_profit"):
            _positive(getattr(self, field), field)
        if self.stop_loss > self.stake:
            raise InvalidMultiplierPolicy("stop_loss cannot exceed stake")
        if type(self.maximum_holding_ticks) is not int or self.maximum_holding_ticks < 1:
            raise InvalidMultiplierPolicy("maximum_holding_ticks must be positive")
        if not isinstance(self.strategy_reason, str) or not self.strategy_reason.strip():
            raise InvalidMultiplierPolicy("strategy_reason must be non-blank")


@dataclass(frozen=True, slots=True)
class MultiplierReplayResult:
    """Estimated P&L; never equivalent to provider-observed settlement."""

    profit: Decimal
    economy: EconomyProvenance
    entry_tick: Tick
    exit_tick: Tick


def decide_multiplier(
    *,
    history: Sequence[Tick],
    symbol: str,
    policy: MultiplierPolicy,
) -> MultiplierIntent | NoTradeIntent:
    """Detect a simple directionally consistent regime from past ticks only."""
    if len(history) < policy.lookback_ticks:
        return NoTradeIntent(
            action=ContractAction.NO_TRADE,
            strategy_reason="insufficient Multiplier warm-up sample",
        )
    window = history[-policy.lookback_ticks :]
    if any(right.epoch <= left.epoch for left, right in pairwise(window)):
        raise InvalidMultiplierPolicy("tick epochs must be strictly increasing")
    start = window[0].quote
    if start == 0:
        raise InvalidMultiplierPolicy("entry quote cannot be zero")
    with localcontext() as context:
        context.prec = 28
        total_return = (window[-1].quote - start) / start
        if abs(total_return) < policy.minimum_absolute_return:
            return NoTradeIntent(
                action=ContractAction.NO_TRADE,
                strategy_reason="absolute return is below the frozen regime threshold",
            )
        direction = Decimal("1") if total_return > 0 else Decimal("-1")
        aligned = sum(
            1 for left, right in pairwise(window) if (right.quote - left.quote) * direction > 0
        )
        consistency = Decimal(aligned) / Decimal(len(window) - 1)
    if consistency < policy.minimum_directional_consistency:
        return NoTradeIntent(
            action=ContractAction.NO_TRADE,
            strategy_reason="directional consistency is below the frozen regime threshold",
        )
    return MultiplierIntent(
        symbol=symbol,
        contract_type=(ContractType.MULTUP if total_return > 0 else ContractType.MULTDOWN),
        stake=policy.stake,
        multiplier=policy.multiplier,
        stop_loss=policy.stop_loss,
        take_profit=policy.take_profit,
        maximum_holding_ticks=policy.maximum_holding_ticks,
        strategy_reason="causal return and directional-consistency regime",
    )


def replay_multiplier_estimate(
    intent: MultiplierIntent,
    *,
    entry_tick: Tick,
    exit_tick: Tick,
    observed_commission: Decimal,
) -> MultiplierReplayResult:
    """Estimate bounded P&L using documented linear multiplier semantics."""
    if exit_tick.epoch <= entry_tick.epoch:
        raise InvalidMultiplierPolicy("exit tick must be later than entry tick")
    if entry_tick.quote == 0:
        raise InvalidMultiplierPolicy("entry quote cannot be zero")
    if (
        not isinstance(observed_commission, Decimal)
        or not observed_commission.is_finite()
        or observed_commission < 0
    ):
        raise InvalidMultiplierPolicy("observed_commission must be non-negative")
    direction = Decimal("1") if intent.contract_type is ContractType.MULTUP else Decimal("-1")
    with localcontext() as context:
        context.prec = 28
        movement = (exit_tick.quote - entry_tick.quote) / entry_tick.quote
        raw_profit = intent.stake * intent.multiplier * movement * direction
        net_profit = raw_profit - observed_commission
        profit = min(intent.take_profit, max(-intent.stop_loss, net_profit))
    return MultiplierReplayResult(
        profit=profit,
        economy=EconomyProvenance.ESTIMATED,
        entry_tick=entry_tick,
        exit_tick=exit_tick,
    )
