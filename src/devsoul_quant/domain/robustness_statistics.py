"""Deterministic paired uncertainty summaries for synthetic robustness gates."""

from dataclasses import dataclass
from decimal import Decimal
from random import Random


class InvalidPairedStatistics(ValueError):
    """Raised when a paired robustness sample or bootstrap policy is invalid."""


@dataclass(frozen=True, slots=True)
class PairedBootstrapSummary:
    """Paired mean difference and deterministic percentile interval."""

    sample_count: int
    mean_difference: Decimal
    lower_bound: Decimal
    upper_bound: Decimal
    negative_count: int
    tie_count: int
    positive_count: int


def paired_bootstrap_summary(
    differences: tuple[Decimal, ...],
    *,
    confidence: Decimal,
    resamples: int,
    seed: int,
) -> PairedBootstrapSummary:
    """Summarize paired differences using a seeded percentile bootstrap."""
    if not differences:
        raise InvalidPairedStatistics("differences must be non-empty")
    if any(not isinstance(value, Decimal) or not value.is_finite() for value in differences):
        raise InvalidPairedStatistics("differences must contain finite Decimals")
    if (
        not isinstance(confidence, Decimal)
        or not confidence.is_finite()
        or not (Decimal(0) < confidence < Decimal(1))
    ):
        raise InvalidPairedStatistics("confidence must be a finite Decimal within (0, 1)")
    if type(resamples) is not int or resamples < 1:
        raise InvalidPairedStatistics("resamples must be a positive integer")
    if type(seed) is not int:
        raise InvalidPairedStatistics("seed must be an integer")

    sample_count = len(differences)
    random = Random(seed)
    bootstrap_means = sorted(
        sum(
            (differences[random.randrange(sample_count)] for _ in range(sample_count)),
            Decimal(0),
        )
        / Decimal(sample_count)
        for _ in range(resamples)
    )
    tail_probability = (Decimal(1) - confidence) / Decimal(2)
    lower_index = int(tail_probability * Decimal(resamples))
    upper_index = min(
        resamples - 1,
        int((Decimal(1) - tail_probability) * Decimal(resamples)),
    )

    return PairedBootstrapSummary(
        sample_count=sample_count,
        mean_difference=sum(differences, Decimal(0)) / Decimal(sample_count),
        lower_bound=bootstrap_means[lower_index],
        upper_bound=bootstrap_means[upper_index],
        negative_count=sum(value < 0 for value in differences),
        tie_count=sum(value == 0 for value in differences),
        positive_count=sum(value > 0 for value in differences),
    )
