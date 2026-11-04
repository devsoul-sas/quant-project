"""Deterministic replay over DevSoul-owned synthetic ticks."""

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from itertools import pairwise

from devsoul_quant.domain.contracts import ContractType, EnterContractIntent


class Outcome(StrEnum):
    """Directional settlement outcome without monetary claims."""

    WIN = "WIN"
    LOSS = "LOSS"


class EconomyProvenance(StrEnum):
    """Origin classification for contract economics."""

    OBSERVED = "OBSERVED"
    ESTIMATED = "ESTIMATED"
    UNAVAILABLE = "UNAVAILABLE"


class InsufficientTicks(ValueError):
    """Raised when a replay cannot reach the requested expiry tick."""


class InvalidTickSequence(ValueError):
    """Raised when replay ticks are not strictly ordered in time."""


class UnsupportedBarrier(ValueError):
    """Raised when a tracer cannot settle the requested barrier semantics."""


class InvalidTick(ValueError):
    """Raised when a synthetic tick violates replay invariants."""


@dataclass(frozen=True, slots=True)
class Tick:
    """One synthetic tick."""

    epoch: int
    quote: Decimal

    def __post_init__(self) -> None:
        if type(self.epoch) is not int:
            raise InvalidTick("tick epoch must be an integer")
        if not isinstance(self.quote, Decimal):
            raise InvalidTick("tick quote must be a Decimal")
        if not self.quote.is_finite():
            raise InvalidTick("tick quote must be finite")


@dataclass(frozen=True, slots=True)
class ReplayResult:
    """Deterministic directional result with no inferred P/L."""

    outcome: Outcome
    economy: EconomyProvenance
    entry_tick: Tick
    exit_tick: Tick


def replay_rise_fall(
    intent: EnterContractIntent,
    ticks: Sequence[Tick],
    *,
    economy: EconomyProvenance = EconomyProvenance.UNAVAILABLE,
) -> ReplayResult:
    """Replay a Rise contract to its tick-duration expiry with a declared economy."""
    if intent.barrier is not None:
        raise UnsupportedBarrier("barrier is not supported by the Rise/Fall tracer")
    if len(ticks) <= intent.duration:
        raise InsufficientTicks("tick window does not reach contract expiry")
    replay_window = ticks[: intent.duration + 1]
    if any(current.epoch <= previous.epoch for previous, current in pairwise(replay_window)):
        raise InvalidTickSequence("tick epochs must be strictly increasing")
    entry_tick = ticks[0]
    exit_tick = ticks[intent.duration]
    if intent.contract_type is ContractType.CALL:
        won = exit_tick.quote > entry_tick.quote
    else:
        won = exit_tick.quote < entry_tick.quote
    outcome = Outcome.WIN if won else Outcome.LOSS
    return ReplayResult(
        outcome=outcome,
        economy=economy,
        entry_tick=entry_tick,
        exit_tick=exit_tick,
    )
