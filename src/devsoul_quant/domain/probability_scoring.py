"""Exact probabilistic forecast scoring for synthetic validation.

All calculations use ``Decimal``. Brier score measures probability accuracy;
expected calibration error summarizes reliability over fixed-width bins. These
are scientific diagnostics, not evidence of economic profitability.
"""

from dataclasses import dataclass
from decimal import Decimal


class InvalidProbabilityScore(ValueError):
    """Raised when forecasts or calibration settings are malformed."""


@dataclass(frozen=True, slots=True)
class ProbabilityForecast:
    """One causal probability forecast and its subsequently observed outcome."""

    probability: Decimal
    observed: bool

    def __post_init__(self) -> None:
        if (
            not isinstance(self.probability, Decimal)
            or not self.probability.is_finite()
            or not (Decimal(0) <= self.probability <= Decimal(1))
        ):
            raise InvalidProbabilityScore("probability must be a finite Decimal within [0, 1]")
        if type(self.observed) is not bool:
            raise InvalidProbabilityScore("observed must be a boolean")


@dataclass(frozen=True, slots=True)
class CalibrationBin:
    """Observed reliability within one non-empty fixed-width probability bin."""

    index: int
    count: int
    mean_probability: Decimal
    observed_frequency: Decimal


@dataclass(frozen=True, slots=True)
class ProbabilityScore:
    """Aggregate Brier and fixed-bin calibration diagnostics."""

    forecast_count: int
    brier_score: Decimal
    calibration_error: Decimal
    bins: tuple[CalibrationBin, ...]


def score_forecasts(
    forecasts: tuple[ProbabilityForecast, ...], *, bin_count: int = 10
) -> ProbabilityScore:
    """Score a non-empty sequence with exact Brier and weighted calibration error."""
    if not forecasts:
        raise InvalidProbabilityScore("scoring requires at least one forecast")
    if type(bin_count) is not int or bin_count < 1:
        raise InvalidProbabilityScore("bin_count must be a positive integer")

    total = len(forecasts)
    squared_errors = tuple(
        (forecast.probability - Decimal(int(forecast.observed))) ** 2 for forecast in forecasts
    )
    brier = sum(squared_errors, Decimal(0)) / Decimal(total)

    grouped: list[list[ProbabilityForecast]] = [[] for _ in range(bin_count)]
    for forecast in forecasts:
        index = min(int(forecast.probability * bin_count), bin_count - 1)
        grouped[index].append(forecast)

    bins: list[CalibrationBin] = []
    weighted_error = Decimal(0)
    for index, group in enumerate(grouped):
        if not group:
            continue
        count = len(group)
        mean_probability = sum((item.probability for item in group), Decimal(0)) / Decimal(count)
        observed_frequency = Decimal(sum(item.observed for item in group)) / Decimal(count)
        weighted_error += (
            abs(mean_probability - observed_frequency) * Decimal(count) / Decimal(total)
        )
        bins.append(
            CalibrationBin(
                index=index,
                count=count,
                mean_probability=mean_probability,
                observed_frequency=observed_frequency,
            )
        )

    return ProbabilityScore(
        forecast_count=total,
        brier_score=brier,
        calibration_error=weighted_error,
        bins=tuple(bins),
    )
