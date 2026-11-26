"""Deterministic range and mean-reversion measures for Multipliers research.

These are descriptive measures over a bounded tick window, computed with
``Decimal`` at 50 digits (never floating point). The "zero point" (reference)
is configurable so the research can compare a fixed price reference, a
normalized displacement from the window start, or a moving average.

The module only measures; it never recommends MULTUP / MULTDOWN. Interpretation
belongs to the decision engine.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import ROUND_HALF_EVEN, Context, Decimal, localcontext
from enum import StrEnum
from itertools import pairwise

_DECIMAL_CONTEXT = Context(prec=50, rounding=ROUND_HALF_EVEN)


class InvalidRangeRegime(ValueError):
    """Raised for empty, short, or degenerate range inputs."""


class ReferenceMode(StrEnum):
    """How the reversion reference ("zero point") is defined."""

    PRICE = "PRICE"
    DISPLACEMENT = "DISPLACEMENT"
    MOVING_AVERAGE = "MOVING_AVERAGE"


@dataclass(frozen=True, slots=True)
class RangePolicy:
    """Frozen window and reference configuration for range analysis."""

    window: int
    reference_mode: ReferenceMode
    fixed_reference: Decimal | None = None

    def __post_init__(self) -> None:
        if type(self.window) is not int or self.window < 2:
            raise InvalidRangeRegime("window must be an integer of at least two")
        if not isinstance(self.reference_mode, ReferenceMode):
            raise InvalidRangeRegime("reference_mode must be a ReferenceMode")
        if self.fixed_reference is not None and (
            not isinstance(self.fixed_reference, Decimal)
            or not self.fixed_reference.is_finite()
            or self.fixed_reference <= 0
        ):
            raise InvalidRangeRegime("fixed_reference must be a positive finite Decimal or None")
        if self.reference_mode is ReferenceMode.PRICE and self.fixed_reference is None:
            raise InvalidRangeRegime("PRICE reference mode requires fixed_reference")


@dataclass(frozen=True, slots=True)
class RangeProfile:
    """Descriptive range/reversion measures for one tick window."""

    reference: Decimal
    displacement: Decimal
    z_score: Decimal
    window_min: Decimal
    window_max: Decimal
    amplitude: Decimal
    moving_average: Decimal
    volatility: Decimal
    momentum: Decimal
    deceleration: Decimal
    autocorrelation: Decimal
    crossing_count: int
    return_frequency: Decimal
    mean_return_ticks: Decimal | None


def _require_quotes(quotes: Sequence[Decimal], *, minimum: int) -> tuple[Decimal, ...]:
    normalized = tuple(quotes)
    if len(normalized) < minimum:
        raise InvalidRangeRegime(f"requires at least {minimum} quotes")
    if any(
        not isinstance(quote, Decimal) or not quote.is_finite() or quote <= 0
        for quote in normalized
    ):
        raise InvalidRangeRegime("quotes must be positive finite Decimals")
    return normalized


def returns(quotes: Sequence[Decimal]) -> tuple[Decimal, ...]:
    """Return per-tick simple returns (q_t - q_{t-1}) / q_{t-1}."""
    normalized = _require_quotes(quotes, minimum=2)
    with localcontext(_DECIMAL_CONTEXT):
        return tuple((current - previous) / previous for previous, current in pairwise(normalized))


def moving_average(quotes: Sequence[Decimal], window: int) -> Decimal:
    """Return the simple moving average of the last ``window`` quotes."""
    normalized = _require_quotes(quotes, minimum=window)
    with localcontext(_DECIMAL_CONTEXT):
        return sum(normalized[-window:], Decimal(0)) / Decimal(window)


def reference_price(quotes: Sequence[Decimal], policy: RangePolicy) -> Decimal:
    """Return the configured zero point for a quote window."""
    if policy.reference_mode is ReferenceMode.PRICE:
        assert policy.fixed_reference is not None
        return policy.fixed_reference
    normalized = _require_quotes(quotes, minimum=2)
    if policy.reference_mode is ReferenceMode.DISPLACEMENT:
        return normalized[0]
    return moving_average(normalized, policy.window)


def displacement(quote: Decimal, reference: Decimal) -> Decimal:
    """Return the normalized displacement (quote - reference) / reference."""
    if not isinstance(quote, Decimal) or not quote.is_finite() or quote <= 0:
        raise InvalidRangeRegime("quote must be a positive finite Decimal")
    if not isinstance(reference, Decimal) or not reference.is_finite() or reference <= 0:
        raise InvalidRangeRegime("reference must be a positive finite Decimal")
    with localcontext(_DECIMAL_CONTEXT):
        return (quote - reference) / reference


def volatility(quotes: Sequence[Decimal], window: int) -> Decimal:
    """Return the population standard deviation of the last ``window`` returns."""
    normalized = _require_quotes(quotes, minimum=window + 1)
    window_returns = returns(normalized)[-window:]
    with localcontext(_DECIMAL_CONTEXT):
        mean = sum(window_returns, Decimal(0)) / Decimal(len(window_returns))
        variance = sum(((value - mean) ** 2 for value in window_returns), Decimal(0)) / Decimal(
            len(window_returns)
        )
        return variance.sqrt()


def z_score(displacement_value: Decimal, volatility_value: Decimal) -> Decimal:
    """Return displacement measured in units of volatility."""
    if (
        not isinstance(volatility_value, Decimal)
        or not volatility_value.is_finite()
        or volatility_value <= 0
    ):
        raise InvalidRangeRegime("z-score requires positive volatility")
    return displacement_value / volatility_value


def local_extrema(quotes: Sequence[Decimal], window: int) -> tuple[Decimal, Decimal]:
    """Return (min, max) of the last ``window`` quotes."""
    normalized = _require_quotes(quotes, minimum=window)
    return (min(normalized[-window:]), max(normalized[-window:]))


def amplitude(low: Decimal, high: Decimal, reference: Decimal) -> Decimal:
    """Return the normalized range amplitude (high - low) / reference."""
    with localcontext(_DECIMAL_CONTEXT):
        return (high - low) / reference


def momentum(quotes: Sequence[Decimal], window: int) -> Decimal:
    """Return the mean of the last ``window`` simple returns (signed)."""
    normalized = _require_quotes(quotes, minimum=window + 1)
    window_returns = returns(normalized)[-window:]
    with localcontext(_DECIMAL_CONTEXT):
        return sum(window_returns, Decimal(0)) / Decimal(len(window_returns))


def deceleration(quotes: Sequence[Decimal], window: int) -> Decimal:
    """Return mean absolute return (older half) - mean absolute return (newer half).

    A positive value means the move is losing speed: recent ticks are moving less
    than earlier ticks, which is the slowing condition the reversion hypotheses
    look for.
    """
    normalized = _require_quotes(quotes, minimum=window + 1)
    window_returns = returns(normalized)[-window:]
    split = len(window_returns) // 2
    older = window_returns[:split]
    newer = window_returns[split:]
    if not older or not newer:
        raise InvalidRangeRegime("deceleration requires at least one return per half")
    with localcontext(_DECIMAL_CONTEXT):
        older_mean = sum((abs(value) for value in older), Decimal(0)) / Decimal(len(older))
        newer_mean = sum((abs(value) for value in newer), Decimal(0)) / Decimal(len(newer))
        return older_mean - newer_mean


def autocorrelation(values: Sequence[Decimal]) -> Decimal:
    """Return the lag-1 autocorrelation of a numeric sequence."""
    normalized = tuple(values)
    if len(normalized) < 2:
        raise InvalidRangeRegime("autocorrelation requires at least two values")
    with localcontext(_DECIMAL_CONTEXT):
        mean = sum(normalized, Decimal(0)) / Decimal(len(normalized))
        numerator = sum(
            ((left - mean) * (right - mean) for left, right in pairwise(normalized)),
            Decimal(0),
        )
        denominator = sum(((value - mean) ** 2 for value in normalized), Decimal(0))
        if denominator == 0:
            raise InvalidRangeRegime("autocorrelation is undefined for a constant sequence")
        return numerator / denominator


def crossing_count(quotes: Sequence[Decimal], reference: Decimal) -> int:
    """Return how many times the quote crosses the reference level."""
    normalized = _require_quotes(quotes, minimum=2)
    crossings = 0
    for previous, current in pairwise(normalized):
        previous_side = (previous - reference) >= 0
        current_side = (current - reference) >= 0
        if previous_side != current_side:
            crossings += 1
    return crossings


def analyze_range(quotes: Sequence[Decimal], policy: RangePolicy) -> RangeProfile:
    """Assemble the descriptive range/reversion profile for one window."""
    normalized = _require_quotes(quotes, minimum=policy.window + 1)
    with localcontext(_DECIMAL_CONTEXT):
        reference = reference_price(normalized, policy)
        current = normalized[-1]
        current_displacement = displacement(current, reference)
        volatility_value = volatility(normalized, policy.window)
        current_z_score = z_score(current_displacement, volatility_value)
        low, high = local_extrema(normalized, policy.window)
        crossings = crossing_count(normalized, reference)
        return RangeProfile(
            reference=reference,
            displacement=current_displacement,
            z_score=current_z_score,
            window_min=low,
            window_max=high,
            amplitude=amplitude(low, high, reference),
            moving_average=moving_average(normalized, policy.window),
            volatility=volatility_value,
            momentum=momentum(normalized, policy.window),
            deceleration=deceleration(normalized, policy.window),
            autocorrelation=autocorrelation(returns(normalized)),
            crossing_count=crossings,
            return_frequency=Decimal(crossings) / Decimal(policy.window),
            mean_return_ticks=_mean_return_ticks(crossings, policy.window),
        )


def _mean_return_ticks(crossings: int, window: int) -> Decimal | None:
    if crossings == 0:
        return None
    with localcontext(_DECIMAL_CONTEXT):
        return Decimal(window) / Decimal(crossings)
