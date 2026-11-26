"""Tests for deterministic paired robustness statistics."""

from decimal import Decimal

import pytest

from devsoul_quant.domain.robustness_statistics import (
    InvalidPairedStatistics,
    paired_bootstrap_summary,
)


def test_paired_bootstrap_summary_is_exact_for_constant_advantage() -> None:
    summary = paired_bootstrap_summary(
        (Decimal("-0.1"),) * 4,
        confidence=Decimal("0.95"),
        resamples=100,
        seed=17,
    )

    assert summary.sample_count == 4
    assert summary.mean_difference == Decimal("-0.1")
    assert summary.lower_bound == Decimal("-0.1")
    assert summary.upper_bound == Decimal("-0.1")
    assert summary.negative_count == 4
    assert summary.tie_count == 0
    assert summary.positive_count == 0


def test_paired_bootstrap_summary_is_deterministic_for_mixed_differences() -> None:
    differences = (
        Decimal("-0.3"),
        Decimal("-0.1"),
        Decimal("0"),
        Decimal("0.2"),
    )

    first = paired_bootstrap_summary(
        differences,
        confidence=Decimal("0.8"),
        resamples=200,
        seed=23,
    )
    second = paired_bootstrap_summary(
        differences,
        confidence=Decimal("0.8"),
        resamples=200,
        seed=23,
    )

    assert first == second
    assert first.mean_difference == Decimal("-0.05")
    assert first.negative_count == 2
    assert first.tie_count == 1
    assert first.positive_count == 1
    assert first.lower_bound <= first.mean_difference <= first.upper_bound


@pytest.mark.parametrize(
    ("differences", "confidence", "resamples", "seed", "message"),
    [
        ((), Decimal("0.95"), 100, 1, "non-empty"),
        ((Decimal(0),), Decimal(0), 100, 1, "confidence"),
        ((Decimal(0),), Decimal(1), 100, 1, "confidence"),
        ((Decimal(0),), Decimal("0.95"), 0, 1, "resamples"),
        ((Decimal(0),), Decimal("0.95"), 100, True, "seed"),
        ((Decimal("NaN"),), Decimal("0.95"), 100, 1, "finite"),
    ],
)
def test_paired_bootstrap_summary_rejects_invalid_inputs(
    differences: tuple[Decimal, ...],
    confidence: Decimal,
    resamples: int,
    seed: int,
    message: str,
) -> None:
    with pytest.raises(InvalidPairedStatistics, match=message):
        paired_bootstrap_summary(
            differences,
            confidence=confidence,
            resamples=resamples,
            seed=seed,
        )
