"""Deterministic paper settlement for Even/Odd contracts."""

from collections.abc import Sequence
from itertools import pairwise

from devsoul_quant.domain.contracts import ContractType, EnterContractIntent
from devsoul_quant.domain.digit_strategy import last_digit
from devsoul_quant.domain.replay import (
    EconomyProvenance,
    InsufficientTicks,
    InvalidTickSequence,
    Outcome,
    ReplayResult,
    Tick,
    UnsupportedBarrier,
)


def replay_digit(
    intent: EnterContractIntent,
    ticks: Sequence[Tick],
    *,
    economy: EconomyProvenance = EconomyProvenance.UNAVAILABLE,
) -> ReplayResult:
    """Replay an Even/Odd contract to its tick-duration expiry."""
    if intent.barrier is not None:
        raise UnsupportedBarrier("barrier is not supported by the Even/Odd tracer")
    if len(ticks) <= intent.duration:
        raise InsufficientTicks("tick window does not reach contract expiry")
    replay_window = ticks[: intent.duration + 1]
    if any(current.epoch <= previous.epoch for previous, current in pairwise(replay_window)):
        raise InvalidTickSequence("tick epochs must be strictly increasing")
    if intent.contract_type not in (ContractType.DIGITEVEN, ContractType.DIGITODD):
        raise ValueError("digit replay requires an Even/Odd contract")

    entry_tick = replay_window[0]
    exit_tick = replay_window[-1]
    is_even = last_digit(exit_tick) % 2 == 0
    won = is_even if intent.contract_type is ContractType.DIGITEVEN else not is_even
    return ReplayResult(
        outcome=Outcome.WIN if won else Outcome.LOSS,
        economy=economy,
        entry_tick=entry_tick,
        exit_tick=exit_tick,
    )
