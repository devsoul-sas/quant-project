"""Non-economic target-before-stop outcomes for synthetic Multiplier research.

The barriers are relative quote movements, not provider contract prices, payout,
commission or monetary P&L. Results therefore remain tick-proxy evidence only.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Context, Decimal, localcontext
from enum import StrEnum
from itertools import pairwise

from devsoul_quant.domain.decision import DecisionAction
from devsoul_quant.domain.replay import Tick

_DECIMAL_CONTEXT = Context(prec=50)


class InvalidDirectionalOutcome(ValueError):
    """Raised when a directional outcome cannot be settled safely."""


class DirectionalOutcome(StrEnum):
    """First directional barrier reached within the frozen horizon."""

    TARGET = "TARGET"
    STOP = "STOP"
    TIMEOUT = "TIMEOUT"


@dataclass(frozen=True, slots=True)
class DirectionalBarrierPolicy:
    """Frozen quote-return barriers and maximum settlement horizon."""

    target_return: Decimal
    stop_return: Decimal
    maximum_holding_ticks: int

    def __post_init__(self) -> None:
        for field in ("target_return", "stop_return"):
            value = getattr(self, field)
            if not isinstance(value, Decimal) or not value.is_finite() or value <= 0:
                raise InvalidDirectionalOutcome(f"{field} must be a positive finite Decimal")
        if type(self.maximum_holding_ticks) is not int or self.maximum_holding_ticks < 1:
            raise InvalidDirectionalOutcome("maximum_holding_ticks must be a positive integer")


@dataclass(frozen=True, slots=True)
class DirectionalSettlement:
    """Path-dependent directional result with no economic interpretation."""

    outcome: DirectionalOutcome
    holding_ticks: int
    terminal_tick: Tick
    directional_return: Decimal


def settle_directional_outcome(
    *,
    action: DecisionAction,
    entry_tick: Tick,
    future_ticks: Sequence[Tick],
    policy: DirectionalBarrierPolicy,
) -> DirectionalSettlement:
    """Settle the first relative quote barrier after the causal entry tick."""
    if action not in (DecisionAction.MULTUP, DecisionAction.MULTDOWN):
        raise InvalidDirectionalOutcome("action must be MULTUP or MULTDOWN")
    horizon = tuple(future_ticks[: policy.maximum_holding_ticks])
    if len(horizon) < policy.maximum_holding_ticks:
        raise InvalidDirectionalOutcome("future ticks must cover maximum_holding_ticks")
    ordered = (entry_tick, *horizon)
    if any(right.epoch <= left.epoch for left, right in pairwise(ordered)):
        raise InvalidDirectionalOutcome("ticks must be strictly increasing after entry")

    direction = Decimal(1) if action is DecisionAction.MULTUP else Decimal(-1)
    with localcontext(_DECIMAL_CONTEXT):
        for holding_ticks, tick in enumerate(horizon, start=1):
            movement = ((tick.quote - entry_tick.quote) / entry_tick.quote) * direction
            if movement >= policy.target_return:
                return DirectionalSettlement(
                    DirectionalOutcome.TARGET, holding_ticks, tick, movement
                )
            if movement <= -policy.stop_return:
                return DirectionalSettlement(DirectionalOutcome.STOP, holding_ticks, tick, movement)
        terminal = horizon[-1]
        movement = ((terminal.quote - entry_tick.quote) / entry_tick.quote) * direction
        return DirectionalSettlement(
            DirectionalOutcome.TIMEOUT,
            policy.maximum_holding_ticks,
            terminal,
            movement,
        )
