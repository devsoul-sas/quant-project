"""Accumulator (ACCU) contract model and causal streak reconstruction.

An accumulator grows a stake by ``growth_rate`` on every tick whose spot stays
within a fixed percentage band (``barrier_fraction``) of the previous tick's
spot. The band is a *moving* barrier: each in-zone transition re-anchors the
reference to the current quote. A transition whose absolute return exceeds the
band breaks the streak.

This module only models the contractual barrier semantics and reconstructs
streaks from an owned tick sequence using ``Decimal``; it never prices payout,
recommends entry, or persists anything.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import ROUND_HALF_EVEN, Context, Decimal, localcontext
from itertools import pairwise

from devsoul_quant.domain.replay import Tick

_CONTEXT = Context(prec=50, rounding=ROUND_HALF_EVEN)


class InvalidAccumulator(ValueError):
    """Raised for invalid or internally inconsistent accumulator inputs."""


@dataclass(frozen=True, slots=True)
class AccumulatorContract:
    """Provider-independent ACCU contract parameters for streak reconstruction.

    ``barrier_fraction`` is the per-unit band (``tick_size_barrier``), e.g.
    ``0.000483474879`` (~0.04835%) for R_100 at a 5% growth rate. ``maximum_ticks``
    is the contract auto-settle cap and is *not* used for natural streak counting.
    """

    symbol: str
    growth_rate: Decimal
    barrier_fraction: Decimal
    maximum_ticks: int
    stake: Decimal

    def __post_init__(self) -> None:
        if not isinstance(self.symbol, str) or not self.symbol.strip():
            raise InvalidAccumulator("symbol must be a non-blank string")
        for field in ("growth_rate", "barrier_fraction", "stake"):
            value = getattr(self, field)
            if not isinstance(value, Decimal) or not value.is_finite() or value <= 0:
                raise InvalidAccumulator(f"{field} must be a positive finite Decimal")
        if self.growth_rate >= Decimal("1"):
            raise InvalidAccumulator("growth_rate must be below 1 (100%)")
        if self.barrier_fraction >= Decimal("1"):
            raise InvalidAccumulator("barrier_fraction must be below 1 (100%)")
        if type(self.maximum_ticks) is not int or self.maximum_ticks < 1:
            raise InvalidAccumulator("maximum_ticks must be a positive integer")


@dataclass(frozen=True, slots=True)
class Streak:
    """One reconstructed streak segment."""

    length: int
    broke: bool
    entry_epoch: int
    exit_epoch: int

    def __post_init__(self) -> None:
        if type(self.length) is not int or self.length < 0:
            raise InvalidAccumulator("streak length must be a non-negative integer")
        if type(self.entry_epoch) is not int or type(self.exit_epoch) is not int:
            raise InvalidAccumulator("streak epochs must be integers")


def _positive_fraction(value: object, field: str) -> Decimal:
    if not isinstance(value, Decimal) or not value.is_finite() or value <= 0:
        raise InvalidAccumulator(f"{field} must be a positive finite Decimal")
    return value


def in_zone(previous: Decimal, current: Decimal, barrier_fraction: Decimal) -> bool:
    """Return whether the transition stays within the moving barrier band."""
    fraction = _positive_fraction(barrier_fraction, "barrier_fraction")
    if (
        not isinstance(previous, Decimal)
        or not previous.is_finite()
        or previous <= 0
        or not isinstance(current, Decimal)
        or not current.is_finite()
        or current <= 0
    ):
        raise InvalidAccumulator("quotes must be positive finite Decimals")
    with localcontext(_CONTEXT):
        return abs((current - previous) / previous) <= fraction


def reconstruct_streaks(
    ticks: Sequence[Tick],
    barrier_fraction: Decimal,
) -> tuple[Streak, ...]:
    """Reconstruct every consecutive in-zone streak over a contiguous tick series.

    A transition ``t`` is in-zone when ``|t.quote - previous.quote| / previous.quote``
    is at most ``barrier_fraction``; the band re-anchors to ``t.quote`` on every
    in-zone transition. The returned tuple contains one :class:`Streak` per run,
    including the trailing (possibly still ongoing) run with ``broke=False``. A
    run of length 0 records an immediate breach on the first transition.
    """
    _positive_fraction(barrier_fraction, "barrier_fraction")
    if not isinstance(ticks, Sequence):
        raise InvalidAccumulator("ticks must be a sequence")
    if not ticks:
        return ()
    normalized = tuple(ticks)
    streaks: list[Streak] = []
    run_start = normalized[0]
    run_end = normalized[0]
    current = 0
    for previous, tick in pairwise(normalized):
        if tick.epoch <= previous.epoch:
            raise InvalidAccumulator("tick epochs must be strictly increasing")
        if in_zone(previous.quote, tick.quote, barrier_fraction):
            current += 1
            run_end = tick
        else:
            streaks.append(
                Streak(
                    length=current,
                    broke=True,
                    entry_epoch=run_start.epoch,
                    exit_epoch=run_end.epoch,
                )
            )
            current = 0
            run_start = tick
            run_end = tick
    streaks.append(
        Streak(
            length=current,
            broke=False,
            entry_epoch=run_start.epoch,
            exit_epoch=run_end.epoch,
        )
    )
    return tuple(streaks)


def split_continuous_segments(
    ticks: Sequence[Tick],
    cadence_seconds: int,
) -> tuple[tuple[Tick, ...], ...]:
    """Split ticks into contiguous segments, breaking at gaps wider than the cadence.

    A gap larger than ``cadence_seconds`` (or a non-increasing epoch) marks a
    discontinuity and starts a new segment, so streak reconstruction never spans a
    missing observation window.
    """
    if type(cadence_seconds) is not int or cadence_seconds < 1:
        raise InvalidAccumulator("cadence_seconds must be a positive integer")
    if not isinstance(ticks, Sequence):
        raise InvalidAccumulator("ticks must be a sequence")
    normalized = tuple(ticks)
    if not normalized:
        return ()
    segments: list[list[Tick]] = []
    current: list[Tick] = [normalized[0]]
    for previous, tick in pairwise(normalized):
        if tick.epoch <= previous.epoch or tick.epoch - previous.epoch > cadence_seconds:
            segments.append(current)
            current = [tick]
        else:
            current.append(tick)
    segments.append(current)
    return tuple(tuple(segment) for segment in segments)
