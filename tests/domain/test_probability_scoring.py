"""Tests for exact probabilistic scoring and calibration."""

from decimal import Decimal

import pytest

from devsoul_quant.domain.probability_scoring import (
    InvalidProbabilityScore,
    ProbabilityForecast,
    score_forecasts,
)


def test_perfect_forecasts_have_zero_brier_and_calibration_error() -> None:
    score = score_forecasts(
        (
            ProbabilityForecast(probability=Decimal("1"), observed=True),
            ProbabilityForecast(probability=Decimal("0"), observed=False),
        ),
        bin_count=2,
    )

    assert score.brier_score == Decimal("0")
    assert score.calibration_error == Decimal("0")
    assert score.forecast_count == 2


def test_brier_score_uses_exact_decimal_mean_squared_error() -> None:
    score = score_forecasts(
        (
            ProbabilityForecast(probability=Decimal("0.8"), observed=True),
            ProbabilityForecast(probability=Decimal("0.6"), observed=False),
        ),
        bin_count=2,
    )

    assert score.brier_score == Decimal("0.20")


def test_calibration_bins_report_mean_forecast_and_observed_frequency() -> None:
    score = score_forecasts(
        (
            ProbabilityForecast(probability=Decimal("0.2"), observed=False),
            ProbabilityForecast(probability=Decimal("0.4"), observed=True),
            ProbabilityForecast(probability=Decimal("0.8"), observed=True),
        ),
        bin_count=2,
    )

    assert len(score.bins) == 2
    assert score.bins[0].count == 2
    assert score.bins[0].mean_probability == Decimal("0.3")
    assert score.bins[0].observed_frequency == Decimal("0.5")
    assert score.bins[1].count == 1
    assert score.bins[1].mean_probability == Decimal("0.8")
    assert score.bins[1].observed_frequency == Decimal("1")
    assert score.calibration_error == Decimal("0.2")


def test_empty_forecasts_fail_closed() -> None:
    with pytest.raises(InvalidProbabilityScore, match="at least one"):
        score_forecasts(())


def test_forecast_rejects_probability_outside_unit_interval() -> None:
    with pytest.raises(InvalidProbabilityScore, match="probability"):
        ProbabilityForecast(probability=Decimal("1.1"), observed=True)


def test_forecast_rejects_non_boolean_observation() -> None:
    with pytest.raises(InvalidProbabilityScore, match="observed"):
        ProbabilityForecast(probability=Decimal("0.5"), observed=1)  # type: ignore[arg-type]


def test_bin_count_must_be_positive() -> None:
    with pytest.raises(InvalidProbabilityScore, match="bin_count"):
        score_forecasts((ProbabilityForecast(Decimal("0.5"), True),), bin_count=0)
